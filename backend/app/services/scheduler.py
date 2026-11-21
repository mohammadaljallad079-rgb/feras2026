"""Daily scheduler for the deadline reminders (§7.5, §12.3).

The brief asks for the reminders to go out automatically at a fixed hour of the
Bahrain business day, to be retried shortly after a failure, and never to be
reported as sent when they were not. A bare ``while true; … sleep 86400`` does
none of that: it drifts by the run duration, it cannot retry, and its exit status
is thrown away.

This module owns that policy and leaves the work to ``reminders.run()``, which
keeps its durable at-most-once claim. The scheduler therefore only decides *when*
to call it:

* **fixed hour** — the next run is the configured ``REMINDER_SCHEDULE_TIME``
  (default 07:00) resolved in ``REMINDERS_TIMEZONE`` (default ``Asia/Bahrain``),
  so the job does not drift and a DST or server-zone change does not move it;
* **retry** — a run that raises is retried after ``RETRY_DELAY`` (15 minutes) up
  to ``MAX_ATTEMPTS`` times, then logged as failed for the day;
* **no fake success** — a failed run never advances the "last success" marker, so
  a restart re-attempts the day instead of silently skipping it;
* **restart-safe** — the marker lives in a file under ``STORAGE_DIR`` (a
  persisted volume). A restart after a successful run waits for tomorrow; a
  restart before the hour waits for the hour; a restart after the hour with no
  success that day runs immediately (catch-up) rather than losing the day.
  Duplicates are impossible regardless, because ``report_reminder_logs`` is the
  arbiter and ``reminders`` claims each reminder atomically.

A delivery that the transport rejects is not a scheduler failure: ``reminders``
records it ``failed`` and retries it on a later run. The scheduler only treats an
*exception* from the job as a failure worth retrying, which is why a transport
outage is retried by the job itself and a database outage is retried here.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as clock_time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.services import periods, reminders

logger = logging.getLogger("scheduler")

# §12.3: retry a failed run after 15 minutes, a bounded number of times, so a
# transient outage is ridden out without a tight loop.
RETRY_DELAY = timedelta(minutes=15)
MAX_ATTEMPTS = 3

# Never busy-loop when the wall clock jumps backwards.
MIN_SLEEP_SECONDS = 5.0

STATE_FILENAME = "scheduler_state.json"


def zone() -> ZoneInfo:
    """The operating timezone, falling back loudly rather than silently."""
    try:
        return ZoneInfo(settings.reminders_timezone)
    except (ZoneInfoNotFoundError, ValueError):
        logger.error(
            "Unknown REMINDERS_TIMEZONE %r; falling back to UTC. Install tzdata "
            "or fix the setting, or the daily run will drift.",
            settings.reminders_timezone,
        )
        return ZoneInfo("UTC")


def schedule_time() -> clock_time:
    """Parse ``REMINDER_SCHEDULE_TIME`` (``HH:MM``)."""
    raw = (settings.reminder_schedule_time or "07:00").strip()
    try:
        hour, minute = raw.split(":")[:2]
        return clock_time(int(hour), int(minute))
    except (ValueError, TypeError):
        logger.error("Invalid REMINDER_SCHEDULE_TIME %r; using 07:00.", raw)
        return clock_time(7, 0)


def next_run_at(now: datetime, at: clock_time, tz: ZoneInfo) -> datetime:
    """The next occurrence of ``at`` in ``tz`` strictly after ``now``."""
    local_now = now.astimezone(tz)
    candidate = datetime.combine(local_now.date(), at, tzinfo=tz)
    if candidate <= now:
        candidate = datetime.combine(local_now.date() + timedelta(days=1), at, tzinfo=tz)
    return candidate


@dataclass(frozen=True)
class Decision:
    """Whether to run now, and when to look again if not."""

    run_now: bool
    wake_at: datetime
    reason: str


def decide(now: datetime, last_success: date | None, at: clock_time, tz: ZoneInfo) -> Decision:
    """Choose between running now (catch-up) and sleeping until the next hour.

    Running is right when the day's slot has already passed and no run has
    succeeded today. Sleeping is right otherwise: before the hour, or after a
    successful run, in which case the next slot is tomorrow.
    """
    local_today = now.astimezone(tz).date()
    slot_today = datetime.combine(local_today, at, tzinfo=tz)

    if last_success == local_today:
        return Decision(False, next_run_at(now, at, tz), "already succeeded today")

    if slot_today <= now:
        return Decision(True, now, "catching up the missed slot")

    return Decision(False, slot_today, "waiting for the daily slot")


def state_path() -> Path:
    return Path(settings.storage_dir) / STATE_FILENAME


def load_last_success(path: Path | None = None) -> date | None:
    """Read the last successful run date, or ``None`` when unreadable.

    An unreadable marker is treated as "no success yet" so the day is attempted
    again. That can only cause an extra run, and the durable reminder claim makes
    an extra run harmless — the opposite mistake would skip a day silently.
    """
    target = path or state_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return date.fromisoformat(payload["last_success_date"])
    except FileNotFoundError:
        return None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Could not read scheduler state %s: %s", target, exc)
        return None


def save_last_success(day: date, path: Path | None = None) -> None:
    target = path or state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"last_success_date": day.isoformat()}), encoding="utf-8"
        )
    except OSError as exc:  # a read-only volume must not crash the scheduler
        logger.error("Could not persist scheduler state %s: %s", target, exc)


def run_once() -> bool:
    """Run the job once. ``True`` only when it completed without raising.

    §7.1/§12.3: the month's period is opened before the reminders go out, so a
    new month never starts with reminders pointing at the previous period.
    """
    started = time.monotonic()
    try:
        periods.run_rollover()
        sent = reminders.run()
    except Exception:
        logger.exception("Daily job failed")
        return False
    logger.info(
        "Daily job completed: period open, %s reminder(s) sent in %.1fs",
        sent,
        time.monotonic() - started,
    )
    return True


def sleep_until(target: datetime, *, sleep=time.sleep, now_fn=lambda: datetime.now(timezone.utc)) -> None:
    """Sleep until ``target``, never less than ``MIN_SLEEP_SECONDS``."""
    remaining = (target - now_fn()).total_seconds()
    if remaining <= 0:
        return
    sleep(max(remaining, MIN_SLEEP_SECONDS))


def run_day(at: clock_time, tz: ZoneInfo, *, attempts: int = MAX_ATTEMPTS) -> bool:
    """Try the job up to ``attempts`` times, sleeping ``RETRY_DELAY`` between.

    Returns ``True`` when one attempt completed. Every failure is logged; a
    success is never logged for a failed attempt.
    """
    for attempt in range(1, attempts + 1):
        if run_once():
            return True
        if attempt < attempts:
            logger.warning(
                "Attempt %s/%s failed; retrying in %s",
                attempt,
                attempts,
                RETRY_DELAY,
            )
            time.sleep(RETRY_DELAY.total_seconds())
    logger.error("Reminder job failed after %s attempt(s); will retry tomorrow", attempts)
    return False


def main() -> int:
    """Run forever. Returns only if the loop is stopped."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    at = schedule_time()
    tz = zone()
    logger.info(
        "Scheduler started: daily at %s %s (retry %s, up to %s attempts)",
        at.strftime("%H:%M"),
        tz.key,
        RETRY_DELAY,
        MAX_ATTEMPTS,
    )
    while True:
        now = datetime.now(timezone.utc)
        decision = decide(now, load_last_success(), at, tz)
        if not decision.run_now:
            logger.info("Next run at %s (%s)", decision.wake_at.isoformat(), decision.reason)
            sleep_until(decision.wake_at)
            continue
        logger.info("Running the reminder job (%s)", decision.reason)
        if run_day(at, tz):
            save_last_success(datetime.now(timezone.utc).astimezone(tz).date())
        else:
            # Move past today's slot so the loop does not spin on a hard failure.
            sleep_until(next_run_at(datetime.now(timezone.utc), at, tz))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
        sys.exit(0)
