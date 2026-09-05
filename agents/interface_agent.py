# 主要作用：统一处理聊天框输入，识别角色、审计问题和制度知识问题，并调用对应 Agent。

import re
import urllib.error

from RAG.vector_ask import ask
from agents.audit_agent import run_audit


ROLE_PATTERNS = [
    re.compile(r"^\s*角色\s*([ABC])\s*", re.IGNORECASE),
    re.compile(r"^\s*role\s*([ABC])\s*", re.IGNORECASE),
    re.compile(r"^\s*([ABC])(?:\s+|[，,:：])", re.IGNORECASE),
    re.compile(r"^\s*([ABC])\s*$", re.IGNORECASE),
]


AUDIT_RULES = [
    (
        "累计金额核对",
        [
            "累计金额",
            "金额错误",
            "金额算错",
            "累计是否错误",
            "变更金额累计",
        ],
    ),
    (
        "阳光采购平台公示",
        [
            "阳光平台",
            "阳光采购平台",
            "是否公示",
            "平台公示",
        ],
    ),
    (
        "工程技术委员会审批",
        [
            "工程技术委员会",
            "技术委员会审批",
            "委员会审批",
        ],
    ),
    (
        "审批流程核验",
        [
            "审批流程",
            "审批是否正确",
            "分级审批",
            "审批权限",
        ],
    ),
]


def detect_role(text, current_role):
    for pattern in ROLE_PATTERNS:
        match = pattern.match(text)

        if match:
            role = match.group(1).upper()
            question = text[match.end():].strip()
            return role, question

    return current_role, text.strip()


def detect_audit_rule(question):
    for rule, keywords in AUDIT_RULES:
        if any(keyword in question for keyword in keywords):
            return rule

    if any(
        keyword in question
        for keyword in [
            "审计",
            "核查",
            "检查",
            "项目数据",
            "台账",
            "风险",
            "制度冲突",
            "其他问题",
        ]
    ):
        return None

    return False


def build_audit_response(role, question, result, rule):
    if rule is None:
        findings = result["findings"]
        title = "全部审计结果"
    else:
        findings = [
            finding
            for finding in result["findings"]
            if finding["rule"] == rule
        ]
        title = rule

    return {
        "type": "audit",
        "role": role,
        "question": question,
        "rule": rule,
        "title": title,
        "answer": (
            f"{role}角色已完成“{title}”审计，"
            f"当前权限范围内共发现 {len(findings)} 条结果。"
        ),
        "findings": findings,
        "policy_evidence": result["policy_evidence"],
        "audit_result": result,
    }


def handle_input(text, current_role):
    role, question = detect_role(text, current_role)

    if not question:
        result = run_audit(role)

        return {
            "type": "role_switch",
            "role": role,
            "question": "",
            "answer": (
                f"已切换至角色 {role}。"
                f"当前可访问项目：{'、'.join(result['visible_project_numbers'])}"
            ),
            "audit_result": result,
        }

    audit_rule = detect_audit_rule(question)

    if audit_rule is not False:
        result = run_audit(role)
        return build_audit_response(
            role,
            question,
            result,
            audit_rule,
        )

    try:
        answer, evidence = ask(question)
    except urllib.error.URLError:
        # 网络或证书问题不应让 Streamlit 页面显示 Python traceback。
        return {
            "type": "knowledge",
            "role": role,
            "question": question,
            "answer": "制度知识问答服务暂时不可用，请检查网络或 SSL 证书配置后重试。",
            "evidence": [],
        }

    return {
        "type": "knowledge",
        "role": role,
        "question": question,
        "answer": answer,
        "evidence": evidence,
    }
