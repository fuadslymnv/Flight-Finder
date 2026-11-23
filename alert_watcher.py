#!/usr/bin/env python3
"""
Weekend Flight Deals Alert Watcher CLI.
Scans for weekend getaways under budget for 9-5 weekday workers
and delivers deals to Telegram every 6 hours starting from 9:00 AM.

Usage:
    python alert_watcher.py --now                # Run one immediate scan and send deals
    python alert_watcher.py --daemon             # Run continuous scheduler (every 6h starting 9 AM)
    python alert_watcher.py --test-telegram      # Verify Telegram Bot credentials
    python alert_watcher.py --max-price 60       # Scan with custom max price
    python alert_watcher.py --dry-run            # Scan & display without sending messages
    python alert_watcher.py --clear-history      # Reset sent deal deduplication database
"""

import sys
import argparse
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Configure utf-8 encoding for standard output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.settings import load_settings, save_settings
from backend.services.telegram_notifier import TelegramNotifier
from backend.services.alert_tracker import AlertTracker
from backend.services.scheduler import (
    run_weekend_alert_cycle,
    start_alert_daemon,
    get_next_run_time,
    seconds_until_next_run,
)
from find import format_itinerary_card

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("alert_watcher")


async def async_main():
    parser = argparse.ArgumentParser(description="Weekend Flight Deal Alert Watcher (9-5 weekday workers)")
    parser.add_argument("--now", action="store_true", help="Run an immediate deal check and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuous background scheduler")
    parser.add_argument("--dry-run", action="store_true", help="Find and display deals without sending Telegram messages")
    parser.add_argument("--max-price", type=float, help="Override maximum roundtrip price (default: 60 EUR)")
    parser.add_argument("--test-telegram", action="store_true", help="Test Telegram bot connectivity and exit")
    parser.add_argument("--clear-history", action="store_true", help="Clear alerted deal history database and exit")
    parser.add_argument("--limit", type=int, default=15, help="Max number of deals to display in console")

    args = parser.parse_args()

    # Load settings
    settings = load_settings()
    if args.max_price is not None:
        settings.alerts.max_price = args.max_price

    # 1. Clear history if requested
    if args.clear_history:
        tracker = AlertTracker()
        tracker.clear_history()
        print("✅ Alert history cleared. Future scans will treat all deals as fresh.")
        return

    # 2. Test Telegram connection if requested
    if args.test_telegram:
        notifier = TelegramNotifier(config=settings.alerts.telegram)
        print("Testing Telegram Bot connection...")
        if not notifier.is_configured:
            print("❌ Telegram Bot Token or Chat ID is not configured!")
            print("   Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in your environment,")
            print("   .env file, or inside settings.json under 'alerts.telegram'.")
            return
        success, message = await notifier.test_connection()
        if success:
            print(f"✅ SUCCESS: {message}")
        else:
            print(f"❌ ERROR: {message}")
        return

    # Initialize flight engine
    provider = KiwiMcpProvider()
    cache = FlightCache()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)
    tracker = AlertTracker()
    notifier = TelegramNotifier(config=settings.alerts.telegram)

    next_slot = get_next_run_time(start_hour=settings.alerts.start_hour, interval_hours=settings.alerts.check_interval_hours)
    sec_left = seconds_until_next_run(start_hour=settings.alerts.start_hour, interval_hours=settings.alerts.check_interval_hours)

    print("=" * 87)
    print("✈️  WEEKEND FLIGHT DEAL ALERT WATCHER (9-5 Weekday Workers)")
    print("=" * 87)
    print(f"📍 Home Origins:     {', '.join(settings.alerts.origins)}")
    print(f"💶 Max Budget:       {settings.alerts.max_price:.0f} {settings.alerts.currency}")
    print(f"📅 Horizon:          Next {settings.alerts.horizon_days} days")
    print(f"⏰ Schedule:         Every {settings.alerts.check_interval_hours}h starting at {settings.alerts.start_hour}:00 AM")
    print(f"⏳ Next Scheduled:   {next_slot.strftime('%Y-%m-%d %H:%M')} (in {sec_left/3600:.1f}h)")
    print(f"🔄 Open-Jaw:         {'Allowed' if settings.alerts.allow_open_jaw else 'Disabled'}")
    print(f"📱 Telegram Alerts:  {'Configured' if notifier.is_configured else '⚠️ Not configured (Console only)'}")
    print("=" * 87)

    # 3. Continuous daemon mode
    if args.daemon:
        print("\n🚀 Starting continuous alert daemon...")
        await start_alert_daemon(engine, run_immediately=True, dry_run=args.dry_run)
        return

    # 4. Immediate single run (default if --now or no arguments given)
    print("\n🔍 Running immediate scan for weekend deals...")
    all_deals, fresh_deals = await run_weekend_alert_cycle(
        engine=engine,
        notifier=notifier,
        tracker=tracker,
        dry_run=args.dry_run,
        max_send_count=args.limit,
    )

    if not all_deals:
        print("\n❌ No weekend deals found under the price threshold.")
        print(f"💡 Tip: Try increasing the max price with `--max-price 80` or broadening your search.")
        return

    print(f"\n🎉 Found {len(all_deals)} total weekend deals! ({len(fresh_deals)} new/price-dropped):")
    print("-" * 87)

    for i, it in enumerate(all_deals[:args.limit], 1):
        is_fresh = any(AlertTracker.get_deal_key(it) == AlertTracker.get_deal_key(f) for f in fresh_deals)
        fresh_tag = " [NEW/DISCOUNTED]" if is_fresh else ""
        print(f"Deal #{i:02d}{fresh_tag}:")
        print(format_itinerary_card(i, it, it.currency))

    if notifier.is_configured and not args.dry_run:
        print(f"\n📲 Dispatched {min(len(fresh_deals), 8)} alerts to Telegram!")
    elif not notifier.is_configured:
        print("\n💡 To receive these deals on your phone via Telegram:")
        print("   1. Create a bot using @BotFather on Telegram to get your BOT_TOKEN")
        print("   2. Send a message to your bot and get your CHAT_ID using @userinfobot")
        print("   3. Add them to settings.json or .env: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        print("   4. Verify with: python alert_watcher.py --test-telegram")


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nWatcher stopped by user.")


if __name__ == "__main__":
    main()
