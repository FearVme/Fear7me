# 主要作用：根据制度要求，对工程设计变更数据库执行金额、公示、技术委员会、审批流程及其他冲突审计。

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
import re

from agents.load_database import load_database


def number(value):
    return Decimal(str(value or 0))


def yes(value):
    return str(value).startswith("是")


def date_from_text(value):
    match = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
    if match is None:
        return None
    return datetime.strptime(match.group(), "%Y-%m-%d")


def audit_amounts(database):
    findings = []
    totals = defaultdict(
        lambda: {
            "estimate": Decimal("0"),
            "approved": Decimal("0"),
        }
    )

    for change in sorted(database["changes"], key=lambda item: item["sequence"]):
        contract = change["contract_number"]
        totals[contract]["estimate"] += number(change["estimate_amount"])
        totals[contract]["approved"] += number(change["approved_amount"])

        expected_estimate = totals[contract]["estimate"]
        expected_approved = totals[contract]["approved"]

        if expected_estimate != number(change["cumulative_estimate"]):
            findings.append(
                {
                    "rule": "累计金额核对",
                    "level": "高",
                    "change_number": change["change_number"],
                    "message": "累计估算金额与逐笔金额合计不一致",
                    "expected": expected_estimate,
                    "reported": number(change["cumulative_estimate"]),
                }
            )

        if expected_approved != number(change["cumulative_approved"]):
            findings.append(
                {
                    "rule": "累计金额核对",
                    "level": "高",
                    "change_number": change["change_number"],
                    "message": "累计核准金额与逐笔金额合计不一致",
                    "expected": expected_approved,
                    "reported": number(change["cumulative_approved"]),
                }
            )

    return findings


def audit_sunshine_publicity(database):
    findings = []

    for change in database["changes"]:
        single_amount = max(
            number(change["estimate_amount"]),
            number(change["approved_amount"]),
        )
        cumulative_amount = max(
            number(change["cumulative_estimate"]),
            number(change["cumulative_approved"]),
        )
        contract_total = number(change["contract_total"])

        reasons = []

        if single_amount >= Decimal("400"):
            reasons.append("单项变更金额达到400万元")

        if cumulative_amount / contract_total >= Decimal("0.05"):
            reasons.append("累计变更金额达到合同价5%")

        if reasons and not yes(change["sunshine_publicity"]):
            findings.append(
                {
                    "rule": "阳光采购平台公示",
                    "level": "高",
                    "change_number": change["change_number"],
                    "message": "；".join(reasons) + "，但未标记为已公示",
                }
            )

    return findings


def audit_committee(database):
    findings = []
    reviews = defaultdict(list)

    for review in database["committee_reviews"]:
        reviews[review["project_number"]].append(review)

    for change in database["changes"]:
        amount = max(
            number(change["estimate_amount"]),
            number(change["approved_amount"]),
        )

        if amount < Decimal("400"):
            continue

        if not yes(change["technical_committee"]):
            findings.append(
                {
                    "rule": "工程技术委员会审批",
                    "level": "高",
                    "change_number": change["change_number"],
                    "message": "A类或B类变更未标记为工程技术委员会评审",
                }
            )

        project_reviews = reviews[change["project_number"]]
        if not any(review["status"] == "已完成" for review in project_reviews):
            findings.append(
                {
                    "rule": "工程技术委员会审批",
                    "level": "高",
                    "change_number": change["change_number"],
                    "message": "项目没有状态为“已完成”的技术委员会评审记录",
                }
            )

    return findings


def audit_approval_flow(database):
    changes = database["changes"]
    required_fields = [
        "approval_flow",
        "approval_status",
        "approver",
        "approval_date",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in changes[0]
    ]

    if not missing_fields:
        return []

    return [
        {
            "rule": "审批流程核验",
            "level": "待补数据",
            "message": "当前数据库缺少审批节点、审批状态、审批人或审批完成日期，无法核验完整流程",
            "missing_fields": missing_fields,
        }
    ]


def audit_other_conflicts(database):
    findings = []
    internal_publicity_exists = "internal_publicity" in database["changes"][0]

    if not internal_publicity_exists:
        findings.append(
            {
                "rule": "制度冲突检查",
                "level": "待补数据",
                "message": "数据库没有内部公示字段，无法核验所有设计变更是否完成内部公示",
            }
        )

    for change in database["changes"]:
        issue_date = change["issue_date"]
        start_date = date_from_text(change["change_started"])

        if start_date and start_date < issue_date and not yes(change["emergency"]):
            findings.append(
                {
                    "rule": "先批后建核验",
                    "level": "待补数据",
                    "change_number": change["change_number"],
                    "message": "变更发起日期前已有实施记录；数据库缺少审批完成日期，需补充后核验是否违反先批后建要求",
                }
            )

        amount = max(
            number(change["estimate_amount"]),
            number(change["approved_amount"]),
        )

        if amount >= Decimal("400") and not yes(change["expert_review"]):
            findings.append(
                {
                    "rule": "制度冲突检查",
                    "level": "中",
                    "change_number": change["change_number"],
                    "message": "重大变更未标记为已完成专家评审",
                }
            )

        ratio = max(
            number(change["cumulative_estimate"]),
            number(change["cumulative_approved"]),
        ) / number(change["contract_total"])

        if ratio >= Decimal("0.90") and not yes(change["warning_90"]):
            findings.append(
                {
                    "rule": "制度冲突检查",
                    "level": "中",
                    "change_number": change["change_number"],
                    "message": "累计金额达到合同价90%，但90%预警字段未标记",
                }
            )

    return findings


def audit_all(database):
    findings = []
    findings.extend(audit_amounts(database))
    findings.extend(audit_sunshine_publicity(database))
    findings.extend(audit_committee(database))
    findings.extend(audit_approval_flow(database))
    findings.extend(audit_other_conflicts(database))
    return findings


def main():
    database = load_database()
    findings = audit_all(database)

    print(
        json.dumps(
            {
                "finding_count": len(findings),
                "findings": findings,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
