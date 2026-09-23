"""Evaluate the matcher using a completed run's registry, without repeating extraction."""

import argparse
import json
import time
from pathlib import Path

import httpx

from app.config import Settings
from app.registry import match_registry, reconcile_mappings
from app.schemas import FunctionRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_id")
    parser.add_argument("--api-url", default="http://localhost:8010")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    response = httpx.get(
        f"{args.api_url.rstrip('/')}/api/v1/analyses/{args.analysis_id}", timeout=30
    )
    response.raise_for_status()
    registry = FunctionRegistry.model_validate(response.json()["function_registry"])
    print("Before:", registry.coverage.model_dump(), flush=True)
    started = time.monotonic()
    links, added = match_registry(registry, Settings())
    result = reconcile_mappings(registry, links, added)
    print(
        json.dumps(
            {
                "seconds": round(time.monotonic() - started, 1),
                "decisions": len(links),
                "after": result.coverage.model_dump(),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print("Saved locally:", args.output)


if __name__ == "__main__":
    main()
