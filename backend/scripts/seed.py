"""CLI: seed the admin user.

Usage (from the ``backend`` directory)::

    python -m scripts.seed
    #   or
    python scripts/seed.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as a bare script: ``python scripts/seed.py``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.seed import seed_admin  # noqa: E402
from app.database import SessionLocal  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("segmently.scripts.seed")


def main() -> None:
    db = SessionLocal()
    try:
        user = seed_admin(db)
        logger.info("Admin ready: %s (id=%s)", user.email, user.id)
    finally:
        db.close()


if __name__ == "__main__":
    main()
