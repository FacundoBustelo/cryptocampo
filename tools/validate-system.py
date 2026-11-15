#!/usr/bin/env python3
"""Ejecuta controles independientes y conserva logs y códigos incluso ante fallos."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def now():
    return datetime.now(timezone.utc).isoformat()


def run_check(output, name, command, timeout=300):
    started = now()
    log = output / f"{name}.txt"
    with log.open("w") as stream:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    text=True, timeout=timeout)
            code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write(f"\nTiempo máximo excedido: {timeout}s\n")
            code = 124
        except OSError as error:
            stream.write(f"{type(error).__name__}: {error}\n")
            code = 127
    record = {"name": name, "command": command, "started_at": started, "finished_at": now(),
              "exit_code": code, "status": "passed" if code == 0 else "failed", "log": log.name}
    print(f"{name}: {record['status']} (exit {code}); {log}", flush=True)
    return record


def source_hashes():
    paths = [ROOT / "foundry.toml", ROOT / "README.md", ROOT / "Makefile"]
    for folder in ("src", "test", "script", "tools", "assets", ".github/workflows"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tools/validation" /
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    args = parser.parse_args()
    output = args.output_dir.resolve()
    # Un directorio nuevo impide confundir resultados anteriores con esta ejecución.
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "started_at": now(), "cwd": str(ROOT),
              "platform": platform.platform(), "python": sys.version,
              "ci": {k: os.environ.get(k) for k in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")},
              "source_sha256": source_hashes(), "checks": [], "status": "running"}

    def save():
        (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    def check(name, command, dependency=None):
        if dependency is not None and dependency["status"] != "passed":
            record = {"name": name, "command": command, "exit_code": None, "status": "skipped",
                      "reason": f"Falló el requisito {dependency['name']}"}
        else:
            record = run_check(output, name, command)
        report["checks"].append(record)
        save()
        return record

    save()
    check("commit", ["git", "rev-parse", "HEAD"])
    check("working-tree", ["git", "status", "--short"])
    check("diff", ["git", "diff", "--no-ext-diff", "HEAD"])
    for library in ("openzeppelin-contracts", "forge-std"):
        check(f"{library}-revision", ["git", "-C", f"lib/{library}", "rev-parse", "HEAD"])
        check(f"{library}-status", ["git", "-C", f"lib/{library}", "status", "--porcelain"])
    forge = ".tools/bin/forge"
    for binary in ("forge", "anvil", "cast"):
        check(f"{binary}-version", [f".tools/bin/{binary}", "--version"])
    check("metadata-local", [sys.executable, "tools/verify-metadata.py", "--local-only",
                             "--output-dir", str(output / "metadata-local")])
    check("python-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py", "-v"])
    check("format", [forge, "fmt", "--check"])
    build = check("build", [forge, "build", "--force", "--color", "never"])
    check("solidity-tests", [forge, "test", "-vv", "--color", "never"], build)
    coverage = check("coverage", [forge, "coverage", "--report", "summary", "--report", "debug",
                                  "--color", "never"], build)
    check("coverage-summary", [sys.executable, "tools/summarize-coverage.py", str(output / "coverage.txt"),
                               "--check-baseline"], coverage)
    # Coverage deshabilita el optimizador: restaurarlo antes de ambos informes de gas.
    optimized = check("optimized-build", [forge, "build", "--force", "--color", "never"], build)
    check("gas-report", [forge, "test", "--gas-report", "--color", "never"], optimized)
    matrix = check("gas-matrix", [sys.executable, "tools/measure-gas.py"], optimized)
    if matrix["status"] == "passed":
        shutil.copyfile(ROOT / ".tools/gas-scenarios.json", output / "gas-scenarios.json")
    check("local-demo", [sys.executable, "tools/demo.py", "--output-dir", str(output / "demo")], optimized)
    report.update(finished_at=now(), status="passed" if all(c["status"] == "passed" for c in report["checks"])
                  else "failed")
    save()
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
