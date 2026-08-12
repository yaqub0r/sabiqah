#!/usr/bin/env python3
"""Export private al-Isabah research branches to the Sabiqah review contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VOLUME_REF = "20264a5ca018fe2a2890dc070f9c6bd904e3cb84"
COHORT_REF = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178"
COHORT_COMMIT = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178"
CORPUS_ID = "al-isabah-review-a3b76bf"
ARTIFACT_SHA = "f12585cea28d7c7b318728f74b1a95a0d8b2812cb25d6e70f1b9e7b0b9422a3f"


def git(git_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", f"--git-dir={git_dir}", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def git_json(git_dir: Path, ref: str, path: str) -> dict[str, Any]:
    value = json.loads(git(git_dir, "show", f"{ref}:{path}"))
    if not isinstance(value, dict):
        raise ValueError(f"{ref}:{path} must contain a JSON object")
    return value


def clean_output(output: Path) -> None:
    if output.exists():
        for path in sorted(output.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    output.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def normalized_unresolved(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "category": str(value.get("category", "unresolved")),
            **(
                {"arabicSpan": str(value["arabic_span"])}
                if value.get("arabic_span")
                else {}
            ),
            "explanation": str(value.get("explanation", "Review required.")),
            **(
                {"priority": str(value["human_review_priority"])}
                if value.get("human_review_priority")
                else {}
            ),
        }
        for value in values
    ]


def entry_item(
    entry: dict[str, Any],
    collection_ids: list[str],
    blind: dict[int, dict[str, Any]],
    critic: dict[int, dict[str, Any]],
    adjudicated: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    segments = entry["segments"]
    sequence = int(entry["printed_entry_number"])
    unresolved = normalized_unresolved(entry.get("unresolved", []))
    translation = entry["translation"]
    provenance = entry["provenance"]
    source_artifact_id = provenance.get("source_artifact_id")
    source_artifact_sha256 = provenance.get("source_artifact_sha256")
    if not source_artifact_id:
        source_artifact_id = (
            f"al-isabah:cohort:{provenance['cohort_id']}:entry:{sequence}"
        )
        source_artifact_sha256 = provenance["source_sha256"]
    workflow_stages: list[dict[str, Any]] = [
        {
            "stage": "source_alignment",
            "state": "complete",
            "summary": "The source segments are aligned to stable volume, page, and integrity references.",
        }
    ]
    if sequence in adjudicated:
        blind_value = blind[sequence]
        critic_value = critic[sequence]
        adjudicated_value = adjudicated[sequence]
        critic_issues = [
            {
                "severity": str(issue.get("severity", "notice")),
                "category": str(issue.get("category", "translation")),
                "explanation": str(issue.get("explanation", "Review required.")),
                **(
                    {"suggestedFix": str(issue["suggested_fix"])}
                    if issue.get("suggested_fix")
                    else {}
                ),
            }
            for issue in critic_value.get("issues", [])
        ]
        workflow_stages.extend(
            [
                {
                    "stage": "blind_translation",
                    "state": "complete",
                    "summary": "An independent blind English translation was produced from the locked Arabic source.",
                    "englishText": blind_value["english_text"],
                },
                {
                    "stage": "critique",
                    "state": "needs_attention" if critic_issues else "complete",
                    "summary": f"Independent criticism recorded {len(critic_issues)} issue(s).",
                    "issues": critic_issues,
                },
                {
                    "stage": "adjudication",
                    "state": "complete",
                    "summary": "The blind translation and critic findings were adjudicated into the current working translation.",
                    "englishText": adjudicated_value["english_text"],
                },
            ]
        )
    workflow_stages.extend(
        [
            {
                "stage": "machine_validation",
                "state": (
                    "needs_attention"
                    if translation["machine_assessment"] == "needs_attention"
                    else "complete"
                ),
                "summary": f"Machine assessment: {translation['machine_assessment'].replace('_', ' ')}.",
            },
            {
                "stage": "human_review",
                "state": (
                    "complete"
                    if translation["human_review"] in {"reviewed", "verified"}
                    else "pending"
                ),
                "summary": f"Human review: {translation['human_review'].replace('_', ' ')}.",
            },
            {
                "stage": "compliance_promotion",
                "state": "blocked",
                "summary": "Public promotion remains blocked by the source-compliance manifest.",
            },
        ]
    )
    return {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "id": entry["id"],
        "kind": "entry",
        "sequence": sequence,
        "printedEntryNumber": sequence,
        "volume": str(segments[0]["volume"]),
        "title": {
            "en": entry["title"]["english"],
            "ar": entry["title"]["arabic_observed"],
        },
        "translationState": translation["state"],
        "machineAssessment": translation["machine_assessment"],
        "humanReview": translation["human_review"],
        "collectionIds": collection_ids,
        "segments": [
            {
                "id": segment["id"],
                "arabic": segment["arabic"],
                "english": segment["english"],
                "pages": [
                    {
                        "volume": str(segment["volume"]),
                        "printedPage": segment.get("printed_page"),
                        "readerPage": segment.get("reader_page"),
                        "providerPage": segment.get("reader_url"),
                    }
                ],
                "machineState": segment["machine_state"],
            }
            for segment in segments
        ],
        "names": entry.get("names", []),
        "unresolved": unresolved,
        "workflowStages": workflow_stages,
        "provenance": {
            "sourceArtifactId": source_artifact_id,
            "sourceArtifactSha256": source_artifact_sha256,
        },
    }


def context_item(
    value: dict[str, Any],
    sequence: int,
    blind: dict[str, dict[str, Any]],
    critic: dict[str, dict[str, Any]],
    classified: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source = value["source"]
    pages = source["source"]["pages"]
    names = value.get("names", [])
    title_en = names[0]["english"] if names else source["relationship"]
    title_ar = names[0]["arabic"] if names else ""
    unresolved = normalized_unresolved(value.get("unresolved", []))
    blind_value = blind[value["result_id"]]
    critic_value = critic[value["result_id"]]
    classified_value = classified[value["result_id"]]
    critic_issues = [
        {
            "severity": str(issue.get("severity", "notice")),
            "category": str(issue.get("category", "translation")),
            "explanation": str(issue.get("explanation", "Review required.")),
            **(
                {"suggestedFix": str(issue["suggested_fix"])}
                if issue.get("suggested_fix")
                else {}
            ),
        }
        for issue in critic_value.get("issues", [])
    ]
    return {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "id": f"khadijah-context-{sequence:04d}",
        "kind": "context",
        "sequence": sequence,
        "printedEntryNumber": None,
        "volume": str(pages[0]["volume"]),
        "title": {"en": title_en, "ar": title_ar},
        "relationship": source["relationship"],
        "rationale": source["rationale"],
        "translationState": "translated",
        "machineAssessment": "needs_attention" if unresolved else "passed",
        "humanReview": "unreviewed",
        "collectionIds": ["khadijah-immediate", "khadijah-context"],
        "segments": [
            {
                "id": f"khadijah-context-{sequence:04d}-segment-0001",
                "arabic": classified_value["relevant_arabic"],
                "english": value["english_text"],
                "pages": [
                    {
                        "volume": str(page["volume"]),
                        "printedPage": int(page["page"]),
                        "readerPage": int(page["index"]) + 1,
                        "providerPage": f"https://usul.ai/t/isaba-fi-tamyiz/{int(page['index']) + 1}",
                    }
                    for page in pages
                ],
                "machineState": "machine_adjudicated_unreviewed",
            }
        ],
        "names": names,
        "unresolved": unresolved,
        "decisions": value.get("decisions", []),
        "workflowStages": [
            {
                "stage": "source_alignment",
                "state": "complete",
                "summary": "The contextual source block is locked to page and integrity references.",
            },
            {
                "stage": "blind_translation",
                "state": "complete",
                "summary": "An independent blind English translation was produced.",
                "englishText": blind_value["english_text"],
            },
            {
                "stage": "critique",
                "state": "needs_attention" if critic_issues else "complete",
                "summary": f"Independent criticism recorded {len(critic_issues)} issue(s).",
                "issues": critic_issues,
            },
            {
                "stage": "adjudication",
                "state": "complete",
                "summary": "Critic findings were adjudicated into the current working translation.",
                "englishText": value["english_text"],
            },
            {
                "stage": "machine_validation",
                "state": "needs_attention" if unresolved else "complete",
                "summary": f"The current record retains {len(unresolved)} unresolved item(s).",
            },
            {
                "stage": "human_review",
                "state": "pending",
                "summary": "Human review has not started.",
            },
            {
                "stage": "compliance_promotion",
                "state": "blocked",
                "summary": "Public promotion remains blocked by the source-compliance manifest.",
            },
        ],
        "provenance": {
            "sourceArtifactId": f"al-isabah:khadijah-context:{value['result_id']}",
            "sourceArtifactSha256": source["source"]["text_sha256"],
        },
    }


def list_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "kind": item["kind"],
        "sequence": item["sequence"],
        "printedEntryNumber": item["printedEntryNumber"],
        "volume": item["volume"],
        "titleEn": item["title"]["en"],
        "titleAr": item["title"]["ar"],
        "translationState": item["translationState"],
        "machineAssessment": item["machineAssessment"],
        "humanReview": item["humanReview"],
        "unresolvedCount": len(item["unresolved"]),
        "collectionIds": item["collectionIds"],
        **(
            {"relationship": item["relationship"]}
            if item.get("relationship")
            else {}
        ),
    }


def export(git_dir: Path, output: Path, generated_at: str) -> dict[str, Any]:
    clean_output(output)
    entry_paths = [
        path
        for path in git(git_dir, "ls-tree", "-r", "--name-only", COHORT_REF, "content/entries").splitlines()
        if path.endswith(".json")
    ]
    volume_ids = set(
        path.rsplit("/", 1)[-1].removesuffix(".json")
        for path in git(git_dir, "ls-tree", "-r", "--name-only", VOLUME_REF, "content/entries").splitlines()
        if path.endswith(".json")
    )
    cohort_bundle = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.bundle.json"
    )
    cohort_ids = {entry["id"] for entry in cohort_bundle["entries"]}
    context = git_json(
        git_dir,
        COHORT_REF,
        "derived/cohorts/khadijah-immediate.context-adjudicated.json",
    )
    cohort_blind = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.blind.json"
    )
    cohort_critic = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.critic.json"
    )
    cohort_adjudicated = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.adjudicated.json"
    )
    context_blind = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.context-blind.json"
    )
    context_critic = git_json(
        git_dir, COHORT_REF, "derived/cohorts/khadijah-immediate.context-critic.json"
    )
    blind_by_entry = {int(value["entry_number"]): value for value in cohort_blind["entries"]}
    critic_by_entry = {int(value["entry_number"]): value for value in cohort_critic["entries"]}
    adjudicated_by_entry = {
        int(value["entry_number"]): value for value in cohort_adjudicated["entries"]
    }
    blind_by_context = {value["result_id"]: value for value in context_blind["items"]}
    critic_by_context = {value["result_id"]: value for value in context_critic["items"]}
    classifications = git_json(
        git_dir,
        COHORT_REF,
        "derived/cohorts/khadijah-immediate.mention-classification.json",
    )
    classified_by_context = {
        value["result_id"]: value
        for value in classifications["items"]
        if value["decision"] == "include_context"
    }

    items: list[dict[str, Any]] = []
    for path in entry_paths:
        entry = git_json(git_dir, COHORT_REF, path)
        collections: list[str] = []
        if entry["id"] in volume_ids:
            collections.append("volume-08")
        if entry["id"] in cohort_ids:
            collections.append("khadijah-immediate")
        if not collections:
            raise ValueError(f"{entry['id']} is not assigned to a review collection")
        items.append(
            entry_item(
                entry,
                collections,
                blind_by_entry,
                critic_by_entry,
                adjudicated_by_entry,
            )
        )
    for index, value in enumerate(context["items"], start=1):
        items.append(
            context_item(
                value,
                index,
                blind_by_context,
                critic_by_context,
                classified_by_context,
            )
        )

    list_items = sorted((list_item(item) for item in items), key=lambda x: (x["kind"], x["sequence"]))
    translated = sum(item["translationState"] == "translated" for item in list_items)
    needs_attention = sum(item["machineAssessment"] == "needs_attention" for item in list_items)
    unresolved_count = sum(item["unresolvedCount"] for item in list_items)
    human_reviewed = sum(item["humanReview"] in {"reviewed", "verified"} for item in list_items)
    decisions: dict[str, int] = {}
    for result in classifications["items"]:
        decision = str(result["decision"])
        decisions[decision] = decisions.get(decision, 0) + 1

    summary = {
        "schemaVersion": "1.0.0",
        "work": {
            "slug": "al-isabah",
            "titleAr": "الإصابة في تمييز الصحابة",
            "titleEn": "Al-Isabah fi Tamyiz al-Sahabah",
        },
        "corpus": {
            "id": CORPUS_ID,
            "sourceRepository": "https://github.com/yaqub0r/al-isabah",
            "sourceCommit": COHORT_COMMIT,
            "generatedAt": generated_at,
            "promotionStatus": "blocked",
        },
        "counts": {
            "entries": len(entry_paths),
            "contextualPassages": len(context["items"]),
            "translated": translated,
            "needsAttention": needs_attention,
            "unresolvedItems": unresolved_count,
            "humanReviewed": human_reviewed,
        },
        "collections": [
            {
                "id": "volume-08",
                "title": "Volume 8",
                "kind": "volume",
                "itemCount": len(volume_ids),
                "reviewState": "unreviewed",
                "description": "Complete machine-validated Volume 8 translation awaiting human and compliance review.",
            },
            {
                "id": "khadijah-immediate",
                "title": "Khadijah and her immediate associates",
                "kind": "cohort",
                "itemCount": len(cohort_ids) + len(context["items"]),
                "reviewState": "unreviewed",
                "description": "Fifteen complete biographies and fourteen additional contextual passages ready for human review.",
            },
        ],
        "coverage": {
            "sourceResults": int(classifications["source_result_count"]),
            "decisions": decisions,
        },
    }
    index = {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "items": list_items,
    }
    write_json(output / "summary.json", summary)
    write_json(output / "index.json", index)
    for item in items:
        write_json(output / "items" / f"{item['id']}.json", item)

    manifest_files = []
    for path in sorted(path for path in output.rglob("*.json") if path.name != "manifest.json"):
        relative = path.relative_to(output).as_posix()
        manifest_files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schemaVersion": "1.0.0",
        "corpusId": CORPUS_ID,
        "sourceCommit": COHORT_COMMIT,
        "generatedAt": generated_at,
        "objectCount": len(manifest_files),
        "files": manifest_files,
    }
    write_json(output / "manifest.json", manifest)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()
    summary = export(args.git_dir.resolve(), args.output.resolve(), args.generated_at)
    print(
        f"Exported {summary['counts']['entries']} entries and "
        f"{summary['counts']['contextualPassages']} contexts to {args.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
