import json
import os
import sys
from typing import Any

from openai import AzureOpenAI

from ddl_parser import extract_ddls, split_sql_statements

print("Starting AI DDL Classification...")

DDL_ARTIFACT = "ddl_output.json"
CLASSIFICATION_ARTIFACT = "ddl_classification.json"
AZURE_OPENAI_API_VERSION = "2024-02-15-preview"

SYSTEM_PROMPT = """You are an expert Databricks Delta Lake schema change reviewer.

Your task is to classify every DDL statement in the input as REVERSIBLE or IRREVERSIBLE.

Definitions:
- REVERSIBLE: the rollback can be produced directly from the DDL statement itself without needing lost data, prior schema snapshots, or external metadata.
- IRREVERSIBLE: the rollback needs reconstruction, prior metadata, or lost state may not be recoverable from the DDL alone.

You must handle any combination of DDL commands, including mixed CREATE, ALTER, DROP, TRUNCATE, RENAME, property changes, constraints, comments, ownership, location, partitions, views, schemas, and other DDL variants.

Classification principles:
- CREATE TABLE is usually REVERSIBLE because it can be rolled back with DROP TABLE when the table is newly created by the migration.
- ALTER TABLE ADD COLUMN / ADD COLUMNS is usually REVERSIBLE.
- ALTER TABLE RENAME COLUMN or RENAME TO is usually REVERSIBLE.
- DROP TABLE is IRREVERSIBLE.
- TRUNCATE TABLE is IRREVERSIBLE.
- ALTER TABLE DROP COLUMN is IRREVERSIBLE.
- ALTER TABLE ALTER COLUMN TYPE is IRREVERSIBLE unless the previous type is explicitly recoverable from the statement itself.
- Any statement that discards data, discards schema details, or depends on prior metadata must be IRREVERSIBLE.

Return valid JSON only.

Required JSON shape:
{
  "statements": [
    {
      "id": "ddl_1",
      "classification": "CREATE_TABLE|ALTER_TABLE|DROP_TABLE|TRUNCATE_TABLE|DDL_OTHER",
      "reversibility": "REVERSIBLE|IRREVERSIBLE",
      "rollback_strategy": "DIRECT_REVERSE|AI_RECONSTRUCT",
      "reason": "short explanation"
    }
  ]
}

Rules:
- Return exactly one object in "statements" for each input statement id.
- Preserve the same ids from the input.
- Keep reasons short and concrete.
- If uncertain, prefer IRREVERSIBLE.
"""


def emit_outputs(is_drop: bool, rollback_type: str) -> None:
    print(f"##vso[task.setvariable variable=IS_DROP;isOutput=true]{str(is_drop).lower()}")
    print(f"##vso[task.setvariable variable=ROLLBACK_TYPE;isOutput=true]{rollback_type}")


def load_migrations() -> list[dict[str, Any]]:
    if not os.path.exists(DDL_ARTIFACT):
        print("No ddl_output.json found — skipping classification")
        emit_outputs(False, "NONE")
        sys.exit(0)

    with open(DDL_ARTIFACT) as f:
        payload = json.load(f)

    migrations = payload.get("migrations", [])
    if not migrations:
        print("No migration scripts found in ddl_output.json")
        emit_outputs(False, "NONE")
        sys.exit(0)

    return migrations


def collect_ddls(migrations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_ddls = []

    for migration in migrations:
        script_name = migration.get("script_name", "<unknown>")
        path = migration.get("path")

        if not path or not os.path.exists(path):
            print(f"Skipping missing migration file: {script_name}")
            continue

        with open(path) as f:
            sql_text = f.read()

        statements = split_sql_statements(sql_text)
        ddls = extract_ddls(statements)

        print(f"{script_name}: found {len(ddls)} DDL command(s)")
        for ddl in ddls:
            print(f"  - {ddl['statement']}")
            all_ddls.append(
                {
                    "id": ddl["id"],
                    "script_name": script_name,
                    "path": path,
                    "statement": ddl["statement"],
                    "type": ddl.get("type"),
                    "table": ddl.get("table"),
                }
            )

    if not all_ddls:
        print("No DDL statements found")
        emit_outputs(False, "NONE")
        sys.exit(0)

    return all_ddls


def build_user_prompt(ddls: list[dict[str, Any]]) -> str:
    prompt_payload = {
        "instructions": [
            "Classify each DDL statement as reversible or irreversible.",
            "Use the provided id for each result.",
            "Decide rollback_strategy as DIRECT_REVERSE for reversible statements or AI_RECONSTRUCT for irreversible statements.",
        ],
        "ddl_statements": [
            {
                "id": ddl["id"],
                "script_name": ddl["script_name"],
                "statement": ddl["statement"],
            }
            for ddl in ddls
        ],
    }
    return json.dumps(prompt_payload, indent=2)


def get_ai_client() -> AzureOpenAI:
    return AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    )


def classify_with_ai(ddls: list[dict[str, Any]]) -> dict[str, Any]:
    client = get_ai_client()
    deployment_name = os.environ["AZURE_DEPLOYMENT_NAME"]

    response = client.chat.completions.create(
        model=deployment_name,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(ddls)},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Azure OpenAI returned an empty classification response")

    result = json.loads(content)
    if not isinstance(result, dict) or "statements" not in result:
        raise ValueError("Azure OpenAI response is missing the 'statements' field")

    if not isinstance(result["statements"], list):
        raise ValueError("Azure OpenAI response 'statements' must be a list")

    return result


