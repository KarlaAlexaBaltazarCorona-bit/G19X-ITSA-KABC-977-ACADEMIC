#!/usr/bin/env python3
"""
Security & OWASP Quality Auditor
Script unificado para auditar la seguridad, sintaxis, dependencias y reglas de OWASP.
Ejecuta:
  1. Ruff (Sintaxis y calidad de código)
  2. Semgrep (OWASP Top 10 y reglas de seguridad de Python)
  3. Bandit (Análisis estático de vulnerabilidades AST)
  4. pip-audit (Vulnerabilidades conocidas CVEs en librerías)
  5. Pytest (Pruebas unitarias e integración de seguridad)
"""

import sys
import time
import subprocess
import argparse
import shutil
from pathlib import Path

# Mitigación para consolas Windows (evita errores de codec charmap / cp1252)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REPO_ROOT = Path(__file__).resolve().parent.parent

def run_step(step_num: int, title: str, cmd: list[str], ignore_failure: bool = False) -> bool:
    print(f"\n{BOLD}{CYAN}[Paso {step_num}] {title}{RESET}")
    print(f"{YELLOW}> {' '.join(cmd)}{RESET}\n")
    start = time.time()
    try:
        res = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            check=False
        )
        duration = time.time() - start
        if res.returncode == 0:
            print(f"\n{GREEN}✓ {title} PASÓ ({duration:.2f}s){RESET}")
            return True
        else:
            if ignore_failure:
                print(f"\n{YELLOW}⚠ {title} ADVERTENCIA ({duration:.2f}s){RESET}")
                return True
            print(f"\n{RED}✗ {title} FALLÓ con código {res.returncode} ({duration:.2f}s){RESET}")
            return False
    except FileNotFoundError:
        print(f"\n{RED}✗ Comando no encontrado: {cmd[0]}. Verifica que esté instalado.{RESET}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Auditoría integral de Ciberseguridad y OWASP")
    parser.add_argument("--skip-tests", action="store_true", help="Omitir la suite de pruebas pytest")
    parser.add_argument("--fix", action="store_true", help="Auto-corregir problemas menores de sintaxis con ruff")
    args = parser.parse_args()

    print(f"{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}   🛡️  AUDITORÍA INTEGRAL DE SEGURIDAD Y OWASP   {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}")

    results = []

    # 1. Ruff
    ruff_cmd = [sys.executable, "-m", "ruff", "check"]
    if args.fix:
        ruff_cmd.append("--fix")
    ruff_cmd.append(".")
    results.append(("1. Calidad y Sintaxis (Ruff)", run_step(1, "Calidad y Sintaxis (Ruff)", ruff_cmd)))

    # 2. Gitleaks (Detección de Secretos)
    gitleaks_bin = shutil.which("gitleaks") or "gitleaks"
    gitleaks_cmd = [gitleaks_bin, "dir", ".", "--verbose"]
    results.append(("2. Detección de Secretos (Gitleaks)", run_step(2, "Detección de Secretos (Gitleaks)", gitleaks_cmd)))

    # 3. Semgrep (OWASP Top 10)
    semgrep_bin = shutil.which("semgrep") or "semgrep"
    semgrep_cmd = [
        semgrep_bin, "scan",
        "--config", "p/owasp-top-ten",
        "--config", "p/python",
        "--metrics=off",
        "app/"
    ]
    results.append(("3. Escaneo OWASP Top 10 (Semgrep)", run_step(3, "Escaneo OWASP Top 10 (Semgrep)", semgrep_cmd)))

    # 4. Bandit (SAST AST)
    bandit_cmd = [
        sys.executable, "-m", "bandit",
        "-r", ".",
        "-x", "./.venv,./tests,./scripts",
        "-ll"
    ]
    results.append(("4. Análisis SAST de Vulnerabilidades (Bandit)", run_step(4, "Análisis SAST de Vulnerabilidades (Bandit)", bandit_cmd)))

    # 5. pip-audit (CVEs vía OSV)
    pip_audit_cmd = [
        sys.executable, "-m", "pip_audit",
        "-s", "osv",
        "-r", "requirements.txt"
    ]
    results.append(("5. Auditoría de Dependencias (pip-audit)", run_step(5, "Auditoría de Dependencias (pip-audit)", pip_audit_cmd)))

    # 6. Pytest
    if not args.skip_tests:
        pytest_cmd = [
            sys.executable, "-m", "pytest",
            "-v"
        ]
        results.append(("6. Pruebas Unitarias y de Seguridad (Pytest)", run_step(6, "Pruebas Unitarias y de Seguridad (Pytest)", pytest_cmd)))
    else:
        print(f"\n{YELLOW}[Paso 6 Omitido] Pruebas Unitarias (Pytest){RESET}")

    # Resumen
    print(f"\n{BOLD}{CYAN}===================================================={RESET}")
    print(f"{BOLD}{CYAN}               RESUMEN DE AUDITORÍA                 {RESET}")
    print(f"{BOLD}{CYAN}===================================================={RESET}")

    all_passed = True
    for name, passed in results:
        status = f"{GREEN}APROBADO{RESET}" if passed else f"{RED}REPROBADO{RESET}"
        print(f" • {name:<45} [{status}]")
        if not passed:
            all_passed = False

    print(f"{BOLD}{CYAN}===================================================={RESET}")
    if all_passed:
        print(f"{BOLD}{GREEN}✅ TODO EN ORDEN: El código cumple con las políticas de OWASP y calidad.{RESET}\n")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}❌ SE ENCONTRARON VULNERABILIDADES O ERRORES: Corrige los puntos antes de hacer push.{RESET}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
