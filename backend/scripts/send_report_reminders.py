"""Send the monthly-report deadline reminders (§7.5).

Run from cron once a day; it is idempotent per day because it only fires on the
day offsets the brief names (three days before the due date, on the due date,
and daily once the period is late).

    DATABASE_URL=... python scripts/send_report_reminders.py

Exit code is the number of reminders actually sent, so a cron wrapper can tell
"nothing to do" from "transport failed" (which prints a warning and sends 0).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import reminders


def main() -> int:
    sent = reminders.run()
    print(f"Report reminders sent: {sent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
