"""
Scan Telegram Handlers Module
Handles standard fixture and betting scan workflows (/today, /tomorrow, /scan, /sports, and scan callbacks).
Delegates core betting pipeline execution to BettingService without implementing business logic.
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes

from betting_service import BettingService
from keyboards import build_main_menu_keyboard, build_sport_keyboard

logger = logging.getLogger(__name__)


# /today
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["target_date"] = "Today"
    sport = context.user_data.get("target_sport", "All")
    await update.message.reply_text(
        f"🔍 *Scanning Today's unstarted fixtures ({sport})...*\nPlease wait a moment...",
        parse_mode="Markdown",
    )
    slip_res = await asyncio.to_thread(BettingService.execute_scan_pipeline, "Today", sport)
    context.user_data["current_slip"] = slip_res
    await update.message.reply_text(
        slip_res.formatted_summary,
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )


# /tomorrow
async def tomorrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["target_date"] = "Tomorrow"
    sport = context.user_data.get("target_sport", "All")
    await update.message.reply_text(
        f"🔍 *Scanning Tomorrow's unstarted fixtures ({sport})...*\nPlease wait a moment...",
        parse_mode="Markdown",
    )
    slip_res = await asyncio.to_thread(BettingService.execute_scan_pipeline, "Tomorrow", sport)
    context.user_data["current_slip"] = slip_res
    await update.message.reply_text(
        slip_res.formatted_summary,
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )


# /sports
async def sports_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = "🏆 Select your target sport category for fixture discovery and SportyBet catalog matching:"
    await update.message.reply_text(
        msg, reply_markup=build_sport_keyboard(), parse_mode="Markdown"
    )


# /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_date = context.user_data.get("target_date", "Today")
    sport = context.user_data.get("target_sport", "All")

    await update.message.reply_text(
        f"🔍 *Scanning LiveScore fixtures & matching SportyBet catalog...*\nDate: `{target_date}` | Sport: `{sport}`",
        parse_mode="Markdown",
    )

    slip_res = await asyncio.to_thread(BettingService.execute_scan_pipeline, target_date, sport)
    context.user_data["current_slip"] = slip_res

    await update.message.reply_text(
        slip_res.formatted_summary,
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )


async def handle_scan_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handles scan-related callback actions: cmd_today, cmd_tomorrow, cmd_sports, set_sport_*, cmd_scan.
    Returns True if the callback was processed by scan handlers, False otherwise.
    """
    if data in ["cmd_today", "cmd_tomorrow"]:
        target_date = "Today" if data == "cmd_today" else "Tomorrow"
        context.user_data["target_date"] = target_date
        sport = context.user_data.get("target_sport", "All")
        await query.message.edit_text(
            f"🔍 *Scanning {target_date}'s unstarted fixtures ({sport})...*\nPlease wait a moment...",
            parse_mode="Markdown",
        )
        slip_res = await asyncio.to_thread(BettingService.execute_scan_pipeline, target_date, sport)
        context.user_data["current_slip"] = slip_res
        await query.message.edit_text(
            slip_res.formatted_summary,
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )
        return True
    elif data == "cmd_sports":
        await query.message.edit_text(
            "🏆 Select your target sport category:",
            reply_markup=build_sport_keyboard(),
            parse_mode="Markdown",
        )
        return True
    elif data.startswith("set_sport_"):
        sport = data.split("_")[-1]
        context.user_data["target_sport"] = sport
        await query.message.edit_text(
            f"🏆 Target sport set to: `{sport.upper()}`.\nClick **Scan & Match Catalog** below.",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return True
    elif data == "cmd_scan":
        target_date = context.user_data.get("target_date", "Today")
        sport = context.user_data.get("target_sport", "All")
        await query.message.edit_text(
            f"🔍 *Scanning LiveScore fixtures & matching SportyBet catalog...*\nDate: `{target_date}` | Sport: `{sport}`",
            parse_mode="Markdown",
        )
        slip_res = await asyncio.to_thread(BettingService.execute_scan_pipeline, target_date, sport)
        context.user_data["current_slip"] = slip_res
        await query.message.edit_text(
            slip_res.formatted_summary,
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )
        return True

    return False
