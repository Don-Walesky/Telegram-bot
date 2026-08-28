"""
Telegram UI Keyboards & Button Builders
Centralized inline keyboard builders for main menu, sport selections, wizards, and channel siever options.
"""

from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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
