"""Send the monthly-report deadline reminders (§7.5).

Run from cron once a day, ideally shortly after the reminders timezone's day
boundary. The work itself is idempotent: each company/period/day reminder is
claimed through a durable log, so running the job twice — or two workers at the
same time — sends a given reminder at most once.

    DATABASE_URL=... python scripts/send_report_reminders.py

Exit code is 0 when the run completed (whether or not anything was sent) and 2
when the run raised, so a cron wrapper can tell "nothing to do" from "the job
itself failed". The number of reminders actually delivered is printed; a
transport failure is reported as a warning and never as a delivery.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import reminders  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        sent = reminders.run()
    except Exception:  # the job failed; make it visible to cron
        logging.getLogger("send_report_reminders").exception("Report reminder run failed")
        return 2
    print(f"Report reminders sent: {sent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
