#!/usr/bin/env python3
"""Validate credential metadata and calculate the current reminder stage."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("administrator"), str) or not data["administrator"]:
        raise ValueError("administrator must be a non-empty GitHub login")

    thresholds = data.get("reminder_days")
    if (
        not isinstance(thresholds, list)
        or not thresholds
        or any(not isinstance(value, int) or value < 0 for value in thresholds)
        or thresholds != sorted(set(thresholds), reverse=True)
    ):
        raise ValueError("reminder_days must be unique non-negative integers in descending order")

    credentials = data.get("credentials")
    if not isinstance(credentials, list) or not credentials:
        raise ValueError("credentials must be a non-empty list")

    seen_ids: set[str] = set()
    for credential in credentials:
        for field in ("id", "name", "environment", "expires_on"):
            if not isinstance(credential.get(field), str) or not credential[field]:
                raise ValueError(f"credential {field} must be a non-empty string")
        if credential["id"] in seen_ids:
            raise ValueError(f"duplicate credential id: {credential['id']}")
        seen_ids.add(credential["id"])
        dt.date.fromisoformat(credential["expires_on"])

    return data


def reminders_for(data: dict, today: dt.date) -> list[dict]:
    reminders: list[dict] = []
    thresholds: list[int] = data["reminder_days"]

    for credential in data["credentials"]:
        expires_on = dt.date.fromisoformat(credential["expires_on"])
        days_remaining = (expires_on - today).days
        stage: str | None = None

        if days_remaining < 0:
            # A date-specific stage deliberately generates one administrator
            # notification per overdue day until the manifest is updated.
            stage = f"overdue-{today.isoformat()}"
        else:
            for threshold in thresholds:
                if days_remaining <= threshold:
                    stage = str(threshold)

        if stage is not None:
            reminders.append(
                {
                    **credential,
                    "days_remaining": days_remaining,
                    "stage": stage,
                    "critical": days_remaining <= 14,
                }
            )

    return reminders


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--today", type=dt.date.fromisoformat)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    data = load_manifest(args.manifest)
    if args.validate_only:
        return

    today = args.today or dt.datetime.now(dt.timezone.utc).date()
    print(
        json.dumps(
            {
                "administrator": data["administrator"],
                "today": today.isoformat(),
                "reminders": reminders_for(data, today),
            }
        )
    )


if __name__ == "__main__":
    main()
