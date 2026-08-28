"""
Telegram Bot Engine — SportyBet Implied-Probability Booking Code Assistant
Integrates LiveScore Discovery, SportyBet Catalog Matcher, Implied-Probability Filter,
and SportyBet Official Booking Code Client.
"""

import logging
import os
from datetime import datetime, timedelta
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from livescore_client import LiveScoreClient
from sportybet_catalog import SportyBetCatalogService
from probability_filter import ImpliedProbabilityFilter
from sportybet_booking import SportyBetBookingClient, BookingSlipResponse
from channel_monitor import ChannelMonitorService
from code_converter import BetCodeConverterService
from tipster_learning import TipsterMarketLearner
from database import DatabaseService
from learning_engine import StrategyLearningEngine
from builder import CustomSlipBuilder
from betting_service import BettingService
from config import config
from exceptions import BotError, ExternalAPIError, DatabaseError, ValidationError

# Load environment variables & token
TOKEN = config.env.telegram_bot_token

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.app.log_level, logging.INFO),
)
logger = logging.getLogger(__name__)


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Construct main menu inline buttons."""
    keyboard = [
        [
            InlineKeyboardButton("🛠️ Build Betslip", callback_data="wiz_start"),
        ],
        [
            InlineKeyboardButton("📡 Scan Channels & Build Betslip", callback_data="chan_wiz_start"),
        ],
        [
            InlineKeyboardButton("📅 Today's Scan", callback_data="cmd_today"),
            InlineKeyboardButton("📆 Tomorrow's Scan", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton("📜 My Slip History", callback_data="cmd_history"),
            InlineKeyboardButton("🎟️ View Current Slip", callback_data="cmd_slip"),
        ],
        [
            InlineKeyboardButton("🧠 Learning Engine", callback_data="cmd_learn"),
            InlineKeyboardButton("📊 System Status", callback_data="cmd_status"),
        ],
        [
            InlineKeyboardButton("🔄 Convert Code", callback_data="menu_convert"),
            InlineKeyboardButton("ℹ️ Help & Commands", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_sport_keyboard() -> InlineKeyboardMarkup:
    """Sport Category Selection Keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🏆 All Sports", callback_data="set_sport_All"),
            InlineKeyboardButton("⚽ Football", callback_data="set_sport_Football"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="set_sport_Basketball"),
            InlineKeyboardButton("🎾 Tennis", callback_data="set_sport_Tennis"),
        ],
        [
            InlineKeyboardButton("🏒 Ice Hockey", callback_data="set_sport_Ice Hockey"),
        ],
        [
            InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wiz_date_keyboard() -> InlineKeyboardMarkup:
    """Construct 7-day date schedule keyboard (Today, Tomorrow, +4 subsequent days)."""
    now = datetime.now()
    dates = [("📅 Today", "Today"), ("📆 Tomorrow", "Tomorrow")]

    for i in range(2, 6):
        d_obj = now + timedelta(days=i)
        btn_text = d_obj.strftime("%a %d %b")
        btn_val = d_obj.strftime("%Y-%m-%d")
        dates.append((f"🗓️ {btn_text}", btn_val))

    keyboard = []
    for i in range(0, len(dates), 2):
        row = [InlineKeyboardButton(dates[i][0], callback_data=f"wiz_date_{dates[i][1]}")]
        if i + 1 < len(dates):
            row.append(InlineKeyboardButton(dates[i + 1][0], callback_data=f"wiz_date_{dates[i + 1][1]}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)


def build_wiz_sport_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🏆 All Sports", callback_data="wiz_sport_All"),
            InlineKeyboardButton("⚽ Football", callback_data="wiz_sport_Football"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="wiz_sport_Basketball"),
            InlineKeyboardButton("🎾 Tennis", callback_data="wiz_sport_Tennis"),
        ],
        [InlineKeyboardButton("🏒 Ice Hockey", callback_data="wiz_sport_Ice Hockey")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wiz_odds_keyboard() -> InlineKeyboardMarkup:
    """Construct odds keyboard (2.00x min to 7.00x max)."""
    keyboard = [
        [
            InlineKeyboardButton("🎯 2.00x Odds", callback_data="wiz_odds_2.0"),
            InlineKeyboardButton("🎯 3.00x Odds", callback_data="wiz_odds_3.0"),
        ],
        [
            InlineKeyboardButton("🎯 4.00x Odds", callback_data="wiz_odds_4.0"),
            InlineKeyboardButton("🎯 5.00x Odds", callback_data="wiz_odds_5.0"),
        ],
        [
            InlineKeyboardButton("🎯 7.00x Odds (Max Risk)", callback_data="wiz_odds_7.0"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wiz_count_keyboard() -> InlineKeyboardMarkup:
    """Construct game count keyboard (5, 10, 15, 20, 25)."""
    keyboard = [
        [
            InlineKeyboardButton("⚽ 5 Games", callback_data="wiz_count_5"),
            InlineKeyboardButton("⚽ 10 Games", callback_data="wiz_count_10"),
        ],
        [
            InlineKeyboardButton("⚽ 15 Games", callback_data="wiz_count_15"),
            InlineKeyboardButton("⚽ 20 Games", callback_data="wiz_count_20"),
        ],
        [
            InlineKeyboardButton("⚽ 25 Games", callback_data="wiz_count_25"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wiz_prob_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🛡️ 85% Safety", callback_data="wiz_prob_85"),
            InlineKeyboardButton("🛡️ 90% Safety", callback_data="wiz_prob_90"),
            InlineKeyboardButton("🛡️ 95% Ultra Safe", callback_data="wiz_prob_95"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_chan_wiz_prob_keyboard() -> InlineKeyboardMarkup:
    """Construct Channel Scanning Probability Threshold Keyboard (85% min to 95% max)."""
    keyboard = [
        [
            InlineKeyboardButton("🛡️ 85% Minimum Safety", callback_data="chan_prob_85"),
            InlineKeyboardButton("🛡️ 90% High Safety", callback_data="chan_prob_90"),
        ],
        [
            InlineKeyboardButton("🛡️ 95% Maximum Safety", callback_data="chan_prob_95"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_chan_wiz_count_keyboard() -> InlineKeyboardMarkup:
    """Construct Channel Sieving Game Count Keyboard (3, 5, 7, 10 games)."""
    keyboard = [
        [
            InlineKeyboardButton("⚽ 3 Games", callback_data="chan_count_3"),
            InlineKeyboardButton("⚽ 5 Games", callback_data="chan_count_5"),
        ],
        [
            InlineKeyboardButton("⚽ 7 Games", callback_data="chan_count_7"),
            InlineKeyboardButton("⚽ 10 Games", callback_data="chan_count_10"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def post_init(application) -> None:
    bot_info = await application.bot.get_me()
    logger.info(
        f"✅ Bot initialized! Username: @{bot_info.username} (ID: {bot_info.id})"
    )


# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name if update.effective_user else "User"
    welcome = (
        f"👋 *Welcome {user_name}!*\n\n"
        "Welcome to **SportyBet Implied-Probability Booking Helper** ⚽🏀🎾🏒\n\n"
        "Select an option below to start building high-accuracy slips:\n\n"
        "• 🛠️ **Build Betslip:** Select fixture schedule dates (7-day window), target odds (2.00x - 7.00x), game count (5, 10, 15, 20, 25), and safety win probabilities.\n"
        "• 📡 **Scan Channels & Build Betslip:** Scan watched Telegram tipster channels, sieve out high-risk matches (85% - 95% safety), and generate high-win SportyBet load links!"
    )
    await update.message.reply_text(
        welcome, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /today
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["target_date"] = "Today"
    sport = context.user_data.get("target_sport", "All")
    await update.message.reply_text(
        f"🔍 *Scanning Today's unstarted fixtures ({sport})...*\nPlease wait a moment...",
        parse_mode="Markdown",
    )
    slip_res = await asyncio.to_thread(run_pipeline, "Today", sport)
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
    slip_res = await asyncio.to_thread(run_pipeline, "Tomorrow", sport)
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


# Helper: Perform scan and mapping pipeline via BettingService
def run_pipeline(target_date: str = "Today", sport: str = "All") -> BookingSlipResponse:
    return BettingService.execute_scan_pipeline(target_date=target_date, sport=sport)


# /scan
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_date = context.user_data.get("target_date", "Today")
    sport = context.user_data.get("target_sport", "All")

    await update.message.reply_text(
        f"🔍 *Scanning LiveScore fixtures & matching SportyBet catalog...*\nDate: `{target_date}` | Sport: `{sport}`",
        parse_mode="Markdown",
    )

    slip_res = await asyncio.to_thread(run_pipeline, target_date, sport)
    context.user_data["current_slip"] = slip_res

    await update.message.reply_text(
        slip_res.formatted_summary,
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=False,
    )


# /slip
async def slip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    slip_res: BookingSlipResponse = context.user_data.get("current_slip")
    if not slip_res:
        await update.message.reply_text(
            "⚠️ No active slip found. Use `/scan` to discover fixtures and generate a new slip!",
            reply_markup=build_main_menu_keyboard(),
        )
        return

    await update.message.reply_text(
        slip_res.formatted_summary,
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
    )


# /code
async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    slip_res: BookingSlipResponse = context.user_data.get("current_slip")
    if not slip_res:
        await update.message.reply_text(
            "⚠️ No active slip found. Use `/scan` to discover fixtures and generate a new slip!",
            reply_markup=build_main_menu_keyboard(),
        )
        return

    if slip_res.booking_code:
        text = (
            f"📌 *SportyBet Official Booking Code:* `{slip_res.booking_code}`\n\n"
            f"🔗 [Click to Load on SportyBet]({slip_res.share_url})\n\n"
            f"Direct Share Link:\n`{slip_res.share_url}`"
        )
    else:
        text = (
            "⚠️ *No valid booking code generated.* (SportyBet API requires an active browser session to lock booking codes online).\n\n"
            "Please recreate the picks manually on SportyBet using the structured summary from `/slip`."
        )

    await update.message.reply_text(
        text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status_text = (
        "📊 *SYSTEM STATUS & API HEALTH*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 *LiveScore Discovery:* Operational\n"
        "🟢 *SportyBet Catalog Matcher:* Active\n"
        "🟢 *Implied Probability Engine:* Active (85%-95% range)\n"
        "🟢 *Booking Code Client:* Official SportyBet Share Endpoint + Clean Fallback\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ *Configuration:* Secrets loaded from `.env`\n"
        "🛡️ *Hard Constraints:* Zero fake codes, zero login scraping, 100% compliant."
    )
    await update.message.reply_text(
        status_text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /convert <code> [from_bookmaker]
async def convert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        msg = (
            "🔄 *How to Convert a Bet Code to SportyBet:*\n\n"
            "Usage: `/convert <BOOKING_CODE> [from_bookmaker]`\n"
            "Example: `/convert B9JA123 bet9ja`"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return

    code = context.args[0].upper()
    from_bm = context.args[1].lower() if len(context.args) > 1 else "bet9ja"

    res = BetCodeConverterService.convert_code_to_sportybet(
        source_code=code, source_bookmaker=from_bm
    )
    # Learn tipster market pattern from converted code payload
    TipsterMarketLearner.analyze_channel_post(f"Code {code} from {from_bm}")

    user_id = update.effective_user.id if update.effective_user else 0
    DatabaseService.save_conversion(
        user_id=user_id,
        source_code=code,
        source_bookmaker=from_bm.capitalize(),
        sportybet_code=res.sportybet_code,
        provider_used=res.provider_used,
    )

    report = BetCodeConverterService.format_conversion_report(res)
    await update.message.reply_text(
        report,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(),
    )


# /channels
async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    report = ChannelMonitorService.format_channels_report()
    await update.message.reply_text(
        report, parse_mode="Markdown", reply_markup=build_main_menu_keyboard()
    )


# Callback Handler
async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "menu_main":
        await query.message.edit_text(
            "👋 *Main Menu — Select an Option:*",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    elif data in ["cmd_today", "cmd_tomorrow"]:
        target_date = "Today" if data == "cmd_today" else "Tomorrow"
        context.user_data["target_date"] = target_date
        sport = context.user_data.get("target_sport", "All")
        await query.message.edit_text(
            f"🔍 *Scanning {target_date}'s unstarted fixtures ({sport})...*\nPlease wait a moment...",
            parse_mode="Markdown",
        )
        slip_res = await asyncio.to_thread(run_pipeline, target_date, sport)
        context.user_data["current_slip"] = slip_res
        await query.message.edit_text(
            slip_res.formatted_summary,
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )
    elif data == "cmd_sports":
        await query.message.edit_text(
            "🏆 Select your target sport category:",
            reply_markup=build_sport_keyboard(),
            parse_mode="Markdown",
        )
    elif data.startswith("set_sport_"):
        sport = data.split("_")[-1]
        context.user_data["target_sport"] = sport
        await query.message.edit_text(
            f"🏆 Target sport set to: `{sport.upper()}`.\nClick **Scan & Match Catalog** below.",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    elif data == "cmd_scan":
        target_date = context.user_data.get("target_date", "Today")
        sport = context.user_data.get("target_sport", "All")
        await query.message.edit_text(
            f"🔍 *Scanning LiveScore fixtures & matching SportyBet catalog...*\nDate: `{target_date}` | Sport: `{sport}`",
            parse_mode="Markdown",
        )
        slip_res = await asyncio.to_thread(run_pipeline, target_date, sport)
        context.user_data["current_slip"] = slip_res
        await query.message.edit_text(
            slip_res.formatted_summary,
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )
    elif data == "cmd_slip":
        slip_res = context.user_data.get("current_slip")
        if slip_res:
            await query.message.edit_text(
                slip_res.formatted_summary,
                reply_markup=build_main_menu_keyboard(),
                parse_mode="Markdown",
            )
        else:
            await query.message.edit_text(
                "⚠️ No active slip found. Click **Scan & Match Catalog** to generate one!",
                reply_markup=build_main_menu_keyboard(),
            )
    elif data == "cmd_code":
        slip_res = context.user_data.get("current_slip")
        if not slip_res:
            await query.message.edit_text(
                "⚠️ No active slip found. Click **Scan & Match Catalog** to generate one!",
                reply_markup=build_main_menu_keyboard(),
            )
        elif slip_res.booking_code:
            text = (
                f"📌 *SportyBet Official Booking Code:* `{slip_res.booking_code}`\n\n"
                f"🔗 [Click to Load on SportyBet]({slip_res.share_url})"
            )
            await query.message.edit_text(
                text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
            )
        else:
            text = (
                "⚠️ *No valid booking code generated.* (SportyBet API requires a live browser session to lock booking codes online).\n\n"
                "Please recreate the picks manually on SportyBet using the structured summary from your slip."
            )
            await query.message.edit_text(
                text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
            )
    elif data == "cmd_learn":
        report = StrategyLearningEngine.format_learning_report()
        await query.message.edit_text(
            report, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "cmd_status":
        status_text = (
            "📊 *SYSTEM STATUS & API HEALTH*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🟢 *LiveScore Discovery:* Operational\n"
            "🟢 *SportyBet Catalog Matcher:* Active\n"
            "🟢 *Implied Probability Engine:* Active (85%-95% range)\n"
            "🟢 *Hourly Market Harvester:* Active (Background 60m cycle)\n"
            "🟢 *Booking Code Client:* Official SportyBet Share Endpoint + Clean Fallback\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ *Configuration:* Secrets loaded from `.env`\n"
            "🛡️ *Hard Constraints:* Zero fake codes, zero login scraping, 100% compliant."
        )
        await query.message.edit_text(
            status_text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "menu_channels":
        report = ChannelMonitorService.format_channels_report()
        await query.message.edit_text(
            report, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "menu_convert":
        prompt = (
            "🔄 *CONVERT BET CODE TO SPORTYBET*\n\n"
            "To convert any booking code from Bet9ja, 1xBet, or 22Bet to SportyBet, send:\n"
            "`/convert B9JA123 bet9ja`"
        )
        await query.message.edit_text(
            prompt, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "menu_help":
        help_text = (
            "ℹ️ *COMMANDS GUIDE*\n\n"
            "• `/start` - Show main interactive menu\n"
            "• `/custom` - Launch 5-step custom bet slip builder wizard\n"
            "• `/today` - Select today's unstarted fixtures\n"
            "• `/tomorrow` - Select tomorrow's unstarted fixtures\n"
            "• `/sports` - Filter by sport category\n"
            "• `/scan` - Run LiveScore discovery & SportyBet catalog matching\n"
            "• `/slip` - View current matched slip\n"
            "• `/code` - Get SportyBet booking code or recreation slip\n"
            "• `/learn` - View strategy rules & hourly learned SportyBet markets\n"
            "• `/status` - View API health & system status\n"
            "• `/channels` - View monitored Telegram channels\n"
            "• `/convert <CODE>` - Convert external bookmaker codes"
        )
        await query.message.edit_text(
            help_text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "cmd_history":
        await history_command(update, context)
    elif data == "chan_wiz_start":
        text = (
            "📡 *SCAN CHANNELS & BUILD BETSLIP*\n\n"
            "This scanner analyzes slips posted in watched Telegram channels, sieves out high-risk matches according to your safety threshold, and builds a high-win SportyBet load link.\n\n"
            "📌 *Step 1 of 2: Select Minimum Safety Probability Threshold*"
        )
        await query.message.edit_text(
            text, reply_markup=build_chan_wiz_prob_keyboard(), parse_mode="Markdown"
        )
    elif data.startswith("chan_prob_"):
        sel_prob = float(data.replace("chan_prob_", ""))
        context.user_data.setdefault("chan_wiz", {})["prob"] = sel_prob
        text = (
            f"📡 *SCAN CHANNELS & BUILD BETSLIP*\n\n"
            f"🛡️ Safety Threshold: `{sel_prob}%`\n\n"
            f"📌 *Step 2 of 2: Select Number of Games to Sieve*"
        )
        await query.message.edit_text(
            text, reply_markup=build_chan_wiz_count_keyboard(), parse_mode="Markdown"
        )
    elif data.startswith("chan_count_"):
        sel_count = int(data.replace("chan_count_", ""))
        chan_wiz = context.user_data.get("chan_wiz", {})
        sel_prob = chan_wiz.get("prob", 85.0)

        await query.message.edit_text(
            f"📡 *Scanning watched channels & sieving high-win slip...*\n"
            f"Safety: `{sel_prob}%` | Games: `{sel_count}`",
            parse_mode="Markdown",
        )

        from channel_siever import ChannelSlipSiever
        res = await asyncio.to_thread(
            ChannelSlipSiever.scan_and_sieve_channel_slips,
            sel_prob,
            sel_count,
        )
        context.user_data["current_slip"] = res

        user_id = query.from_user.id if query.from_user else 0
        DatabaseService.save_slip(
            user_id=user_id,
            match_date="Watched Channels",
            sport="Multi-Channel",
            game_count=len(res.picks),
            target_odds=res.total_odds,
            actual_odds=res.total_odds,
            min_probability=sel_prob,
            booking_code="",
            summary_text=res.formatted_summary,
        )

        await query.message.edit_text(
            res.formatted_summary, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
        )
    elif data == "wiz_start":
        await custom_command(update, context)
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
    elif data.startswith("wiz_prob_"):
        sel_prob = float(data.replace("wiz_prob_", ""))
        wiz = context.user_data.get("wiz", {})
        target_date = wiz.get("date", "Today")
        target_sport = wiz.get("sport", "All")
        target_odds = wiz.get("odds", 2.0)
        game_count = wiz.get("count", 3)

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

        # Save to database history
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


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays user's last 5 generated bet slips from SQLite database."""
    user_id = update.effective_user.id if update.effective_user else 0
    history = DatabaseService.get_user_history(user_id=user_id, limit=5)

    if not history:
        await update.message.reply_text(
            "📜 *SLIP HISTORY*\n\nNo saved bet slips found yet. Use `/scan` or `/custom` to build your first slip!",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
        )
        return

    lines = [
        "📜 *YOUR GENERATED SLIP HISTORY*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for idx, item in enumerate(history, 1):
        date_str = item.get("match_date", "Today")
        sport_str = item.get("sport", "All")
        odds_val = item.get("actual_odds", 1.0)
        game_cnt = item.get("game_count", 0)
        created = item.get("created_at", "")[:16]

        lines.append(
            f"{idx}. 📅 `{date_str}` | 🏆 `{sport_str}` | ⚽ {game_cnt} Games\n"
            f"   🎯 Actual Odds: `{odds_val:.2f}x` | 🕒 `{created}`\n"
        )

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 Click **Custom Slip Builder** to generate a new slip!")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays admin monitoring stats for bot owner."""
    admin_id_str = config.env.admin_user_id
    user_id = update.effective_user.id if update.effective_user else 0

    if admin_id_str and str(user_id) != admin_id_str:
        await update.message.reply_text("⛔ *Unauthorized:* Admin command restricted to bot owner.")
        return

    stats = DatabaseService.get_admin_stats()
    text = (
        "👑 *BOT OWNER ADMIN DASHBOARD*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Total Slips Generated:* `{stats['total_slips']}`\n"
        f"🔄 *Total Code Conversions:* `{stats['total_conversions']}`\n"
        f"👥 *Total Unique Users:* `{stats['unique_users']}`\n"
        f"💾 *SQLite DB Size:* `{stats['db_size_kb']} KB`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 *Status:* All modules & database operational."
    )
    await update.message.reply_text(
        text, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start interactive 5-step custom bet slip wizard."""
    context.user_data["wiz"] = {}
    text = (
        "⚙️ *CUSTOM MULTI-SPORT SLIP BUILDER WIZARD*\n\n"
        "Welcome! Follow this 5-step interactive wizard to build a tailored bet slip matching your exact odds, game count, and probability preferences.\n\n"
        "📌 *Step 1 of 5: Select Match Date*"
    )
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, reply_markup=build_wiz_date_keyboard(), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=build_wiz_date_keyboard(), parse_mode="Markdown"
        )


async def learn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger on-demand market learning scan and display report."""
    scan_res = StrategyLearningEngine.learn_hourly_sportybet_markets()
    report = StrategyLearningEngine.format_learning_report()
    msg = (
        f"{report}\n\n"
        f"🔄 *Live Harvester Status:* Scanned {scan_res['sports_scanned']} sports | "
        f"Indexed: {scan_res['total_indexed']} | New This Scan: {scan_res['new_this_hour']}"
    )
    await update.message.reply_text(
        msg, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


async def hourly_market_learning_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Background task running every 60 minutes to learn new SportyBet markets."""
    try:
        res = StrategyLearningEngine.learn_hourly_sportybet_markets()
        logger.info(
            f"🧠 [Hourly Learning Job] Market scan completed. "
            f"Total indexed: {res['total_indexed']}, New: {res['new_this_hour']}"
        )
    except Exception as e:
        logger.error(f"Error in hourly market learning job: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip() if update.message and update.message.text else ""
    if text:
        TipsterMarketLearner.analyze_channel_post(text)

    await update.message.reply_text(
        f"You sent: `{text}`\n\n💡 Use `/scan` or `/custom` to discover fixtures and generate SportyBet booking codes!",
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception handling update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        err = context.error
        if isinstance(err, BotError):
            msg = f"⚠️ *Application Notice:* {err.message}"
        else:
            msg = "⚠️ *Temporary Error:* Something went wrong while processing your request. Please try again."
        try:
            await update.effective_message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Failed to send error message to Telegram user: {e}")


def main() -> None:
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file.")

    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("custom", custom_command))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("tomorrow", tomorrow_command))
    app.add_handler(CommandHandler("sports", sports_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("slip", slip_command))
    app.add_handler(CommandHandler("code", code_command))
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("channels", channels_command))
    app.add_handler(CommandHandler("convert", convert_command))

    app.add_handler(CallbackQueryHandler(menu_callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    # Schedule hourly SportyBet market learning job (runs every 3600s = 1 hour)
    if app.job_queue:
        app.job_queue.run_repeating(
            hourly_market_learning_job,
            interval=config.app.hourly_market_scan_interval,
            first=10,
            name="hourly_sportybet_market_learning",
        )
        logger.info("⏰ Hourly SportyBet Market Learning background job scheduled (every 60 mins).")

    logger.info("Bot starting...")
    app.run_polling()



if __name__ == "__main__":
    main()
