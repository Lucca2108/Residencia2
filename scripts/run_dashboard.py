#!/usr/bin/env python
"""
Script para executar o Dashboard Streamlit.

Uso:
    python scripts/run_dashboard.py
"""
import subprocess
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Executa o dashboard Streamlit."""
    print("[DASHBOARD] Iniciando Dashboard...")
    print("[DASHBOARD] Abra http://localhost:8501 no navegador.\n")
    
    subprocess.run(
        ["python", "-m", "streamlit", "run", "dashboard/app.py"],
        cwd=PROJECT_ROOT
    )


if __name__ == "__main__":
    main()
