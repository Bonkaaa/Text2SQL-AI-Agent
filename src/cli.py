"""CLI entrypoint for Text2SQL AI Agent.

Allows running the agent via:
    python -m src.cli
    python -m src.cli -i
    python -m src.cli -q "Câu hỏi..."
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.test_agent import main

if __name__ == "__main__":
    main()
