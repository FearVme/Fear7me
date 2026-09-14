"""企业级请求路由：确定性规则优先，模型分析作为兜底。"""

import re


POLICY_PHRASES = (
    "制度", "办法", "规则", "条款", "规定", "要求", "属于哪类", "属于哪一类",
    "分为哪些类别", "审批权限", "审批流程", "是否需要评审", "是否必须公示",
    "必须公示", "对外公示", "能否先实施后审批", "应急", "抢险", "先批后建",
    "依据什么文件", "实施前", "施工单位依据",
)
DATA_PHRASES = (
    "当前", "实际", "项目编号", "查询", "列出", "金额合计", "金额汇总",
    "金额明细", "多少钱", "各项目金额", "变更记录", "审批记录", "审批链",
    "几条变更", "有几条变更", "变更数量",
)
AUDIT_PHRASES = (
    "审计", "合规", "不合规", "违规", "风险", "核查", "检查", "未通过",
    "未公示", "审批级数不足", "审批流程问题",
)


def _has_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def route_request(question):
    """返回稳定、可记录的路由决策，不执行任何数据或模型调用。"""
    text = str(question or "").strip()
    if not text:
        return {
            "route": "invalid",
            "capabilities": [],
            "confidence": 1.0,
            "needs_clarification": True,
        }

    has_policy = _has_any(text, POLICY_PHRASES)
    if "超过合同价5%" in text or "超过合同价 5%" in text:
        has_policy = True
    has_data = _has_any(text, DATA_PHRASES)
    has_audit = _has_any(text, AUDIT_PHRASES)

    # 明确要求实际数据时，制度条件不能把请求误路由为纯制度问答。
    if has_policy and has_data and (has_audit or "实际" in text or "当前" in text or "哪些" in text):
        capabilities = ["policy", "database"]
        if has_audit:
            capabilities.append("audit")
        return {
            "route": "multi",
            "capabilities": capabilities,
            "confidence": 0.95,
            "needs_clarification": False,
        }

    if has_policy and not has_audit:
        return {
            "route": "policy",
            "capabilities": ["policy"],
            "confidence": 0.98,
            "needs_clarification": False,
        }

    if has_audit:
        return {
            "route": "audit",
            "capabilities": ["audit"],
            "confidence": 0.96,
            "needs_clarification": False,
        }

    if has_data:
        return {
            "route": "database",
            "capabilities": ["database"],
            "confidence": 0.96,
            "needs_clarification": False,
        }

    return {
        "route": "model_fallback",
        "capabilities": [],
        "confidence": 0.0,
        "needs_clarification": False,
    }


def extract_scope(question):
    """抽取可审计的显式变更编号；项目名称仍由权限过滤器匹配。"""
    match = re.search(r"K\d{4}-\d{3}-BG-\d{3}", str(question or ""), re.I)
    return {"change_number": match.group(0).upper() if match else None}
