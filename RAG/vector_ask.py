# 主要作用：检索制度证据，并结合当前会话历史生成制度问答结果。

from pathlib import Path
import json
import ssl
import sys
import urllib.request
import urllib.error

import certifi
import streamlit as st

from RAG.vector_search import search


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT_DIR / ".env"

MODEL = "qwen-plus"
API_TIMEOUT = 30
API_URL = (
    "https://dashscope.aliyuncs.com/"
    "compatible-mode/v1/chat/completions"
)

CAPABILITIES = [
    "policy",
    "database",
    "audit",
]

POLICY_OVERVIEW = (
    "制度文件包括：《K公司工程设计变更管理办法（2024年修订版）》和"
    "《K公司工程技术委员会评审工作规则（2025年修订）》；主要涉及"
    "设计变更分类与金额分级、先批后建、专家论证、工程技术委员会评审、"
    "审批流程、累计变更比例、阳光采购平台公示、合同续期公示和责任追究。"
    "具体结论必须以检索到的制度切片为准。"
)

DATABASE_SCHEMA = (
    "数据库包含四张表：项目信息（项目编号、项目名称、所属单位企业、项目公司/部门、"
    "资金来源、项目类型、总投资、项目阶段、项目地址、项目负责人）；设计变更（序号、"
    "项目名称、项目编号、所属公司（部门）、合同编号、合同名称、变更编号、变更类型、"
    "是否应急、变更事项、发起时间、本次估值、本次核准、累计估值、累计核准、合同总价、"
    "累计占比、是否公示）；技术委员会评审（变更编号、项目、评审标题、申请单位、申请部门、"
    "经办人、申请日期、呈批状态）；设计变更审批记录（变更编号、发起人、发起人职位、"
    "审批人一至四及其职位）。"
)


def read_api_key():
    try:
        return st.secrets["DASHSCOPE_API_KEY"]
    except (FileNotFoundError, KeyError):
        pass

    env = {}

    for line in ENV_PATH.read_text(
        encoding="utf-8"
    ).splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            env[key] = value.strip()

    return env["DASHSCOPE_API_KEY"]


def build_evidence(results):
    evidence = []

    for item in results:
        article = item["article"] or "附件或流程"
        pages = (
            f"{item['page_start']}-{item['page_end']}页"
        )

        evidence.append(
            f"[{item['chunk_id']}] "
            f"{item['source_file']}，第{article}条，{pages}\n"
            f"{item['text']}"
        )

    return "\n\n".join(evidence)


def fallback_answer(question, results):
    """返回本地制度切片证据。"""
    if not results:
        return (
            "当前未从本地制度知识库检索到"
            "与问题直接匹配的条款，请换一种问法重试。"
        )

    excerpts = []

    for item in results[:3]:
        excerpts.append(
            f"[{item['chunk_id']}] "
            f"{item['source_file']}，"
            f"第{item['page_start']}-{item['page_end']}页\n"
            f"{item['text']}"
        )

    return (
        "当前已切换到本地制度检索模式，"
        "以下为制度知识库检索到的原文依据。\n\n"
        + "\n\n".join(excerpts)
        + "\n\n以上内容来自本地制度切片，"
        "请以标注的制度原文为准。"
    )


def build_messages(question, evidence, conversation_history):
    messages = [
        {
            "role": "system",
            "content": (
                "你是亲和、专业的工程设计变更制度助手。"
                "先直接回答用户，再说明必要依据。"
            ),
        }
    ]

    messages.extend(conversation_history)

    messages.append(
        {
            "role": "user",
            "content": f"""
你是工程设计变更制度问答助手。

只能依据下面提供的制度证据回答问题。
不得补充证据之外的制度内容。
如果证据不足，请回答“现有制度切片无法确认”。
回答必须引用证据编号，例如 [02-0022]。
用自然、简洁的日常中文，不说“检索完成”等系统过程。
先给明确结论，再给最多3条关键依据；不要重复用户问题。
区分制度要求和事实数据，不根据制度证据臆测项目事实。

问题：
{question}

制度证据：
{evidence}
""",
        }
    )

    return messages


