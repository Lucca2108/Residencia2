#!/usr/bin/env python
"""
Script para executar a API FastAPI.

Uso:
    python scripts/run_api.py
    
Ou com argumentos personalizados:
    python scripts/run_api.py --host 0.0.0.0 --port 8000
"""
import subprocess
import sys
from pathlib import Path

# Ensure we're in the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Executa a API FastAPI com uvicorn."""
    print("[RUN] Iniciando API FastAPI...")
    print("[RUN] Pressione Ctrl+C para parar.\n")
    
    subprocess.run(
        ["python", "-m", "uvicorn", "myapi:app", "--reload"],
        cwd=PROJECT_ROOT
    )


if __name__ == "__main__":
    main()
