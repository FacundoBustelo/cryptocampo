#!/usr/bin/env python3
"""Resume la cobertura de Forge y localiza ramas de CCNFT con cero hits."""

import argparse
import re
from pathlib import Path


def check_baseline(report: str) -> None:
    rows = [line for line in report.splitlines() if re.match(r"\|\s*src/CCNFT\.sol\s*\|", line)]
    if len(rows) != 1:
        raise ValueError("Falta la fila única de cobertura de src/CCNFT.sol.")
    counts = [(int(hit), int(total)) for hit, total in re.findall(r"\((\d+)/(\d+)\)", rows[0])]
    if len(counts) != 4:
        raise ValueError("Formato de cobertura de CCNFT inesperado.")
    for index in (0, 1, 3):
        hit, total = counts[index]
        if total == 0 or hit != total:
            raise ValueError("Regresión: CCNFT requiere 100 % de líneas, sentencias y funciones.")
    hit, total = counts[2]
    if total != 81 or hit < 79:
        raise ValueError("Regresión o cambio de ramas: se requiere al menos 79/81; revisar la justificación.")


def summarize(report: str, source: list[str]) -> str:
    lines = report.splitlines()
    output = ["Resumen de cobertura:"]
    for line in lines:
        if line.startswith("Ran ") and "test suites" in line:
            output.append(line)
        elif "|" in line and ("%" in line or "| File " in line):
            output.append(line)

    in_contract = False
    found_contract = False
    branches = []
    for line in lines:
        if line.startswith("Anchors for Contract "):
            in_contract = line.startswith('Anchors for Contract "CCNFT" ')
            found_contract = found_contract or in_contract
        if in_contract and ": Branch " in line:
            branches.append(line)

    if not found_contract or not branches:
        raise ValueError("No se encontraron las ramas del reporte debug de CCNFT.")

    output.extend(["", "Ramas sin cubrir de src/CCNFT.sol:"])
    uncovered = 0
    for branch in branches:
        hits = re.search(r"hits:\s*(\d+)\)", branch)
        if not hits:
            raise ValueError("No se pudo leer el contador de una rama de CCNFT.")
        if int(hits[1]) != 0:
            continue
        location = re.search(r"lines:\s*(\d+)\.\.(\d+)", branch)
        if not location:
            raise ValueError("No se pudo localizar una rama sin cubrir de CCNFT.")
        start, end = map(int, location.groups())
        if not 1 <= start <= len(source) or end < start:
            raise ValueError("La ubicación de la rama no coincide con src/CCNFT.sol.")
        uncovered += 1
        output.append(branch)
        for number in range(start, min(max(start + 1, end), len(source) + 1)):
            output.append(f"  {number}: {source[number - 1]}")

    output.append(f"Ramas sin cubrir: {uncovered} de {len(branches)} reportadas para CCNFT.")
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--source", type=Path, default=Path("src/CCNFT.sol"))
    parser.add_argument("--check-baseline", action="store_true", help="Exige cobertura completa salvo dos ramas de CCNFT.")
    args = parser.parse_args()
    try:
        report = args.report.read_text()
        print(summarize(report, args.source.read_text().splitlines()))
        if args.check_baseline:
            check_baseline(report)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error al resumir cobertura: {error}\n")


if __name__ == "__main__":
    main()
