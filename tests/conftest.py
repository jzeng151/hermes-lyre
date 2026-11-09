import sys
from pathlib import Path

# The plugin lives in lyre/ at the repo root; make it importable as `lyre`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
