"""Daily job: open the month's period, then send the report reminders (§7.1, §7.5, §12.3).

This is the cron entry point. It goes through ``scheduler.run_once`` rather than
calling ``reminders.run`` directly, because the period rollover has to happen
before the reminders are computed — a job that only reminds would keep pointing
at a period nobody opened.

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

from app.services import scheduler  # noqa: E402


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if not scheduler.run_once():
        return 2
    print("Daily job completed: period opened and reminders attempted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
