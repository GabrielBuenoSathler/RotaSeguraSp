#!/usr/bin/env python3
"""Measure a CI command, preserve its exit status and record a job summary."""

import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Uso: ci_step.py NOME COMANDO [ARGUMENTOS...]")
    name, *command = sys.argv[1:]
    started = perf_counter()
    try:
        code = subprocess.run(command, check=False).returncode
    except OSError:
        code = 127
    seconds = round(perf_counter() - started, 3)
    record = {"step": name, "seconds": seconds, "exit_code": code}
    path = Path(os.getenv("CI_TIMINGS_FILE", ".ci-metrics/timings.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as output:
        output.write(json.dumps(record) + "\n")
    if summary := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary, "a") as output:
            output.write(f"- {name}: **{seconds:.2f}s**, saída `{code}`\n")
    print(f"{name}: {seconds:.2f}s (saída {code})", flush=True)
    raise SystemExit(code if code >= 0 else 128 - code)


if __name__ == "__main__":
    main()