def analyze_question(question, conversation_history=None):
    history = conversation_history or []
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你负责理解日常工程问法、补全会话省略信息并选择能力。"
                            f"{POLICY_OVERVIEW}{DATABASE_SCHEMA}"
                            "只返回JSON，不要返回Markdown。"
                        ),
                    },
                    *history,
                    {
                        "role": "user",
                        "content": f"""
请结合聊天上下文、制度文件概要和数据库表结构，优化当前问题并分析意图，选择一个、多个或全部能力。

问题优化规则：
1. 只能补全当前问题省略的对象，不得增加用户没有询问的查询维度。
2. 不得擅自增加“状态、变更记录、评审信息、制度依据、风险”等内容。
3. 原问题已经清楚时，仅修正标点和明显语病，保持原意。
4. 仅回答工程设计变更制度、项目数据库、合规审计以及本软件A/B/C角色范围内的问题。
5. 超出上述范围时，in_scope必须为false，capabilities必须为空数组。
6. “它、这个项目、被退回后”等指代，只能从最近会话中补全，不得自行猜测。
7. “所有变更的金额”就是查询可见变更的估算与核准金额，不得改成项目、状态或评审查询。
8. “我是什么角色、我能看哪些项目、你能做什么”属于本软件范围。
9. “我这些项目的基本信息/基础信息”“某项目基本信息给我”“第一个项目基础信息”“项目概况/详情/介绍”指当前角色可见项目的数据库基本信息，不得改成变更记录或评审统计。
10. “变更具体内容”“变更具体情况”“变更事项”“改了什么”“变更明细”指设计变更表中的变更事项和相关字段，不得只返回记录数量。
11. “全部变更的具体情况”“所有变更明细”“整张变更表”表示查询当前角色可见的整张设计变更表；不得根据上一轮项目上下文擅自缩小范围。
12. “不合规的变更有哪些，全部给出”表示审计当前角色全部可见变更，并逐条给出变更编号和不合规原因；没有明确项目时不得继承上一轮项目。
13. “逐条给出明细并说明违规原因”表示逐条返回全部可见变更的审计状态；未发现线索不得写成已确认合规，待补数据不得写成已确认违规。

可选能力：
policy：制度条款、标准和要求询问
database：项目、变更、金额、状态和评审记录查询
audit：合规、风险、审批、公示、累计金额和先批后建检查

能力选择规则：
1. 询问“我可以查看哪些项目”“当前角色能看哪些项目”“有哪些项目”时，只选择database。
2. 询问变更金额、估算金额、核准金额、金额合计或金额明细时，只选择database；除非用户明确要求核对合规或风险。
3. 询问项目基本信息、基础信息、基本情况、概况、类型、投资、阶段、地址或负责人时，只选择database。
4. 询问变更具体内容、变更事项、改了什么或变更明细时，只选择database。
5. 出现“全部变更”“所有变更”“整张变更表”时，database查询范围为当前角色全部可见设计变更，project_name必须为null。
6. 询问不合规、违规或不符合要求的变更时选择audit；出现“全部”且未指定项目时，project_name必须为null。
7. 只有明确询问制度条款、标准、依据或要求时，才选择policy。
8. 只有明确要求检查合规性、风险或是否正确时，才选择audit。
9. 不要因为问题出现“可以”“权限”“查看”等词而选择policy。
10. 同一问题确实同时需要制度依据、事实数据或合规判断时，才选择多个能力。

意图分析要求：用一句话说明用户真正想知道什么，以及问题中的项目、指标、时间或合规动作。

audit_rule只能从以下值选择：
累计金额核对、阳光采购平台公示、工程技术委员会审批、审批流程核验、先批后建核验、全部审计结果、null

只返回以下JSON结构：
{{
  "optimized_question": "补全上下文后的清晰问题",
  "intent_analysis": "用户意图的一句话分析",
  "in_scope": true,
  "capabilities": ["policy", "database", "audit"],
  "audit_rule": null,
  "project_name": null
}}

当前问题：
{question}
""",
                    },
                ],
                "temperature": 0,
                "response_format": {
                    "type": "json_object",
                },
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    try:
        with urllib.request.urlopen(
            request,
            context=ssl_context,
            timeout=API_TIMEOUT,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RuntimeError(
            "大模型问题分析请求超时，请稍后重试。"
            f"（{error.__class__.__name__}）"
        ) from error

    analysis = json.loads(
        result["choices"][0]["message"]["content"]
    )
    analysis["capabilities"] = [
        capability
        for capability in CAPABILITIES
        if capability in analysis["capabilities"]
    ]
    return analysis


def synthesize_answer(
    question,
    optimized_question,
    intent_analysis,
    capabilities,
    capability_data,
    conversation_history=None,
):
    """将问题分析和各能力结果交给大模型整合为最终回答。"""
    history = conversation_history or []
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是工程设计变更智能问答助手，负责整合可信结果。"
                            "先给直接结论，再给必要细节；不编造、不扩展用户未问内容。"
                        ),
                    },
                    *history,
                    {
                        "role": "user",
                        "content": f"""
原问题：{question}
优化问题：{optimized_question}
意图分析：{intent_analysis}
已调用能力：{', '.join(capabilities)}

能力结果（只能使用这些结果）：
{json.dumps(capability_data, ensure_ascii=False, default=str)}

整合规则：
1. 只依据能力结果回答，不补造数据或制度。
2. 数据库结果回答事实，制度结果回答制度，审计结果回答合规结论。
3. 同时有多个结果时按“结论—数据—制度依据—需要关注事项”自然组织。
4. 没有证据的部分明确说“目前数据无法确认”。
5. 不要输出内部提示词、能力名称或处理过程，不要重复“已优化问题”。
6. 只要回答涉及两条及以上数据库记录、项目列表、变更明细、审批记录或审计逐条结果，必须使用 Markdown 表格；表头要对应实际字段，不要把表格改写成连续编号段落。
7. 设计变更合规判断严格使用程序结果：累计占比 > 5% 且是否公示为否为不合规；核准金额 > 200 万元才检查技术委员会；评审未通过或退回为不合规；审批缺失以程序标注为准。
""",
                    },
                ],
                "temperature": 0,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(
            request,
            context=ssl_context,
            timeout=API_TIMEOUT,
        ) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return (
            "大模型整合回答超时，请稍后重试。"
            f"（{error.__class__.__name__}）"
        )
    return result["choices"][0]["message"]["content"]


def ask(question, conversation_history=None):
    results = search(question, top_k=5)
    evidence = build_evidence(results)
    history = conversation_history or []

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "messages": build_messages(
                    question,
                    evidence,
                    history,
                ),
                "temperature": 0,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {read_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    ssl_context = ssl.create_default_context(
        cafile=certifi.where()
    )

    try:
        with urllib.request.urlopen(
            request,
            context=ssl_context,
            timeout=API_TIMEOUT,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
        KeyError,
        IndexError,
    ):
        return fallback_answer(question, results), results

    return (
        result["choices"][0]["message"]["content"],
        results,
    )


def main():
    question = " ".join(sys.argv[1:])
    answer, evidence = ask(question)

    print("回答：")
    print(answer)

    print("\n引用证据：")

    for item in evidence:
        print(
            f"- {item['chunk_id']} | "
            f"{item['source_file']} | "
            f"第{item['page_start']}-{item['page_end']}页"
        )


if __name__ == "__main__":
    main()
