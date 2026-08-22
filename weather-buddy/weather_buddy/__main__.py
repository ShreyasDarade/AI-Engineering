import sys

from .cli import main

try:  # .env support is a convenience, not a requirement
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

sys.exit(main())
