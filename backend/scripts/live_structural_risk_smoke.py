"""Opt-in real-model test: same-version duplication vs self-review. Uses API credits."""

import argparse
import json
import time
from io import BytesIO

import httpx
from docx import Document

BEFORE = [
    "1.1. Отдел закупок проводит закупки оборудования.",
    "1.2. Независимый отдел аудита проверяет закупки оборудования, проведённые отделом закупок.",
    "1.3. Отдел отчётности составляет и направляет руководителю ежемесячный сводный отчёт о закупках.",
]
AFTER = [
    "2.1. Отдел закупок проводит закупки оборудования.",
    "2.2. Отдел закупок независимо проверяет собственные закупки оборудования и утверждает результат проверки.",
    "2.3. Отдел отчётности составляет и направляет руководителю ежемесячный сводный отчёт о закупках.",
    "2.4. Отдел аналитики составляет и направляет тому же руководителю тот же ежемесячный сводный отчёт о закупках.",
    "2.5. Отдел отчётности и отдел аналитики независимо составляют полный отчёт каждый; разделение обязанностей между ними не предусмотрено.",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8010")
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()
    files = []
    for side, paragraphs in (("before", BEFORE), ("after", AFTER)):
        document = Document()
        for text in paragraphs:
            document.add_paragraph(text)
        buffer = BytesIO()
        document.save(buffer)
        files.append((f"{side}_files", (f"{side}.docx", buffer.getvalue(),
                                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document")))
    with httpx.Client(base_url=args.api_url.rstrip("/"), timeout=30) as client:
        response = client.post("/api/v1/analyses", files=files,
                               data={"title": "Синтетический тест: дублирование и самопроверка"})
        response.raise_for_status()
        analysis_id = response.json()["id"]
        print(f"Analysis: {analysis_id}", flush=True)
        started = time.monotonic()
        last = None
        live_trace_seen = False
        while time.monotonic() - started < args.timeout:
            response = client.get(f"/api/v1/analyses/{analysis_id}")
            response.raise_for_status()
            result = response.json()
            if result["status"] == "processing" and result.get("agent_trace"):
                live_trace_seen = True
            if result["current_step"] != last:
                last = result["current_step"]
                print(last, flush=True)
            if result["status"] in {"completed", "failed"}:
                break
            time.sleep(2)
        else:
            raise SystemExit("Timeout; the analysis may still be running on the server")
        if result["status"] != "completed":
            raise SystemExit("Analysis failed; inspect the run by ID")
        risks = result.get("structural_risks") or []
        checks = {
            "conflict_interest": any(
                r["kind"] == "conflict_interest"
                and {e["side"] for e in r["evidence"]} == {"after"}
                and {"2.1", "2.2"}.issubset({e["evidence"]["clause"] for e in r["evidence"]})
                for r in risks
            ),
            "duplicate": any(
                r["kind"] == "duplicate"
                and {e["side"] for e in r["evidence"]} == {"after"}
                and {"2.3", "2.4"}.issubset({e["evidence"]["clause"] for e in r["evidence"]})
                for r in risks
            ),
            "no_before_conflict": not any(
                r["kind"] == "conflict_interest" and any(e["side"] == "before" for e in r["evidence"])
                for r in risks
            ),
            "conclusion_includes_risks": "Потенциальный риск" in result["conclusion"],
            "live_trace_seen": live_trace_seen,
        }
        print(json.dumps({"passed": all(checks.values()), "checks": checks,
                          "seconds": round(time.monotonic() - started, 1),
                          "risk_count": len(risks)}, ensure_ascii=False, indent=2))
        if not all(checks.values()):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
