"""Put this package on sys.path so `pytest` works from anywhere in the repo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
