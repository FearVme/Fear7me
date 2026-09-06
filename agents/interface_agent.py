# 主要作用：统一处理聊天输入，补充上下文，并选择制度问答或项目审计能力。

import re

from RAG.vector_ask import analyze_question, ask, synthesize_answer
from agents.audit_agent import project_matches, run_audit
from agents.load_database import load_database
from agents.roles import filter_database_for_role


ROLE_NAMES = {
    "A": "项目经理",
    "B": "区域管理",
    "C": "全部项目",
}


ROLE_PATTERNS = [
    re.compile(
        r"^\s*角色\s*([ABC])\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*role\s*([ABC])\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*([ABC])(?:\s+|[，,:：])",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*([ABC])\s*$",
        re.IGNORECASE,
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


def is_role_scope_question(question):
    return any(
        phrase in question
        for phrase in [
            "哪些角色",
            "哪几个角色",
            "有什么角色",
            "有哪些角色",
        ]
    )


def is_current_role_question(question):
    return any(
        phrase in question
        for phrase in [
            "我是什么角色",
            "我的角色是什么",
            "当前是什么角色",
            "当前角色是什么",
            "我现在是什么角色",
        ]
    )


def build_current_role_response(role, question):
    database = filter_database_for_role(
        load_database(),
        role,
    )
    project_lines = [
        f"{index}. {project['project_number']}："
        f"{project['project_name']}"
        for index, project in enumerate(
            database["projects"],
            start=1,
        )
    ]

    return {
        "type": "system_scope",
        "role": role,
        "question": question,
        "optimized_question": question,
        "capabilities": [],
        "answer": (
            f"你当前选择的是 {role}角色 · "
            f"{ROLE_NAMES[role]}，可查看 "
            f"{len(database['projects'])} 个项目：\n\n"
            + "\n\n".join(project_lines)
        ),
        "results": {},
    }


def build_role_scope_response():
    return {
        "type": "system_scope",
        "role": None,
        "question": "我可以查看哪些角色？",
        "optimized_question": "我可以查看哪些角色？",
        "capabilities": [],
        "answer": (
            "当前可以选择 3 个角色：\n\n"
            "1. A角色：项目经理，可查看 1 个项目\n\n"
            "2. B角色：区域管理，可查看 3 个项目\n\n"
            "3. C角色：全部项目，可查看全部 8 个项目"
        ),
        "results": {},
    }


def is_capability_question(question):
    return any(
        phrase in question
        for phrase in [
            "你能干嘛",
            "你能做什么",
            "有什么功能",
            "有哪些功能",
            "有什么能力",
            "有哪些能力",
            "可以做什么",
            "能帮我什么",
        ]
    )


def build_capability_response(role, question):
    return {
        "type": "system_scope",
        "role": role,
        "question": question,
        "optimized_question": question,
        "capabilities": [],
        "answer": (
            "我可以完成 3 类任务：\n\n"
            "1. 制度询问：回答工程设计变更制度、"
            "标准、流程和要求。\n\n"
            "2. 数据库查询：查询当前角色权限内的"
            "项目、设计变更和技术委员会评审记录。\n\n"
            "3. 合规审计：检查累计金额、公示、"
            "技术委员会审批、审批流程和先批后建问题。\n\n"
            "我会根据问题选择其中一个、多个或全部能力。"
        ),
        "results": {},
    }


def is_project_scope_question(question):
    return "项目" in question and any(
        phrase in question
        for phrase in [
            "可以查看",
            "能查看",
            "能看",
            "哪些项目",
            "哪几个项目",
            "有哪些项目",
        ]
    )


def is_project_basic_info_question(question):
    project_hint = "项目" in question or any(
        phrase in question
        for phrase in [
            "水厂",
            "污水处理厂",
            "综合管廊",
            "能源站",
            "工业园",
            "焚烧发电",
            "快速路",
            "安置房",
        ]
    )
    if not project_hint:
        return False

    if "变更" in question and not any(
        phrase in question
        for phrase in [
            "项目基本信息",
            "项目基本情况",
            "项目概况",
        ]
    ):
        return False

    return any(
        phrase in question
        for phrase in [
            "基本信息",
            "基础信息",
            "基本情况",
            "项目概况",
            "项目信息",
            "项目资料",
            "项目详情",
            "项目介绍",
        ]
    )


def is_change_amount_question(question):
    return "变更" in question and any(
        phrase in question
        for phrase in [
            "金额",
            "多少钱",
            "合计",
            "总额",
        ]
    )


def wants_change_amount_details(question):
    return any(
        phrase in question
        for phrase in [
            "明细",
            "每条",
            "逐条",
            "分别",
            "具体",
        ]
    )


def is_change_content_question(question):
    return "变更" in question and any(
        phrase in question
        for phrase in [
            "具体内容",
            "具体情况",
            "变更内容",
            "事项",
            "改了什么",
            "变更明细",
        ]
    )


def is_all_change_scope_question(question):
    return any(
        phrase in question
        for phrase in [
            "全部变更",
            "所有变更",
            "所有的变更",
            "整张变更表",
            "全部设计变更",
            "全部给出",
            "所有给出",
        ]
    )


def is_noncompliant_change_question(question):
    return "变更" in question and any(
        phrase in question
        for phrase in [
            "不合规",
            "不合规的",
            "违规",
            "不符合",
            "问题变更",
        ]
    )


def find_change_number(question):
    match = re.search(r"K\d{4}-\d{3}-BG-\d{3}", question, re.IGNORECASE)
    return match.group(0).upper() if match else None


def is_audit_detail_question(question):
    return (
        is_noncompliant_change_question(question)
        or "违规原因" in question
        or "不合规原因" in question
    ) and any(
        phrase in question
        for phrase in [
            "逐条",
            "每条",
            "全部给出",
            "具体明细",
            "详细",
        ]
    )


def format_amount(value):
    return f"{float(value or 0):,.2f}"


def build_project_basic_info_answer(role, database):
    lines = ["| 项目编号 | 项目名称 | 所属公司 | 责任部门 | 资金来源 | 项目类型 | 总投资（万元） | 阶段 | 地址 | 负责人 |", "|---|---|---|---|---|---|---:|---|---|---|"]
    lines.extend(
        f"| {p['project_number']} | {p['project_name']} | {p['company']} | {p['department']} | {p['funding']} | {p['project_type']} | {format_amount(p['total_investment'])} | {p['stage']} | {p['address']} | {p['manager']} |"
        for p in database["projects"]
    )
    return f"你当前可查看的 {len(database['projects'])} 个项目基本信息如下：\n\n" + "\n".join(lines)


def build_change_amount_answer(role, database, question):
    estimate_total = sum(
        float(change["estimate_amount"] or 0)
        for change in database["changes"]
    )
    approved_total = sum(
        float(change["approved_amount"] or 0)
        for change in database["changes"]
    )
    lines = ["| 项目 | 变更数量 | 估算金额合计（万元） | 核准金额合计（万元） |", "|---|---:|---:|---:|"]
    for project in database["projects"]:
        changes = [c for c in database["changes"] if c["project_number"] == project["project_number"]]
        lines.append(
            f"| {project['project_name']} | {len(changes)} | {format_amount(sum(float(c['estimate_amount'] or 0) for c in changes))} | {format_amount(sum(float(c['approved_amount'] or 0) for c in changes))} |"
        )
    detail = ""
    if wants_change_amount_details(question):
        detail_lines = ["| 变更编号 | 项目 | 估算金额（万元） | 核准金额（万元） |", "|---|---|---:|---:"]
        detail_lines.extend(
            f"| {c['change_number']} | {c['project_name']} | {format_amount(c['estimate_amount'])} | {format_amount(c['approved_amount'])} |"
            for c in database["changes"]
        )
        detail = "\n\n变更明细：\n\n" + "\n".join(detail_lines)
    return (
        f"按{role}角色当前权限，共查询到 {len(database['changes'])} 条设计变更。"
        f"估算金额合计 {format_amount(estimate_total)} 万元，核准金额合计 {format_amount(approved_total)} 万元。\n\n"
        "按项目汇总：\n\n" + "\n".join(lines) + detail
    )


def build_change_content_answer(role, database):
    lines = ["| 变更编号 | 项目 | 变更类型 | 是否应急 | 变更事项 | 本次估值（万元） | 本次核准（万元） | 累计核准（万元） | 累计占比 | 是否公示 |", "|---|---|---|---|---|---:|---:|---:|---:|---|"]
    lines.extend(
        f"| {c['change_number']} | {c['project_name']} | {c['change_type']} | {c['emergency']} | {c['change_item']} | {format_amount(c['estimate_amount'])} | {format_amount(c['approved_amount'])} | {format_amount(c['cumulative_approved'])} | {float(c['cumulative_ratio']) * 100:.2f}% | {c['sunshine_publicity']} |"
        for c in database["changes"]
    )
    return f"按{role}角色当前权限，共找到 {len(database['changes'])} 条设计变更，具体内容如下：\n\n" + "\n".join(lines)


def find_visible_project_name(role, question):
    database = filter_database_for_role(
        load_database(),
        role,
    )
    compact_question = question.replace(" ", "")

    ordinal_map = {
        "第一个": 0,
        "第一個": 0,
        "第二个": 1,
        "第二個": 1,
        "第三个": 2,
        "第三個": 2,
    }
    for ordinal, index in ordinal_map.items():
        if ordinal in question and index < len(database["projects"]):
            return database["projects"][index]["project_name"]

    best_match = None
    best_score = 0

    for project in database["projects"]:
        if project["project_number"] in question:
            return project["project_name"]

        compact_name = project["project_name"].replace(" ", "")
        for length in range(len(compact_name), 2, -1):
            fragments = [
                compact_name[start:start + length]
                for start in range(
                    len(compact_name) - length + 1
                )
            ]
            for fragment in fragments:
                if fragment in {"项目", "工程", "EPC"}:
                    continue
                if fragment in compact_question:
                    if length > best_score:
                        best_match = project["project_name"]
                        best_score = length
                    break

    return best_match


def build_database_response(
    role,
    question,
    project_name=None,
):
    database = filter_database_for_role(
        load_database(),
        role,
    )
    if project_name:
        database = {
            "projects": [
                project
                for project in database["projects"]
                if project_matches(
                    project["project_name"],
                    project_name,
                )
            ],
            "changes": [
                change
                for change in database["changes"]
                if project_matches(
                    change["project_name"],
                    project_name,
                )
            ],
            "committee_reviews": [
                review
                for review in database["committee_reviews"]
                if project_matches(
                    review["project_name"],
                    project_name,
                )
            ],
        }

    project_name_lines = [
        f"{index}. {project['project_name']}"
        for index, project in enumerate(
            database["projects"],
            start=1,
        )
    ]
    project_name_text = "\n\n".join(
        project_name_lines
    )

    if is_change_content_question(question):
        answer = build_change_content_answer(role, database)
    elif is_project_basic_info_question(question):
        answer = build_project_basic_info_answer(
            role,
            database,
        )
    elif is_project_scope_question(question):
        answer = (
            f"{role}角色可以查看 "
            f"{len(database['projects'])} 个项目：\n\n"
            f"{project_name_text}"
        )
    elif is_change_amount_question(question):
        answer = build_change_amount_answer(
            role,
            database,
            question,
        )
    else:
        project_lines = [
            f"{index}. {project['project_number']}："
            f"{project['project_name']}"
            for index, project in enumerate(
                database["projects"],
                start=1,
            )
        ]
        project_text = "\n\n".join(project_lines)
        answer = (
            f"{role}角色数据库查询完成，"
            f"项目 {len(database['projects'])} 个：\n\n"
            f"{project_text}\n\n"
            f"设计变更 {len(database['changes'])} 条，"
            f"技术委员会评审 "
            f"{len(database['committee_reviews'])} 条。"
        )

    return {
        "type": "database",
        "role": role,
        "question": question,
        "answer": answer,
        "database": database,
    }


def build_audit_response(
    role,
    question,
    result,
    rule,
):
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

    if is_noncompliant_change_question(question):
        findings = [
            finding
            for finding in findings
            if finding.get("change_number")
        ]
        title = "不合规设计变更"

    project_name = result.get(
        "project_name"
    )

    scope_text = (
        f"项目“{project_name}”"
        if project_name
        else "当前权限范围"
    )
    confirmed_findings = [
        finding
        for finding in findings
        if finding.get("level") != "待补数据"
    ]
    pending_findings = [
        finding
        for finding in findings
        if finding.get("level") == "待补数据"
    ]
    conclusion = (
        f"确认 {len(confirmed_findings)} 条不合规变更，"
        f"另有 {len(pending_findings)} 条需要补充数据后核验。"
        if is_noncompliant_change_question(question) and findings
        else (
        f"发现 {len(findings)} 项需要关注的结果。" if findings else "暂未发现异常。"
        )
    )
    detail = ""
    if is_noncompliant_change_question(question):
        detail = "\n\n" + "\n\n".join(
            f"{index}. {finding['change_number']}："
            f"{finding['message']}（{finding.get('level', '需核验')}）"
            for index, finding in enumerate(findings, start=1)
        )

    return {
        "type": "audit",
        "role": role,
        "question": question,
        "rule": rule,
        "title": title,
        "answer": f"已核查{scope_text}的“{title}”，{conclusion}{detail}",
        "findings": findings,
        "policy_evidence": result["policy_evidence"],
        "audit_result": result,
    }


def build_audit_detail_response(role, result):
    database = result.get("database") or filter_database_for_role(load_database(), role)
    if result.get("project_name"):
        database = {
            "projects": [
                project
                for project in database["projects"]
                if project_matches(
                    project["project_name"],
                    result["project_name"],
                )
            ],
            "changes": [
                change
                for change in database["changes"]
                if project_matches(
                    change["project_name"],
                    result["project_name"],
                )
            ],
            "committee_reviews": [
                review for review in database["committee_reviews"]
                if project_matches(review["project_name"], result["project_name"])
            ],
            "approval_records": [
                record for record in database["approval_records"]
                if project_matches(record["project_name"], result["project_name"])
            ],
        }
    findings_by_change = {}
    for finding in result["findings"]:
        change_number = finding.get("change_number")
        if change_number:
            findings_by_change.setdefault(
                change_number,
                [],
            ).append(finding)

    confirmed_count = 0
    pending_count = 0
    sections = [
        "| 变更编号 | 项目 | 变更事项 | 核准金额（万元） | 公示 | 技术委员会 | 审批记录 | 审计结论 | 原因 |",
        "|---|---|---|---:|---|---|---|---|---|",
    ]
    for index, change in enumerate(database["changes"], start=1):
        findings = findings_by_change.get(
            change["change_number"],
        )
        if findings:
            reasons = "；".join(
                f"{finding['message']}（{finding.get('level', '需核验')}）"
                for finding in findings
            )
            if any(
                finding.get("level") == "待补数据"
                for finding in findings
            ):
                pending_count += 1
                status = "待补数据，暂不能直接认定为违规"
            else:
                confirmed_count += 1
                status = "审计确认存在不合规问题"
        else:
            reasons = "当前审计规则未发现不合规线索"
            status = "未发现线索，不等同于确认合规"

        committee = next((r for r in database["committee_reviews"] if r["change_number"] == change["change_number"]), None)
        approval = next((r for r in database["approval_records"] if r["change_number"] == change["change_number"]), None)
        committee_status = committee["status"] if committee else "无记录"
        approval_status = f"{len(approval['approvers'])}级" if approval else "无记录"
        sections.append(
            f"| {change['change_number']} | {change['project_name']} | {change['change_item']} | {format_amount(change['approved_amount'])} | {change['sunshine_publicity']} | {committee_status} | {approval_status} | {status} | {reasons} |"
        )

    return (
        f"当前角色可见的 {len(database['changes'])} 条设计变更已逐条审计。"
        f"其中确认不合规 {confirmed_count} 条，"
        f"待补数据核验 {pending_count} 条。\n\n"
        + "\n".join(sections)
    )


def handle_input(
    text,
    current_role,
    conversation_history=None,
):
    history = conversation_history or []

    role, question = detect_role(
        text,
        current_role,
    )

    if not question:
        result = run_audit(role)

        return {
            "type": "role_switch",
            "role": role,
            "question": "",
            "answer": (
                f"已切换至角色 {role}。"
                f"当前可访问项目："
                f"{'、'.join(result['visible_project_numbers'])}"
            ),
            "audit_result": result,
        }

    normalized_question = question.rstrip("/／ ")

    if is_current_role_question(normalized_question):
        return build_current_role_response(
            role,
            normalized_question,
        )

    if is_capability_question(normalized_question):
        return build_capability_response(
            role,
            normalized_question,
        )

    if is_role_scope_question(normalized_question):
        response = build_role_scope_response()
        response["role"] = role
        response["question"] = question
        return response

    if is_change_content_question(normalized_question):
        analysis = analyze_question(
            normalized_question,
            conversation_history=history,
        )
        project_name = None
        if not is_all_change_scope_question(normalized_question):
            project_name = find_visible_project_name(
                role,
                normalized_question,
            )
        if analysis.get("project_name") and project_name:
            project_name = find_visible_project_name(
                role,
                analysis["project_name"],
            ) or project_name
        database_response = build_database_response(
            role,
            normalized_question,
            project_name=project_name,
        )
        return {
            "type": "database",
            "role": role,
            "question": question,
            "optimized_question": normalized_question,
            "capabilities": ["database"],
            "intent_analysis": analysis.get(
                "intent_analysis",
                "查询设计变更表中的具体变更事项和相关字段。",
            ),
            "answer": database_response["answer"],
            "results": {"database": database_response["database"]},
        }

    change_number = find_change_number(normalized_question)
    if change_number and any(phrase in normalized_question for phrase in ["合规", "违规", "不合规", "审批", "评审", "公示", "审计"]):
        audit_result = run_audit(role, change_number=change_number)
        direct_answer = build_audit_detail_response(role, audit_result)
        return {
            "type": "audit", "role": role, "question": question,
            "optimized_question": normalized_question, "capabilities": ["audit"],
            "intent_analysis": "按变更编号核验公示、审批层级和工程技术委员会评审状态。",
            "answer": direct_answer, "results": {"audit": audit_result},
        }

    if is_project_basic_info_question(normalized_question):
        project_name = find_visible_project_name(
            role,
            normalized_question,
        )
        database_response = build_database_response(
            role,
            normalized_question,
            project_name=project_name,
        )
        return {
            "type": "database",
            "role": role,
            "question": question,
            "optimized_question": normalized_question,
            "capabilities": ["database"],
            "answer": database_response["answer"],
            "results": {
                "database": database_response["database"],
            },
        }

    if is_project_scope_question(normalized_question):
        database_response = build_database_response(
            role,
            normalized_question,
        )
        return {
            "type": "database",
            "role": role,
            "question": question,
            "optimized_question": normalized_question,
            "capabilities": ["database"],
            "answer": database_response["answer"],
            "results": {
                "database": database_response["database"],
            },
        }

    if is_change_amount_question(normalized_question):
        project_name = find_visible_project_name(
            role,
            normalized_question,
        )
        database_response = build_database_response(
            role,
            normalized_question,
            project_name=project_name,
        )
        return {
            "type": "database",
            "role": role,
            "question": question,
            "optimized_question": normalized_question,
            "capabilities": ["database"],
            "answer": database_response["answer"],
            "results": {
                "database": database_response["database"],
            },
        }

    analysis = analyze_question(
        normalized_question,
        conversation_history=history,
    )
    optimized_question = analysis[
        "optimized_question"
    ]
    capabilities = analysis["capabilities"]
    project_name = analysis["project_name"]
    answers = []
    results = {}

    if not analysis["in_scope"]:
        return {
            "type": "out_of_scope",
            "role": role,
            "question": question,
            "optimized_question": optimized_question,
            "capabilities": [],
            "answer": (
                "该问题超出本系统范围。"
                "本系统仅回答工程设计变更制度、"
                "项目数据库查询和合规审计问题。"
            ),
            "results": {},
        }

    if "policy" in capabilities:
        answer, evidence = ask(
            optimized_question,
            conversation_history=history,
        )
        answers.append(f"【制度询问】\n{answer}")
        results["policy"] = evidence

    if "database" in capabilities:
        database_response = build_database_response(
            role,
            optimized_question,
            project_name=project_name,
        )
        answers.append(
            f"【数据库查询】\n"
            f"{database_response['answer']}"
        )
        results["database"] = database_response[
            "database"
        ]

    if "audit" in capabilities:
        audit_rule = analysis["audit_rule"]

        if audit_rule == "全部审计结果":
            audit_rule = None

        if is_noncompliant_change_question(normalized_question):
            project_name = (
                None
                if is_all_change_scope_question(normalized_question)
                else find_visible_project_name(
                    role,
                    normalized_question,
                )
            )

        audit_result = run_audit(
            role,
            project_name=project_name,
        )
        audit_response = build_audit_response(
            role,
            optimized_question,
            audit_result,
            audit_rule,
        )
        answers.append(
            f"【审计】\n{audit_response['answer']}"
        )
        results["audit"] = audit_response

        if is_audit_detail_question(normalized_question):
            direct_answer = build_audit_detail_response(
                role,
                audit_result,
            )
            return {
                "type": "audit",
                "role": role,
                "question": question,
                "optimized_question": optimized_question,
                "capabilities": ["audit"],
                "intent_analysis": analysis.get(
                    "intent_analysis",
                    "逐条审计当前角色可见的设计变更。",
                ),
                "answer": (
                    f"我理解你想问：{optimized_question}\n\n"
                    f"意图分析：{analysis.get('intent_analysis', '逐条审计当前角色可见的设计变更。')}\n\n"
                    + direct_answer
                ),
                "results": results,
            }

    optimization_note = ""
    if optimized_question != normalized_question:
        optimization_note = (
            f"我理解你想问：{optimized_question}\n\n"
        )
    intent_note = (
        f"意图分析：{analysis.get('intent_analysis', '识别用户问题并按权限查询相关信息。')}\n\n"
    )

    capability_data = {
        "results": answers,
    }
    integrated_answer = synthesize_answer(
        normalized_question,
        optimized_question,
        analysis.get("intent_analysis", "未提供"),
        capabilities,
        capability_data,
        conversation_history=history,
    )

    return {
        "type": (
            capabilities[0]
            if len(capabilities) == 1
            else "multiple"
        ),
        "role": role,
        "question": question,
        "optimized_question": optimized_question,
        "capabilities": capabilities,
        "answer": optimization_note + intent_note + integrated_answer,
        "intent_analysis": analysis.get("intent_analysis", ""),
        "results": results,
    }
