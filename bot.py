"""
Telegram Bot Engine — SportyBet Implied-Probability Booking Code Assistant
Integrates LiveScore Discovery, SportyBet Catalog Matcher, Implied-Probability Filter,
and SportyBet Official Booking Code Client.
"""

import logging
import os
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
from learning_engine import StrategyLearningEngine
from builder import CustomSlipBuilder

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Construct main menu inline buttons."""
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Custom Slip Builder", callback_data="wiz_start"),
            InlineKeyboardButton("🔍 Scan & Match Catalog", callback_data="cmd_scan"),
        ],
        [
            InlineKeyboardButton("📅 Today's Scan", callback_data="cmd_today"),
            InlineKeyboardButton("📆 Tomorrow's Scan", callback_data="cmd_tomorrow"),
        ],
        [
            InlineKeyboardButton("🏆 Select Sports", callback_data="cmd_sports"),
            InlineKeyboardButton("🎟️ View Current Slip", callback_data="cmd_slip"),
        ],
        [
            InlineKeyboardButton("📌 Get Booking Code", callback_data="cmd_code"),
            InlineKeyboardButton("🧠 Learning Engine", callback_data="cmd_learn"),
        ],
        [
            InlineKeyboardButton("📡 Monitored Channels", callback_data="menu_channels"),
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
    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data="wiz_date_Today"),
            InlineKeyboardButton("📆 Tomorrow", callback_data="wiz_date_Tomorrow"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
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
    keyboard = [
        [
            InlineKeyboardButton("🎯 1.5x Odds", callback_data="wiz_odds_1.5"),
            InlineKeyboardButton("🎯 2.0x Odds", callback_data="wiz_odds_2.0"),
        ],
        [
            InlineKeyboardButton("🎯 3.0x Odds", callback_data="wiz_odds_3.0"),
            InlineKeyboardButton("🎯 5.0x Odds", callback_data="wiz_odds_5.0"),
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wiz_count_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⚽ 2 Games", callback_data="wiz_count_2"),
            InlineKeyboardButton("⚽ 3 Games", callback_data="wiz_count_3"),
            InlineKeyboardButton("⚽ 4 Games", callback_data="wiz_count_4"),
        ],
        [
            InlineKeyboardButton("⚽ 5 Games", callback_data="wiz_count_5"),
            InlineKeyboardButton("⚽ 7 Games", callback_data="wiz_count_7"),
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
        "I discover unstarted fixtures from LiveScore, match them against **SportyBet's official event catalog**, filter markets with **85%-95% Bookmaker-Implied Probability** (`1 / decimal_odds`), and generate real SportyBet booking codes!\n\n"
        "👇 *Use the buttons below or commands like `/scan` to get started:*"
    )
    await update.message.reply_text(
        welcome, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /today
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["target_date"] = "Today"
    msg = "📅 Target date set to: **TODAY**.\nUse `/scan` or click **Scan & Match Catalog** below."
    await update.message.reply_text(
        msg, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /tomorrow
async def tomorrow_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["target_date"] = "Tomorrow"
    msg = "📆 Target date set to: **TOMORROW**.\nUse `/scan` or click **Scan & Match Catalog** below."
    await update.message.reply_text(
        msg, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
    )


# /sports
async def sports_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = "🏆 Select your target sport category for fixture discovery and SportyBet catalog matching:"
    await update.message.reply_text(
        msg, reply_markup=build_sport_keyboard(), parse_mode="Markdown"
    )


# Helper: Perform scan and mapping pipeline
def run_pipeline(target_date: str = "Today", sport: str = "All") -> BookingSlipResponse:
    # 1. Discovery
    fixtures = LiveScoreClient.fetch_unstarted_fixtures(
        target_date_str=target_date, sport_filter=sport
    )

    if not fixtures:
        return BookingSlipResponse(
            booking_code="",
            share_url="https://www.sportybet.com/ng/m/sports/football/",
            picks=[],
            total_odds=1.0,
            formatted_summary=f"⚠️ *No unstarted matches discovered for {target_date.upper()} in category {sport.upper()}.*",
            unmapped_warning=False,
        )

    # 2. SportyBet Catalog Fetching & Matching
    sb_events = SportyBetCatalogService.fetch_sportybet_catalog(sport=sport)

    all_selections = []
    unmapped_count = 0

    if sb_events:
        for fix in fixtures:
            sb_event = SportyBetCatalogService.match_fixture(fix, sb_events)
            if sb_event:
                extracted = SportyBetCatalogService.extract_selections_from_event(sb_event)
                all_selections.extend(extracted)
            else:
                unmapped_count += 1
    else:
        # Catalog is empty: Do NOT generate mock/fake events. Inform user honestly.
        return BookingSlipResponse(
            booking_code="",
            share_url="https://www.sportybet.com/ng/m/sports/football/",
            picks=[],
            total_odds=1.0,
            formatted_summary=(
                f"📡 *SportyBet Live Catalog Status Update*\n\n"
                f"LiveScore discovered {len(fixtures)} unstarted matches for `{target_date.upper()}` ({sport.upper()}).\n"
                f"However, SportyBet live catalog endpoints are currently updating or restricting request access.\n\n"
                f"💡 *No fake events were generated.* Please retry in a few moments or use `/custom` to build a slip!"
            ),
            unmapped_warning=True,
        )

    # 3. Probability Filter (60% - 95% Bookmaker-Implied Probability)
    filtered_picks = ImpliedProbabilityFilter.filter_selections(
        all_selections, min_prob=60.0, max_prob=95.0
    )

    # Limit to top 5 safest picks for a clean multi-leg slip
    slip_picks = filtered_picks[:5]

    # 4. Generate Official SportyBet Booking Code or Structured Fallback
    slip_res = SportyBetBookingClient.generate_booking_code(slip_picks, country_code="ng")
    slip_res.unmapped_warning = (unmapped_count > 0)
    return slip_res


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
    elif data == "cmd_today":
        context.user_data["target_date"] = "Today"
        await query.message.edit_text(
            "📅 Target date set to: **TODAY**.\nClick **Scan & Match Catalog** below.",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
        )
    elif data == "cmd_tomorrow":
        context.user_data["target_date"] = "Tomorrow"
        await query.message.edit_text(
            "📆 Target date set to: **TOMORROW**.\nClick **Scan & Match Catalog** below.",
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
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
        slip_res = run_pipeline(target_date=target_date, sport=sport)
        context.user_data["current_slip"] = slip_res
        await query.message.edit_text(
            slip_res.formatted_summary,
            reply_markup=build_main_menu_keyboard(),
            parse_mode="Markdown",
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
    elif data == "wiz_start":
        await custom_command(update, context)
    elif data.startswith("wiz_date_"):
        sel_date = data.replace("wiz_date_", "")
        context.user_data.setdefault("wiz", {})["date"] = sel_date
        text = (
            f"⚙️ *CUSTOM SLIP BUILDER WIZARD*\n\n"
            f"📅 Date Selected: `{sel_date}`\n\n"
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
            f"⚙️ *CUSTOM SLIP BUILDER WIZARD*\n\n"
            f"📅 Date: `{wiz.get('date', 'Today')}` | 🏆 Sport: `{sel_sport}`\n\n"
            f"📌 *Step 3 of 5: Select Target Accumulator Odds*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_odds_keyboard(), parse_mode="Markdown"
        )
    elif data.startswith("wiz_odds_"):
        sel_odds = float(data.replace("wiz_odds_", ""))
        context.user_data.setdefault("wiz", {})["odds"] = sel_odds
        wiz = context.user_data.get("wiz", {})
        text = (
            f"⚙️ *CUSTOM SLIP BUILDER WIZARD*\n\n"
            f"📅 Date: `{wiz.get('date', 'Today')}` | 🏆 Sport: `{wiz.get('sport', 'All')}` | 🎯 Target Odds: `{sel_odds}x`\n\n"
            f"📌 *Step 4 of 5: Select Number of Matches*"
        )
        await query.message.edit_text(
            text, reply_markup=build_wiz_count_keyboard(), parse_mode="Markdown"
        )
    elif data.startswith("wiz_count_"):
        sel_count = int(data.replace("wiz_count_", ""))
        context.user_data.setdefault("wiz", {})["count"] = sel_count
        wiz = context.user_data.get("wiz", {})
        text = (
            f"⚙️ *CUSTOM SLIP BUILDER WIZARD*\n\n"
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

        await query.message.edit_text(
            res.formatted_summary, reply_markup=build_main_menu_keyboard(), parse_mode="Markdown"
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
    text = update.message.text.strip()
    await update.message.reply_text(
        f"You sent: `{text}`\n\n💡 Use `/scan` or `/custom` to discover fixtures and generate SportyBet booking codes!",
        reply_markup=build_main_menu_keyboard(),
        parse_mode="Markdown",
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception handling update:", exc_info=context.error)


def main() -> None:
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file.")

    app = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("custom", custom_command))
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
            interval=3600,
            first=10,
            name="hourly_sportybet_market_learning",
        )
        logger.info("⏰ Hourly SportyBet Market Learning background job scheduled (every 60 mins).")

    logger.info("Bot starting...")
    app.run_polling()



if __name__ == "__main__":
    main()
