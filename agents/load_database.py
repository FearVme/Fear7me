# 主要作用：读取三张项目数据库表，并统一转换为审计 Agent 使用的数据结构。

from pathlib import Path
import json

import openpyxl


ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT_DIR / "Database/工作簿2_K公司8项目完整模拟数据.xlsx"


def load_database():
    workbook = openpyxl.load_workbook(
        DATABASE_PATH,
        data_only=True,
        read_only=True,
    )

    project_sheet = workbook["项目信息"]
    change_sheet = workbook["设计变更"]
    committee_sheet = workbook["技术委员会评审"]

    projects = []

    for row in project_sheet.iter_rows(
        min_row=2,
        values_only=True,
    ):
        projects.append(
            {
                "project_number": row[0],
                "project_name": row[1],
                "company": row[2],
                "department": row[3],
                "funding": row[4],
                "project_type": row[5],
                "total_investment": row[6],
                "stage": row[7],
                "address": row[8],
                "manager": row[9],
            }
        )

    changes = []

    for excel_row, row in enumerate(
        change_sheet.iter_rows(
            min_row=5,
            values_only=True,
        ),
        start=5,
    ):
        if row[0] is None:
            continue

        changes.append(
            {
                "excel_row": excel_row,
                "sequence": row[0],
                "project_name": row[1],
                "project_number": row[2],
                "company": row[3],
                "contract_number": row[4],
                "contract_name": row[5],
                "project_start_date": row[6],
                "project_status": row[7],
                "project_end_date": row[8],
                "change_number": row[9],
                "change_type": row[10],
                "emergency": row[11],
                "change_item": row[12],
                "issue_date": row[13],
                "estimate_amount": row[14],
                "approved_amount": row[15],
                "change_started": row[16],
                "change_completed": row[17],
                "technical_committee": row[18],
                "cumulative_estimate": row[19],
                "cumulative_approved": row[20],
                "expert_review": row[21],
                "contract_total": row[22],
                "estimate_warning_ratio": row[23],
                "approved_warning_ratio": row[24],
                "warning_90": row[25],
                "over_contract_5_percent": row[26],
                "sunshine_publicity": row[27],
                "contract_renewal": row[28],
                "renewal_publicity": row[29],
                "reporter": row[30],
            }
        )

    committee_reviews = []

    for excel_row, row in enumerate(
        committee_sheet.iter_rows(
            min_row=2,
            values_only=True,
        ),
        start=2,
    ):
        committee_reviews.append(
            {
                "excel_row": excel_row,
                "sequence": row[0],
                "project_name": row[1],
                "project_number": row[2],
                "engineering_name": row[3],
                "company": row[4],
                "title": row[5],
                "applicant": row[6],
                "department": row[7],
                "handler": row[8],
                "application_date": row[9],
                "status": row[10],
                "operation": row[11],
            }
        )

    return {
        "projects": projects,
        "changes": changes,
        "committee_reviews": committee_reviews,
    }


def main():
    database = load_database()

    print(
        json.dumps(
            {
                "project_count": len(database["projects"]),
                "change_count": len(database["changes"]),
                "committee_review_count": len(
                    database["committee_reviews"]
                ),
                "first_project": database["projects"][0],
                "first_change": database["changes"][0],
                "first_committee_review": database[
                    "committee_reviews"
                ][0],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()