"""
Periodic Weekend Flight Deal Scheduler.
Checks for weekend flight deals every 6 hours starting from 9:00 AM (09:00, 15:00, 21:00, 03:00)
and delivers newly found or discounted deals to Telegram.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple

from backend.core.models import RoundTripItinerary, WeekendAlertSettings
from backend.core.combiner import FlightEngine
from backend.core.weekend import find_weekend_deals
from backend.services.telegram_notifier import TelegramNotifier
from backend.services.alert_tracker import AlertTracker

logger = logging.getLogger(__name__)


def get_schedule_hours(start_hour: int = 9, interval_hours: int = 6) -> List[int]:
    """Calculate the hours of the day when alerts should trigger."""
    count = 24 // interval_hours
    hours = sorted(set((start_hour + i * interval_hours) % 24 for i in range(count)))
    return hours


def get_next_run_time(
    now: Optional[datetime] = None,
    start_hour: int = 9,
    interval_hours: int = 6,
) -> datetime:
    """
    Calculate the next scheduled datetime for deal checking.
    Default anchors: 09:00, 15:00, 21:00, 03:00.
    """
    current = now or datetime.now()
    schedule_hours = get_schedule_hours(start_hour, interval_hours)

    candidates = [
        datetime.combine(current.date(), time(hour=h, minute=0, second=0))
        for h in schedule_hours
    ]

    for c in candidates:
        if c > current:
            return c

    # If all today's slots have passed, return the first slot tomorrow
    tomorrow = current.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(hour=schedule_hours[0], minute=0, second=0))


def seconds_until_next_run(
    now: Optional[datetime] = None,
    start_hour: int = 9,
    interval_hours: int = 6,
) -> float:
    """Return seconds remaining until next run time."""
    current = now or datetime.now()
    next_run = get_next_run_time(current, start_hour=start_hour, interval_hours=interval_hours)
    delta = (next_run - current).total_seconds()
    return max(0.0, delta)


async def run_weekend_alert_cycle(
    engine: FlightEngine,
    notifier: Optional[TelegramNotifier] = None,
    tracker: Optional[AlertTracker] = None,
    force_refresh: bool = False,
    dry_run: bool = False,
    max_send_count: int = 8,
) -> Tuple[List[RoundTripItinerary], List[RoundTripItinerary]]:
    """
    Execute one full weekend alert search cycle.
    Returns (all_matching_deals, fresh_dispatched_deals).
    """
    alert_settings = engine.settings.alerts
    tracker = tracker or AlertTracker()
    notifier = notifier or TelegramNotifier(config=alert_settings.telegram)

    logger.info(
        f"Starting weekend flight deal scan (max price {alert_settings.max_price} {alert_settings.currency}, "
        f"horizon {alert_settings.horizon_days} days, open-jaw: {alert_settings.allow_open_jaw})..."
    )

    all_deals = await find_weekend_deals(
        engine=engine,
        alert_settings=alert_settings,
        force_refresh=force_refresh,
    )

    logger.info(f"Found {len(all_deals)} total matching weekend deals under {alert_settings.max_price}€.")

    fresh_deals = tracker.filter_fresh_deals(all_deals)
    logger.info(f"Filtered down to {len(fresh_deals)} fresh (unnotified or price-dropped) deals.")

    if not fresh_deals:
        logger.info("No new deals to send this cycle.")
        return all_deals, []

    if dry_run:
        logger.info(f"[DRY-RUN] Would dispatch {min(len(fresh_deals), max_send_count)} deals to Telegram.")
        return all_deals, fresh_deals

    # Send alerts via Telegram
    if notifier.is_configured:
        sent_count = await notifier.send_deals(
            fresh_deals,
            max_deals=max_send_count,
            header_note="Automated 6-Hour Scheduled Deal Scan",
        )
        logger.info(f"Dispatched {sent_count} deal alerts to Telegram.")
        tracker.record_sent_deals(fresh_deals[:max_send_count])
    else:
        logger.warning(
            "Telegram bot is not configured (missing bot_token or chat_id). "
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to receive alerts."
        )

    return all_deals, fresh_deals


async def start_alert_daemon(
    engine: FlightEngine,
    run_immediately: bool = True,
    dry_run: bool = False,
):
    """
    Background loop that wakes up every 6 hours starting at 9:00 AM (09:00, 15:00, 21:00, 03:00).
    """
    settings = engine.settings.alerts
    notifier = TelegramNotifier(config=settings.telegram)
    tracker = AlertTracker()

    logger.info("Starting Weekend Flight Deal Alert Daemon...")
    logger.info(f"Schedule: every {settings.check_interval_hours}h starting at {settings.start_hour}:00")

    if run_immediately:
        logger.info("Executing initial immediate deal scan on startup...")
        try:
            await run_weekend_alert_cycle(
                engine=engine,
                notifier=notifier,
                tracker=tracker,
                dry_run=dry_run,
            )
        except Exception as e:
            logger.error(f"Error in initial deal scan: {e}")

    while True:
        sec_wait = seconds_until_next_run(
            start_hour=settings.start_hour,
            interval_hours=settings.check_interval_hours,
        )
        next_dt = get_next_run_time(
            start_hour=settings.start_hour,
            interval_hours=settings.check_interval_hours,
        )
        logger.info(f"Next scheduled alert scan in {sec_wait/3600:.2f} hours (at {next_dt.strftime('%Y-%m-%d %H:%M:%S')}). Sleeping...")

        await asyncio.sleep(sec_wait)

        logger.info(f"Scheduled alert trigger firing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}!")
        try:
            await run_weekend_alert_cycle(
                engine=engine,
                notifier=notifier,
                tracker=tracker,
                dry_run=dry_run,
            )
        except Exception as e:
            logger.error(f"Error executing scheduled alert scan: {e}")
