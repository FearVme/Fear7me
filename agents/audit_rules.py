# 主要作用：按照变更金额、公示、审批层级和技术委员会规则生成逐单审计结果。

from collections import defaultdict
from decimal import Decimal


def number(value):
    return Decimal(str(value or 0))


def yes(value):
    return str(value).startswith("是")


def committee_for_change(database, change_number):
    return [
        review for review in database["committee_reviews"]
        if review["change_number"] == change_number
    ]


def approval_for_change(database, change_number):
    return next(
        (record for record in database["approval_records"]
         if record["change_number"] == change_number),
        None,
    )


def audit_publicity(change):
    ratio = number(change["cumulative_ratio"])
    if ratio > Decimal("0.05") and not yes(change["sunshine_publicity"]):
        return {
            "rule": "阳光采购平台公示", "level": "高",
            "change_number": change["change_number"],
            "message": f"累计核准变更占比为{ratio * 100:.2f}%，超过5%，但“是否公示”为否",
        }
    return None


def audit_approval(change, approval):
    amount = number(change["approved_amount"])
    if amount <= Decimal("5"):
        required_index = 1
        required_text = "部门分管负责人"
    elif amount <= Decimal("50"):
        required_index = 2
        required_text = "部门主要负责人"
    elif amount <= Decimal("200"):
        required_index = 3
        required_text = "集团公司分管领导"
    else:
        required_index = 4
        required_text = "集团公司总经理"

    if approval is None:
        return {
            "rule": "审批流程核验", "level": "高",
            "change_number": change["change_number"],
            "message": f"核准金额{amount:.2f}万元，缺少审批记录，无法证明已完成{required_text}审批",
        }

    actual_count = len(approval["approvers"])
    if actual_count < required_index:
        return {
            "rule": "审批流程核验", "level": "高",
            "change_number": change["change_number"],
            "message": f"核准金额{amount:.2f}万元，审批记录仅到第{actual_count}级，缺少{required_text}审批",
        }
    return None


def audit_committee(database, change):
    amount = number(change["approved_amount"])
    if amount <= Decimal("200"):
        return None

    reviews = committee_for_change(database, change["change_number"])
    if not reviews:
        return {
            "rule": "工程技术委员会审批", "level": "高",
            "change_number": change["change_number"],
            "message": "核准金额超过200万元，但没有对应的工程技术委员会评审记录",
        }

    status = str(reviews[-1]["status"] or "")
    if status in {"未通过", "退回"}:
        return {
            "rule": "工程技术委员会审批", "level": "高",
            "change_number": change["change_number"],
            "message": f"核准金额超过200万元，工程技术委员会评审状态为“{status}”",
        }
    if status in {"待评审", "评审中"}:
        return {
            "rule": "工程技术委员会审批", "level": "待补数据",
            "change_number": change["change_number"],
            "message": f"核准金额超过200万元，工程技术委员会评审状态为“{status}”，流程尚未完成",
        }
    if status != "通过":
        return {
            "rule": "工程技术委员会审批", "level": "待补数据",
            "change_number": change["change_number"],
            "message": f"工程技术委员会评审状态为“{status}”，无法确认已通过",
        }
    return None


def audit_change_record(database, change):
    findings = []
    publicity = audit_publicity(change)
    if publicity:
        findings.append(publicity)
    approval = audit_approval(change, approval_for_change(database, change["change_number"]))
    if approval:
        findings.append(approval)
    committee = audit_committee(database, change)
    if committee:
        findings.append(committee)
    return findings


def audit_all(database):
    findings = []
    for change in database["changes"]:
        findings.extend(audit_change_record(database, change))
    return findings


def main():
    from agents.load_database import load_database
    import json
    result = audit_all(load_database())
    print(json.dumps({"finding_count": len(result), "findings": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
