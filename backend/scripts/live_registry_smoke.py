"""Opt-in smoke test through a running API. Uses real model credits; no customer data."""

import argparse
import json
import time
from io import BytesIO

import httpx
from docx import Document

BEFORE = [
    "Общие положения",
    "1.1. Отдел контроля готовит ежемесячный отчёт о рисках.",
    "1.2. Отдел контроля ведёт реестр нарушений.",
    "1.3. Отдел контроля проверяет соблюдение сроков закупок.",
    "1.4. Отдел контроля хранит утверждённые протоколы проверок.",
]
AFTER = [
    "Общие положения",
    "9.1. Отдел контроля готовит ежеквартальный отчёт о рисках.",
    "9.2. Департамент данных ведёт реестр нарушений.",
    "9.3. Отдел контроля публикует сводку инцидентов.",
    "9.4. Отдел контроля хранит утверждённые протоколы проверок.",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8010")
    parser.add_argument("--timeout", type=int, default=360)
    args = parser.parse_args()
    files = []
    for side, paragraphs in (("before", BEFORE), ("after", AFTER)):
        document = Document()
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
        buffer = BytesIO()
        document.save(buffer)
        files.append(
            (
                f"{side}_files",
                (
                    f"{side}.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            )
        )
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=20) as client:
        response = client.post(
            "/api/v1/analyses",
            files=files,
            data={"title": "Контрольный пример: пять исходов функций"},
        )
        response.raise_for_status()
        analysis_id = response.json()["id"]
        print(f"Analysis: {analysis_id}", flush=True)
        started = time.monotonic()
        previous = None
        while time.monotonic() - started < args.timeout:
            response = client.get(f"/api/v1/analyses/{analysis_id}")
            response.raise_for_status()
            result = response.json()
            if result["current_step"] != previous:
                previous = result["current_step"]
                print(previous, flush=True)
            if result["status"] in {"completed", "failed"}:
                break
            time.sleep(2)
        else:
            raise SystemExit("Timeout waiting for analysis; the server job may still be running.")
        if result["status"] != "completed":
            raise SystemExit("Analysis failed; inspect the run in the UI.")
        registry = result["function_registry"]
        functions = {item["id"]: item for item in registry["functions"]}
        decisions = {
            functions[row["before_id"]]["evidence"]["clause"]: row["status"]
            for row in registry["mappings"]
            if row["before_id"]
        }
        added = {
            functions[target]["evidence"]["clause"]
            for row in registry["mappings"]
            if row["status"] == "added"
            for target in row["after_ids"]
        }
        expected = {"1.1": "changed", "1.2": "moved", "1.3": "lost", "1.4": "unchanged"}
        passed = decisions == expected and added == {"9.3"}
        passed = passed and registry["coverage"]["unresolved_fragments"] == 0
        print(
            json.dumps(
                {
                    "passed": passed,
                    "seconds": round(time.monotonic() - started, 1),
                    "coverage": registry["coverage"],
                    "expected": expected,
                    "actual": decisions,
                    "added_clauses": sorted(added),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if not passed:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
