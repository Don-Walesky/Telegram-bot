"""
Bet Builder Telegram Handlers Module
Handles the interactive 5-step custom betslip wizard workflow (/custom and wiz_* callbacks).
Delegates custom slip construction to CustomSlipBuilder without modifying betting algorithms.
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes

from builder import CustomSlipBuilder
from database import DatabaseService
from keyboards import (
    build_main_menu_keyboard,
    build_wiz_date_keyboard,
    build_wiz_sport_keyboard,
    build_wiz_odds_keyboard,
    build_wiz_count_keyboard,
    build_wiz_prob_keyboard,
)

logger = logging.getLogger(__name__)


# /custom
async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Launches Step 1 of the Custom Bet Builder Wizard and resets user wizard state."""
    context.user_data["wiz"] = {}
    msg_target = update.message if update.message else update.callback_query.message
    await msg_target.reply_text(
        "🛠️ *Custom Slip Builder Wizard*\nSelect Target Date:",
        reply_markup=build_wiz_date_keyboard(),
        parse_mode="Markdown",
    )


async def handle_slip_callback(query, data: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handles Bet Builder wizard callback actions: wiz_start, wiz_date_*, wiz_sport_*, wiz_odds_*, wiz_count_*, wiz_prob_*.
    Returns True if the callback was processed by slip handlers, False otherwise.
    """
    if data == "wiz_start":
        context.user_data["wiz"] = {}
        await query.message.edit_text(
            "🛠️ *Custom Slip Builder Wizard*\nSelect Target Date:",
            reply_markup=build_wiz_date_keyboard(),
            parse_mode="Markdown",
        )
        return True
    elif data.startswith("wiz_date_"):
        sel_date = data.replace("wiz_date_", "")
        context.user_data.setdefault("wiz", {})["date"] = sel_date
        text = (
            f"🛠️ *BUILD BETSLIP WIZARD*\n\n"
            f"📅 Schedule Date: `{sel_date}`\n\n"
            f"📌 *Step 2 of 5: Select Sport Category*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_sport_keyboard(), parse_mode="Markdown"
        )
        return True
    elif data.startswith("wiz_sport_"):
        sel_sport = data.replace("wiz_sport_", "")
        context.user_data.setdefault("wiz", {})["sport"] = sel_sport
        wiz = context.user_data.get("wiz", {})
        text = (
            f"🛠️ *BUILD BETSLIP WIZARD*\n\n"
            f"📅 Date: `{wiz.get('date', 'Today')}` | 🏆 Sport: `{sel_sport}`\n\n"
            f"📌 *Step 3 of 5: Select Target Accumulator Odds (2.00x - 7.00x)*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_odds_keyboard(), parse_mode="Markdown"
        )
        return True
    elif data.startswith("wiz_odds_"):
        sel_odds = float(data.replace("wiz_odds_", ""))
        context.user_data.setdefault("wiz", {})["odds"] = sel_odds
        wiz = context.user_data.get("wiz", {})
        text = (
            f"🛠️ *BUILD BETSLIP WIZARD*\n\n"
            f"📅 Date: `{wiz.get('date', 'Today')}` | 🏆 Sport: `{wiz.get('sport', 'All')}` | 🎯 Target Odds: `{sel_odds}x`\n\n"
            f"📌 *Step 4 of 5: Select Number of Matches (5, 10, 15, 20, 25)*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_count_keyboard(), parse_mode="Markdown"
        )
        return True
    elif data.startswith("wiz_count_"):
        sel_count = int(data.replace("wiz_count_", ""))
        context.user_data.setdefault("wiz", {})["count"] = sel_count
        wiz = context.user_data.get("wiz", {})
        text = (
            f"🛠️ *BUILD BETSLIP WIZARD*\n\n"
            f"📅 Date: `{wiz.get('date', 'Today')}` | 🏆 Sport: `{wiz.get('sport', 'All')}`\n"
            f"🎯 Target Odds: `{wiz.get('odds', 2.0)}x` | ⚽ Games: `{sel_count}`\n\n"
            f"📌 *Step 5 of 5: Select Minimum Probability Threshold*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_prob_keyboard(), parse_mode="Markdown"
        )
        return True
    elif data.startswith("wiz_prob_"):
        sel_prob = float(data.replace("wiz_prob_", ""))
        wiz = context.user_data.get("wiz", {})
        target_date = wiz.get("date", "Today")
        target_sport = wiz.get("sport", "All")
        target_odds = wiz.get("odds", 2.0)
        game_count = wiz.get("count", 5)

        await query.message.edit_text(
            f"⚙️ *Generating custom multi-sport bet slip...*\n"
            f"Date: `{target_date}` | Sport: `{target_sport}` | Odds: `{target_odds}x` | Games: `{game_count}` | Safety: `{sel_prob}%`",
            parse_mode="Markdown",
        )

        res = await asyncio.to_thread(
            CustomSlipBuilder.generate_custom_slip,
            target_odds,
            game_count,
            sel_prob,
            target_date,
            target_sport,
        )
        context.user_data["current_slip"] = res

        # Save generated slip to SQLite database history
        user_id = query.from_user.id if query.from_user else 0
        DatabaseService.save_slip(
            user_id=user_id,
            match_date=target_date,
            sport=target_sport,
            game_count=res.game_count,
            target_odds=target_odds,
            actual_odds=res.actual_odds,
            min_probability=sel_prob,
            booking_code="",
            summary_text=res.formatted_summary,
        )

        await query.message.edit_text(
            res.formatted_summary, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
        return True

    return False
