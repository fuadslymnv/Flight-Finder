"""
Telegram Notification Service for FlightFinder.
Sends beautifully formatted flight deal alerts with deep booking links to a Telegram chat.
"""

import os
import logging
from typing import List, Optional, Tuple
import httpx

from backend.core.models import RoundTripItinerary, TelegramAlertSettings

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        config: Optional[TelegramAlertSettings] = None,
    ):
        # Priority: explicit arg -> config object -> environment variable
        env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        env_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

        cfg_token = config.bot_token.strip() if config else ""
        cfg_chat = config.chat_id.strip() if config else ""

        self.bot_token = bot_token or cfg_token or env_token
        self.chat_id = chat_id or cfg_chat or env_chat
        self.enabled = config.enabled if config else True

    @property
    def is_configured(self) -> bool:
        """Returns True if bot token and chat ID are both present."""
        return bool(self.bot_token and self.chat_id)

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}/{method}"

    async def test_connection(self) -> Tuple[bool, str]:
        """Test Telegram Bot credentials and connectivity."""
        if not self.bot_token:
            return False, "Telegram Bot Token is missing."
        if not self.chat_id:
            return False, "Telegram Chat ID is missing."

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Verify token with getMe
                res = await client.get(self._api_url("getMe"))
                if res.status_code != 200:
                    return False, f"Invalid Telegram Bot Token (HTTP {res.status_code}): {res.text}"
                bot_info = res.json().get("result", {})
                bot_name = bot_info.get("first_name", "Bot")
                bot_username = bot_info.get("username", "")

                # 2. Send test ping to chat_id
                ping_text = (
                    f"✈️ *FlightFinder Telegram Alert Connected!*\n"
                    f"Successfully connected to @{bot_username} ({bot_name}).\n"
                    f"You will receive weekend flight deals under 60€ here every 6 hours."
                )
                msg_res = await client.post(
                    self._api_url("sendMessage"),
                    json={
                        "chat_id": self.chat_id,
                        "text": ping_text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                )
                if msg_res.status_code != 200:
                    return False, f"Failed to send test message to Chat ID {self.chat_id}: {msg_res.text}"

                return True, f"Connected to @{bot_username} and test message sent successfully!"
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False, f"Network error during Telegram test: {e}"

    async def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a plain or Markdown-formatted message to the configured chat."""
        if not self.is_configured:
            logger.warning("TelegramNotifier not configured (bot_token or chat_id missing).")
            return False

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(
                    self._api_url("sendMessage"),
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_web_page_preview": True,
                    },
                )
                if res.status_code == 200:
                    return True
                else:
                    logger.error(f"Telegram API error {res.status_code}: {res.text}")
                    # If Markdown failed, retry as plain text
                    if parse_mode == "Markdown":
                        retry_res = await client.post(
                            self._api_url("sendMessage"),
                            json={"chat_id": self.chat_id, "text": text},
                        )
                        return retry_res.status_code == 200
                    return False
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False

    def format_deal_message(self, it: RoundTripItinerary) -> str:
        """Format a single RoundTripItinerary as a clear Telegram markdown message."""
        out = it.outbound
        ret = it.inbound

        out_day = WEEKDAY_NAMES[out.departure_date.weekday()]
        ret_day = WEEKDAY_NAMES[ret.departure_date.weekday()]

        out_dep = out.departure_time.strftime("%H:%M")
        out_arr = out.arrival_time.strftime("%H:%M")
        ret_dep = ret.departure_time.strftime("%H:%M")
        ret_arr = ret.arrival_time.strftime("%H:%M")

        curr_sym = "€" if it.currency == "EUR" else " Ft"
        city_dest = it.destination_city or out.destination

        lines = [
            f"✈️ *Weekend Deal: {city_dest.upper()} for {it.total_price:,.0f}{curr_sym}*",
            f"📍 Route: `{out.origin} ➔ {out.destination} ➔ {ret.destination}`",
            f"🌙 Trip: {it.nights} night{'s' if it.nights != 1 else ''} ({out_day} {out.departure_date.strftime('%d %b')} – {ret_day} {ret.departure_date.strftime('%d %b')})",
        ]

        if it.is_open_jaw:
            gt = it.ground_transfer
            lines.append("⚠️ *Open-Jaw Trip:* Return lands at a different airport!")
            if gt:
                cost_str = f"~{gt.estimated_cost_eur:.0f}€" if it.currency == "EUR" else f"~{gt.estimated_cost_huf:,.0f} Ft"
                lines.append(f"   🚌 Transfer ({gt.return_airport}➔{gt.origin_airport}): ~{gt.transit_hours}h ({cost_str})")

        out_fl_no = out.flight_number if out.flight_number.startswith(out.carrier_code) else f"{out.carrier_code}{out.flight_number}"
        ret_fl_no = ret.flight_number if ret.flight_number.startswith(ret.carrier_code) else f"{ret.carrier_code}{ret.flight_number}"

        lines.append("")
        lines.append(f"🛫 *Outbound:* {out_day} {out.departure_date.strftime('%d %b')}")
        lines.append(f"   `{out_dep} - {out_arr}` | {out.carrier_name} ({out_fl_no}) | {out.price:,.0f}{curr_sym}")

        lines.append(f"🛬 *Return:* {ret_day} {ret.departure_date.strftime('%d %b')}")
        lines.append(f"   `{ret_dep} - {ret_arr}` | {ret.carrier_name} ({ret_fl_no}) | {ret.price:,.0f}{curr_sym}")

        # Booking links
        links = []
        if out.direct_airline_url:
            links.append(f"[Outbound ({out.carrier_name})]({out.direct_airline_url})")
        elif out.booking_url:
            links.append(f"[Outbound (Kiwi)]({out.booking_url})")

        if ret.direct_airline_url:
            links.append(f"[Return ({ret.carrier_name})]({ret.direct_airline_url})")
        elif ret.booking_url:
            links.append(f"[Return (Kiwi)]({ret.booking_url})")

        if links:
            lines.append("")
            lines.append("🎫 *Direct Booking Links:* " + " | ".join(links))

        return "\n".join(lines)

    async def send_deals(
        self,
        deals: List[RoundTripItinerary],
        max_deals: int = 8,
        header_note: str = "",
    ) -> int:
        """
        Send a header followed by individual deal cards to Telegram.
        Returns the count of successfully sent deals.
        """
        if not deals:
            return 0

        if not self.is_configured:
            logger.warning("TelegramNotifier not configured. Skipping alert dispatch.")
            return 0

        top_deals = deals[:max_deals]
        count_sent = 0

        # Send introductory summary banner
        note_str = f"\n_{header_note}_" if header_note else ""
        header = (
            f"🔔 *FlightFinder: Found {len(deals)} Weekend Deals under {top_deals[0].total_price:.0f}–{top_deals[-1].total_price:.0f}€!*\n"
            f"Here are the top {len(top_deals)} deals for your 9-5 weekend getaways:{note_str}"
        )
        await self.send_message(header)

        for deal in top_deals:
            msg = self.format_deal_message(deal)
            success = await self.send_message(msg)
            if success:
                count_sent += 1

        return count_sent
