# 主要作用：按 A、B、C 角色范围执行工程设计变更审计，并从本地制度向量索引读取对应制度证据。

from pathlib import Path
import json
import sys

from agents.audit_rules import audit_all
from agents.load_database import load_database
from agents.roles import filter_database_for_role


ROOT_DIR = Path(__file__).resolve().parent.parent
VECTOR_INDEX_PATH = ROOT_DIR / "RAG" / "vector_index.json"

AUDITED_FIELDS = [
    "project_number",
    "contract_number",
    "change_number",
    "estimate_amount",
    "approved_amount",
    "cumulative_estimate",
    "cumulative_approved",
    "contract_total",
    "technical_committee",
    "expert_review",
    "sunshine_publicity",
    "warning_90",
]

RULE_EVIDENCE_IDS = {
    "累计金额核对": [
        "02-0044",
    ],
    "阳光采购平台公示": [
        "02-0022",
        "02-0044",
    ],
    "工程技术委员会审批": [
        "02-0013",
        "02-0014",
    ],
    "审批流程核验": [
        "02-0014",
        "02-0035",
        "02-0036",
    ],
    "制度冲突检查": [
        "02-0006",
        "02-0014",
        "02-0022",
    ],
    "先批后建核验": [
        "02-0006",
        "02-0035",
    ],
}


def load_policy_evidence(findings):
    vector_index = json.loads(
        VECTOR_INDEX_PATH.read_text(encoding="utf-8")
    )
    chunks = {
        chunk["chunk_id"]: chunk
        for chunk in vector_index["chunks"]
    }
    evidence = {}
    rules = sorted({finding["rule"] for finding in findings})

    for rule in rules:
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
            for chunk_id in RULE_EVIDENCE_IDS[rule]
        ]

    return evidence


def run_audit(role):
    database = load_database()
    visible_database = filter_database_for_role(database, role)
    findings = audit_all(visible_database)
    policy_evidence = load_policy_evidence(findings)

    return {
        "role": role,
        "all_policies_accessible": True,
        "audited_fields": AUDITED_FIELDS,
        "visible_project_numbers": [
            project["project_number"]
            for project in visible_database["projects"]
        ],
        "project_count": len(visible_database["projects"]),
        "change_count": len(visible_database["changes"]),
        "committee_review_count": len(
            visible_database["committee_reviews"]
        ),
        "finding_count": len(findings),
        "findings": findings,
        "policy_evidence": policy_evidence,
    }


def main():
    role = sys.argv[1]
    result = run_audit(role)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()