# 主要作用：读取项目、设计变更、技术委员会评审和审批记录，并统一转换为审计使用的数据结构。

from pathlib import Path
import json

import openpyxl


ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT_DIR / "Database/K公司8项目完整模拟数据.xlsx"


def rows_as_dicts(sheet):
    rows = sheet.iter_rows(values_only=True)
    headers = next(rows)
    for excel_row, values in enumerate(rows, start=2):
        if not any(value is not None for value in values):
            continue
        yield excel_row, dict(zip(headers, values))


def load_database():
    workbook = openpyxl.load_workbook(DATABASE_PATH, data_only=True, read_only=True)

    projects = []
    for _, row in rows_as_dicts(workbook["项目信息"]):
        projects.append({
            "project_number": row["项目编号"], "project_name": row["项目名称"],
            "company": row["所属单位企业"], "department": row["项目公司/部门"],
            "funding": row["资金来源"], "project_type": row["项目类型"],
            "total_investment": row["总投资（万元）"], "stage": row["项目阶段"],
            "address": row["项目地址"], "manager": row["项目负责人"],
        })

    changes = []
    for excel_row, row in rows_as_dicts(workbook["设计变更"]):
        changes.append({
            "excel_row": excel_row, "sequence": row["序号"],
            "project_name": row["项目名称"], "project_number": row["项目编号"],
            "company": row["所属公司（部门）"], "contract_number": row["合同编号"],
            "contract_name": row["合同名称"], "change_number": row["变更编号"],
            "change_type": row["变更类型"], "emergency": row["是否应急"],
            "change_item": row["变更事项"], "issue_date": row["发起时间"],
            "estimate_amount": row["本次估值 (万元)"], "approved_amount": row["本次核准 (万元)"],
            "cumulative_estimate": row["累计估值 (万元)"], "cumulative_approved": row["累计核准 (万元)"],
            "contract_total": row["合同总价 (万元)"], "cumulative_ratio": row["累计占比"],
            "sunshine_publicity": row["是否公示"],
        })

    committee_reviews = []
    for excel_row, row in rows_as_dicts(workbook["技术委员会评审"]):
        committee_reviews.append({
            "excel_row": excel_row, "sequence": row["序号"], "change_number": row["变更编号"],
            "project_name": row["项目名称"], "project_number": row["项目编号"],
            "company": row["所属企业"], "title": row["评审标题"],
            "applicant": row["申请单位"], "department": row["申请部门"],
            "handler": row["经办人"], "application_date": row["申请日期"],
            "status": row["呈批状态"],
        })

    approval_records = []
    for excel_row, row in rows_as_dicts(workbook["设计变更审批记录"]):
        approval_records.append({
            "excel_row": excel_row, "sequence": row["序号"],
            "project_number": row["项目编号"], "project_name": row["项目名称"],
            "change_number": row["变更编号"], "initiator": row["发起人"],
            "initiator_position": row["发起人职位"],
            "approvers": [
                {"name": row[f"审批人{name}"], "position": row[f"审批人{name}职位"]}
                for name in ["一", "二", "三", "四"]
                if row[f"审批人{name}"] not in (None, "", "-")
            ],
        })

    return {"projects": projects, "changes": changes,
            "committee_reviews": committee_reviews, "approval_records": approval_records}


def main():
    database = load_database()
    print(json.dumps({key: len(value) for key, value in database.items()}, ensure_ascii=False, indent=2))
    print(json.dumps(database["changes"][0], ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
