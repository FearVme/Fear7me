# 主要作用：定义 A、B、C 角色的项目数据访问范围，并过滤数据库数据供审计 Agent 使用。

import json
import sys

from agents.load_database import load_database


ROLE_PROJECT_NUMBERS = {
    "A": {
        "K2025-001",
    },
    "B": {
        "K2025-001",
        "K2026-002",
        "K2025-003",
    },
    "C": None,
}


def filter_database_for_role(database, role):
    allowed_project_numbers = ROLE_PROJECT_NUMBERS[role]

    if allowed_project_numbers is None:
        return database

    return {
        "projects": [
            project
            for project in database["projects"]
            if project["project_number"] in allowed_project_numbers
        ],
        "changes": [
            change
            for change in database["changes"]
            if change["project_number"] in allowed_project_numbers
        ],
        "committee_reviews": [
            review
            for review in database["committee_reviews"]
            if review["project_number"] in allowed_project_numbers
        ],
        "approval_records": [
            record
            for record in database["approval_records"]
            if record["project_number"] in allowed_project_numbers
        ],
    }


def main():
    role = sys.argv[1]
    database = load_database()
    visible_database = filter_database_for_role(database, role)

    print(
        json.dumps(
            {
                "role": role,
                "all_policies_accessible": True,
                "project_count": len(visible_database["projects"]),
                "change_count": len(visible_database["changes"]),
                "committee_review_count": len(
                    visible_database["committee_reviews"]
                ),
                "project_numbers": [
                    project["project_number"]
                    for project in visible_database["projects"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
