import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, EnumType

import bs4
import requests as rq
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)


class Tier(Enum):
    I = "wt_rank1"
    II = "wt_rank2"
    III = "wt_rank3"
    IV = "wt_rank4"
    V = "wt_rank5"
    VI = "wt_rank6"
    VII = "wt_rank7"
    VIII = "wt_rank8"


class Nation(Enum):
    USSR = "wt_ussr"
    GERMANY = "wt_germany"
    USA = "wt_usa"
    BRITAIN = "wt_britain"
    JAPAN = "wt_japan"
    SWEDEN = "wt_sweden"
    CHINA = "wt_china"
    FRANCE = "wt_france"
    ITALY = "wt_italy"


class VehiculeType(Enum):
    ARMY = "wt_tanks"
    AVIATION = "wt_air"
    FLEET = "wt_navy"
    HELICOPTER = "wt_helicopters"


@dataclass
class UserConfig:
    selected_tiers: list[Tier] = field(default_factory=list)
    selected_types: list[VehiculeType] = field(default_factory=list)
    selected_nations: list[Nation] = field(default_factory=list)


class Bot:
    def __init__(self, token: str):
        self.application = ApplicationBuilder().token(token).build()
        self.users_configs = defaultdict(UserConfig)

        self.application.add_handlers(
            [
                CommandHandler("hello", self.hello),
                CommandHandler("tiers", self.send_keyboard_tiers),
                CommandHandler("nations", self.send_keyboard_nations),
                CommandHandler("vehicles", self.send_keyboard_vehicules),
                CallbackQueryHandler(self.button),
            ]
        )

    async def hello(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(f"Hello {update.effective_user.first_name}")  # type:ignore

    async def _send_keyboard_enum(
        self,
        enum: EnumType,
        line_width: int,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        keyboard_auto = []
        rows = []

        user_config = self.users_configs[update.effective_user.id]

        for item in enum:
            text = ""
            match item:
                case Tier():
                    text = (
                        "✅ " + item.name
                        if item in user_config.selected_tiers
                        else item.name
                    )
                case Nation():
                    text = (
                        "✅ " + str(item.name).capitalize()
                        if item in user_config.selected_nations
                        else str(item.name).capitalize()
                    )
                case VehiculeType():
                    text = (
                        "✅ " + str(item.name).capitalize()
                        if item in user_config.selected_types
                        else str(item.name).capitalize()
                    )

            rows.append(InlineKeyboardButton(text=text, callback_data=item.value))
            if len(rows) == line_width:
                keyboard_auto.append(rows)
                rows = []

        if rows:
            keyboard_auto.append(rows)

        reply_markup = InlineKeyboardMarkup(keyboard_auto)

        await update.message.reply_text("Please choose:", reply_markup=reply_markup)  # type: ignore

    async def send_keyboard_tiers(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._send_keyboard_enum(Tier, 4, update, context)

    async def send_keyboard_nations(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._send_keyboard_enum(Nation, 3, update, context)

    async def send_keyboard_vehicules(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self._send_keyboard_enum(VehiculeType, 2, update, context)

    def _parse_query(self, query: CallbackQuery | None):
        if query is None:
            return
        data = query.data.split(" ")[-1]
        data = Tier(data)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()  # type: ignore

        user_config = self.users_configs[update.effective_user.id]

        data = self._parse_query(query)

        # if tier not in user_config.selected_tiers:
        #     user_config.selected_tiers.append(tier)
        # else:
        #     user_config.selected_tiers.remove(tier)

        await query.edit_message_text(text=f"Selected tiers: {data}")  # type: ignore
