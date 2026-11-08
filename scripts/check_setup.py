# scripts/check_setup.py — checks the setup. It does NOT call Gnani or Groq, so it costs no credits.
import importlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_PACKAGES = ["requests", "dotenv", "openai", "sentence_transformers", "faiss",
                     "transformers", "torch", "streamlit", "jiwer", "pytest", "pandas"]
REQUIRED_FOLDERS = ["data", "index", "src", "eval", "results", "tests", "assets", "scripts"]
REQUIRED_ENV = ["GNANI_STT_API_KEY", "GNANI_TTS_API_KEY", "GROQ_API_KEY"]

def ok(msg):
    print("  OK  ", msg)

def bad(msg):
    print("  FAIL", msg)

print("Python version:", sys.version.split()[0])

print("\nPackages:")
for name in REQUIRED_PACKAGES:
    try:
        importlib.import_module(name)
        ok(name)
    except Exception as err:
        bad(f"{name} -> {err}")

print("\nFolders:")
for folder in REQUIRED_FOLDERS:
    ok(folder) if Path(folder).is_dir() else bad(f"{folder} is missing")

print("\nSecrets in .env (values are never printed):")
load_dotenv()
for key in REQUIRED_ENV:
    value = os.getenv(key, "")
    if value and "put_your" not in value:
        ok(f"{key} is set ({len(value)} characters)")
    else:
        bad(f"{key} is missing or still the placeholder")

print("\nGit safety:")
gitignore = Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").exists() else ""
ok(".env is in .gitignore") if ".env" in gitignore.splitlines() else bad(".env is NOT in .gitignore")
print("\nDRY_RUN =", os.getenv("DRY_RUN", "0"), "(1 = no real API calls)")