def normalize_classification(value: str) -> str:
    normalized = (value or "").strip().upper()
    allowed = {
        "CREATE_TABLE",
        "ALTER_TABLE",
        "DROP_TABLE",
        "TRUNCATE_TABLE",
        "DDL_OTHER",
    }
    return normalized if normalized in allowed else "DDL_OTHER"


def normalize_reversibility(value: str) -> str:
    normalized = (value or "").strip().upper()
    return normalized if normalized in {"REVERSIBLE", "IRREVERSIBLE"} else "IRREVERSIBLE"


def normalize_rollback_strategy(value: str, reversibility: str) -> str:
    normalized = (value or "").strip().upper()
    if normalized in {"DIRECT_REVERSE", "AI_RECONSTRUCT"}:
        return normalized
    return "DIRECT_REVERSE" if reversibility == "REVERSIBLE" else "AI_RECONSTRUCT"


def merge_ai_results(
    ddls: list[dict[str, Any]],
    ai_result: dict[str, Any],
) -> list[dict[str, Any]]:
    ai_by_id = {}

    for item in ai_result["statements"]:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if item_id:
            ai_by_id[item_id] = item

    classified_ddls = []

    for ddl in ddls:
        ai_item = ai_by_id.get(ddl["id"])
        if not ai_item:
            raise ValueError(f"Missing AI classification for statement id {ddl['id']}")

        reversibility = normalize_reversibility(ai_item.get("reversibility", ""))
        classified_ddls.append(
            {
                "id": ddl["id"],
                "script_name": ddl["script_name"],
                "path": ddl["path"],
                "statement": ddl["statement"],
                "table": ddl.get("table"),
                "classification": normalize_classification(ai_item.get("classification", "")),
                "reversibility": reversibility,
                "rollback_strategy": normalize_rollback_strategy(
                    ai_item.get("rollback_strategy", ""),
                    reversibility,
                ),
                "reason": (ai_item.get("reason") or "").strip(),
            }
        )

    return classified_ddls


def summarize_results(classified_ddls: list[dict[str, Any]]) -> tuple[str, str, str, bool]:
    classification_names = [item["classification"] for item in classified_ddls]
    reversibility_names = [item["reversibility"] for item in classified_ddls]

    distinct_classifications = {name for name in classification_names if name != "DDL_OTHER"}
    if len(distinct_classifications) > 1:
        final_classification = "MIXED_DDL"
    elif distinct_classifications:
        final_classification = next(iter(distinct_classifications))
    elif classification_names:
        final_classification = "DDL_OTHER"
    else:
        final_classification = "NONE"

    if reversibility_names and all(name == "REVERSIBLE" for name in reversibility_names):
        reversibility_summary = "REVERSIBLE"
        rollback_type = "DIRECT_REVERSE"
    elif any(name == "IRREVERSIBLE" for name in reversibility_names):
        reversibility_summary = "IRREVERSIBLE"
        rollback_type = "AI_RECONSTRUCT"
    else:
        reversibility_summary = "UNKNOWN"
        rollback_type = "NONE"

    is_drop = any(item["classification"] == "DROP_TABLE" for item in classified_ddls)
    return final_classification, reversibility_summary, rollback_type, is_drop


def persist_classification_artifact(
    classified_ddls: list[dict[str, Any]],
    final_classification: str,
    reversibility_summary: str,
    rollback_type: str,
    is_drop: bool,
) -> None:
    with open(CLASSIFICATION_ARTIFACT, "w") as f:
        json.dump(
            {
                "final_classification": final_classification,
                "reversibility_summary": reversibility_summary,
                "rollback_type": rollback_type,
                "is_drop": is_drop,
                "statements": classified_ddls,
            },
            f,
            indent=2,
        )


def main() -> None:
    migrations = load_migrations()
    ddls = collect_ddls(migrations)

    print("Sending DDL batch to Azure OpenAI for reversibility classification...")
    ai_result = classify_with_ai(ddls)
    classified_ddls = merge_ai_results(ddls, ai_result)

    for item in classified_ddls:
        print(f"{item['script_name']} :: {item['id']}")
        print(f"  Classification: {item['classification']}")
        print(f"  Reversibility: {item['reversibility']}")
        print(f"  Rollback Strategy: {item['rollback_strategy']}")
        if item["reason"]:
            print(f"  Reason: {item['reason']}")

    (
        final_classification,
        reversibility_summary,
        rollback_type,
        is_drop,
    ) = summarize_results(classified_ddls)

    persist_classification_artifact(
        classified_ddls,
        final_classification,
        reversibility_summary,
        rollback_type,
        is_drop,
    )

    print("Final Classification:", final_classification)
    print("Reversibility Summary:", reversibility_summary)
    print("Rollback Type:", rollback_type)
    print("Is Drop:", is_drop)

    emit_outputs(is_drop, rollback_type)


if __name__ == "__main__":
    main()
