# 主要作用：按角色、项目或变更编号执行设计变更合规审计，并返回制度证据与原始核验数据。

from pathlib import Path
import json
import sys

from agents.audit_rules import audit_all, audit_change_record
from agents.load_database import load_database
from agents.roles import filter_database_for_role


ROOT_DIR = Path(__file__).resolve().parent.parent
VECTOR_INDEX_PATH = ROOT_DIR / "RAG" / "vector_index.json"

RULE_EVIDENCE_IDS = {
    "阳光采购平台公示": ["02-0022", "02-0044"],
    "工程技术委员会审批": ["02-0013", "02-0014"],
    "审批流程核验": ["02-0014", "02-0035", "02-0036"],
}


def load_policy_evidence(findings):
    vector_index = json.loads(VECTOR_INDEX_PATH.read_text(encoding="utf-8"))
    chunks = {chunk["chunk_id"]: chunk for chunk in vector_index["chunks"]}
    evidence = {}
    for rule in sorted({finding["rule"] for finding in findings}):
        evidence[rule] = [
            {
                "chunk_id": chunks[chunk_id]["chunk_id"],
                "source_file": chunks[chunk_id]["source_file"],
                "article": chunks[chunk_id]["article"],
                "article_title": chunks[chunk_id]["article_title"],
                "page_start": chunks[chunk_id]["page_start"],
                "page_end": chunks[chunk_id]["page_end"],
                "text": chunks[chunk_id]["text"],
            }
            for chunk_id in RULE_EVIDENCE_IDS.get(rule, [])
        ]
    return evidence


def project_matches(project_name, target_project_name):
    project_text = str(project_name).replace(" ", "")
    target_text = str(target_project_name).replace(" ", "")
    project_core = project_text.removesuffix("项目")
    target_core = target_text.removesuffix("项目")
    return target_text in project_text or project_text in target_text or target_core in project_core or project_core in target_core


def filter_database_for_project(database, project_name):
    return {
        key: [item for item in database[key] if project_matches(item.get("project_name", ""), project_name)]
        for key in ["projects", "changes", "committee_reviews", "approval_records"]
    }


def filter_database_for_change(database, change_number):
    change = [item for item in database["changes"] if item["change_number"] == change_number]
    project_numbers = {item["project_number"] for item in change}
    return {
        "projects": [item for item in database["projects"] if item["project_number"] in project_numbers],
        "changes": change,
        "committee_reviews": [item for item in database["committee_reviews"] if item["change_number"] == change_number],
        "approval_records": [item for item in database["approval_records"] if item["change_number"] == change_number],
    }


def run_audit(role, project_name=None, change_number=None):
    database = filter_database_for_role(load_database(), role)
    if change_number:
        visible_database = filter_database_for_change(database, change_number)
    elif project_name:
        visible_database = filter_database_for_project(database, project_name)
    else:
        visible_database = database
    findings = audit_all(visible_database)
    return {
        "role": role, "project_name": project_name, "change_number": change_number,
        "project_count": len(visible_database["projects"]),
        "change_count": len(visible_database["changes"]),
        "committee_review_count": len(visible_database["committee_reviews"]),
        "approval_record_count": len(visible_database["approval_records"]),
        "visible_project_numbers": [item["project_number"] for item in visible_database["projects"]],
        "findings": findings, "finding_count": len(findings),
        "database": visible_database, "policy_evidence": load_policy_evidence(findings),
    }


def audit_change(change_number, role):
    return run_audit(role, change_number=change_number)


def main():
    role = sys.argv[1]
    target = " ".join(sys.argv[2:]) or None
    result = run_audit(role, change_number=target if target and "-BG-" in target else None, project_name=target if target and "-BG-" not in target else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
