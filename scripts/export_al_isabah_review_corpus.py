#!/usr/bin/env python3
"""Export the available al-Isabah work to Sabiqah's protected reading contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCE_REF = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178"
SOURCE_COMMIT = "a3b76bfc72cc9d5d8f6d7d26f249f2f32b0ef178"
CORPUS_ID = "al-isabah-reading-a3b76bf-v3"
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
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
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
        source_artifact_id = f"al-isabah:entry:{sequence}"
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
        "schemaVersion": "2.0.0",
        "corpusId": CORPUS_ID,
        "id": entry["id"],
        "kind": "entry",
        "sequence": sequence,
        "printedEntryNumber": sequence,
        "volume": int(segments[0]["volume"]),
        "title": {
            "en": entry["title"]["english"],
            "ar": entry["title"]["arabic_observed"],
        },
        "translationState": translation["state"],
        "machineAssessment": translation["machine_assessment"],
        "humanReview": translation["human_review"],
        "segments": [
            {
                "id": segment["id"],
                "arabic": segment["arabic"],
                "english": segment["english"],
                "pages": [
                    {
                        "volume": int(segment["volume"]),
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
        "schemaVersion": "2.0.0",
        "corpusId": CORPUS_ID,
        "id": f"isabah-passage-{hashlib.sha256(value['result_id'].encode('utf-8')).hexdigest()[:12]}",
        "kind": "passage",
        "sequence": sequence,
        "printedEntryNumber": None,
        "volume": int(pages[0]["volume"]),
        "title": {"en": title_en, "ar": title_ar},
        "relationship": source["relationship"],
        "rationale": source["rationale"],
        "translationState": "translated",
        "machineAssessment": "needs_attention" if unresolved else "passed",
        "humanReview": "unreviewed",
        "segments": [
            {
                "id": f"isabah-passage-{hashlib.sha256(value['result_id'].encode('utf-8')).hexdigest()[:12]}-segment-0001",
                "arabic": classified_value["relevant_arabic"],
                "english": value["english_text"],
                "pages": [
                    {
                        "volume": int(page["volume"]),
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
            "sourceArtifactId": f"al-isabah:passage:{value['result_id']}",
            "sourceArtifactSha256": source["source"]["text_sha256"],
        },
    }


def printed_page_bounds(item: dict[str, Any]) -> tuple[int | None, int | None]:
    pages = [
        page["printedPage"]
        for segment in item["segments"]
        for page in segment["pages"]
        if page["printedPage"] is not None
    ]
    return (min(pages), max(pages)) if pages else (None, None)


def list_item(item: dict[str, Any], section_id: str) -> dict[str, Any]:
    page_start, page_end = printed_page_bounds(item)
    return {
        "id": item["id"],
        "kind": item["kind"],
        "sequence": item["sequence"],
        "printedEntryNumber": item["printedEntryNumber"],
        "volume": item["volume"],
        "printedPageStart": page_start,
        "printedPageEnd": page_end,
        "sectionId": section_id,
        "titleEn": item["title"]["en"],
        "titleAr": item["title"]["ar"],
        "translationState": item["translationState"],
        "machineAssessment": item["machineAssessment"],
        "humanReview": item["humanReview"],
        "unresolvedCount": len(item["unresolved"]),
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
        for path in git(git_dir, "ls-tree", "-r", "--name-only", SOURCE_REF, "content/entries").splitlines()
        if path.endswith(".json")
    ]
    context = git_json(
        git_dir,
        SOURCE_REF,
        "derived/cohorts/khadijah-immediate.context-adjudicated.json",
    )
    cohort_blind = git_json(
        git_dir, SOURCE_REF, "derived/cohorts/khadijah-immediate.blind.json"
    )
    cohort_critic = git_json(
        git_dir, SOURCE_REF, "derived/cohorts/khadijah-immediate.critic.json"
    )
    cohort_adjudicated = git_json(
        git_dir, SOURCE_REF, "derived/cohorts/khadijah-immediate.adjudicated.json"
    )
    context_blind = git_json(
        git_dir, SOURCE_REF, "derived/cohorts/khadijah-immediate.context-blind.json"
    )
    context_critic = git_json(
        git_dir, SOURCE_REF, "derived/cohorts/khadijah-immediate.context-critic.json"
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
        SOURCE_REF,
        "derived/cohorts/khadijah-immediate.mention-classification.json",
    )
    classified_by_context = {
        value["result_id"]: value
        for value in classifications["items"]
        if value["decision"] == "include_context"
    }

    items: list[dict[str, Any]] = []
    for path in entry_paths:
        entry = git_json(git_dir, SOURCE_REF, path)
        items.append(
            entry_item(
                entry,
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

    items.sort(
        key=lambda item: (
            item["volume"],
            printed_page_bounds(item)[0] or 10**9,
            item["printedEntryNumber"] or 10**9,
            item["sequence"],
        )
    )

    sections: list[dict[str, Any]] = []
    item_sections: dict[str, str] = {}
    volume_summaries: list[dict[str, Any]] = []
    for volume in sorted({item["volume"] for item in items}):
        volume_items = [item for item in items if item["volume"] == volume]
        availability = (
            "complete_translation" if volume == 8 else "selected_passages"
        )
        grouped: list[tuple[str, list[dict[str, Any]]]] = []
        if volume == 8:
            page_groups: dict[int, list[dict[str, Any]]] = {}
            for item in volume_items:
                page_start, _ = printed_page_bounds(item)
                bucket = ((page_start or 1) - 1) // 25
                page_groups.setdefault(bucket, []).append(item)
            for bucket, grouped_items in sorted(page_groups.items()):
                page_start = bucket * 25 + 1
                page_end = page_start + 24
                grouped.append(
                    (
                        f"volume-{volume:02d}-pages-{page_start:04d}-{page_end:04d}",
                        grouped_items,
                    )
                )
        else:
            grouped.append((f"volume-{volume:02d}-selected-passages", volume_items))

        total_sections = len(grouped)
        volume_pages = [
            page
            for item in volume_items
            for page in printed_page_bounds(item)
            if page is not None
        ]
        volume_summaries.append(
            {
                "id": f"volume-{volume:02d}",
                "number": volume,
                "label": f"Volume {volume}",
                "availability": availability,
                "itemCount": len(volume_items),
                "sectionCount": total_sections,
                "firstPrintedPage": min(volume_pages) if volume_pages else None,
                "lastPrintedPage": max(volume_pages) if volume_pages else None,
                "description": (
                    "Complete working translation, grouped into continuous reading sections."
                    if volume == 8
                    else "Selected translated passages; this is not a complete volume."
                ),
            }
        )
        for position, (section_id, section_items) in enumerate(grouped, start=1):
            section_pages = [
                page
                for item in section_items
                for page in printed_page_bounds(item)
                if page is not None
            ]
            section_start = min(section_pages) if section_pages else None
            section_end = max(section_pages) if section_pages else None
            previous_id = grouped[position - 2][0] if position > 1 else None
            next_id = grouped[position][0] if position < total_sections else None
            if volume == 8:
                _, bucket_start, bucket_end = section_id.rsplit("-", 2)
                label = f"Pages {int(bucket_start)}–{int(bucket_end)}"
            else:
                label = "Selected translated passages"
            section = {
                "schemaVersion": "2.0.0",
                "corpusId": CORPUS_ID,
                "id": section_id,
                "volume": volume,
                "label": label,
                "availability": availability,
                "position": position,
                "totalSections": total_sections,
                "printedPageStart": section_start,
                "printedPageEnd": section_end,
                "previousSectionId": previous_id,
                "nextSectionId": next_id,
                "items": section_items,
            }
            sections.append(section)
            for item in section_items:
                item_sections[item["id"]] = section_id

    list_items = [list_item(item, item_sections[item["id"]]) for item in items]
    translated = sum(item["translationState"] == "translated" for item in list_items)
    needs_attention = sum(item["machineAssessment"] == "needs_attention" for item in list_items)
    unresolved_count = sum(item["unresolvedCount"] for item in list_items)
    human_reviewed = sum(item["humanReview"] in {"reviewed", "verified"} for item in list_items)
    summary = {
        "schemaVersion": "2.0.0",
        "work": {
            "slug": "al-isabah",
            "titleAr": "الإصابة في تمييز الصحابة",
            "titleEn": "Al-Isabah fi Tamyiz al-Sahabah",
        },
        "corpus": {
            "id": CORPUS_ID,
            "sourceRepository": "https://github.com/yaqub0r/al-isabah",
            "sourceCommit": SOURCE_COMMIT,
            "generatedAt": generated_at,
            "promotionStatus": "blocked",
        },
        "counts": {
            "entries": len(entry_paths),
            "passages": len(context["items"]),
            "translated": translated,
            "needsAttention": needs_attention,
            "unresolvedItems": unresolved_count,
            "humanReviewed": human_reviewed,
        },
        "volumes": volume_summaries,
    }
    index = {
        "schemaVersion": "2.0.0",
        "corpusId": CORPUS_ID,
        "items": list_items,
    }
    write_json(output / "summary.json", summary)
    write_json(output / "index.json", index)
    for item in items:
        write_json(output / "items" / f"{item['id']}.json", item)
    for section in sections:
        write_json(output / "sections" / f"{section['id']}.json", section)

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
        "schemaVersion": "2.0.0",
        "corpusId": CORPUS_ID,
        "sourceCommit": SOURCE_COMMIT,
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
        f"{summary['counts']['passages']} passages to {args.output}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
