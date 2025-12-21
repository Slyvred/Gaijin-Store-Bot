from collections import defaultdict
from enum import EnumType

import requests as rq
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from helpers import (
    Nation,
    Pack,
    Tier,
    UserConfig,
    VehiculeType,
    add_or_remove,
    escape_md_v2,
    format_pack,
    parse_query,
)


class Bot:
    def __init__(self, token: str):
        self.application = ApplicationBuilder().token(token).build()
        self.users_configs = defaultdict(UserConfig)

        self.application.add_handlers(
            [
                CommandHandler("tiers", self.send_keyboard_tiers),
                CommandHandler("nations", self.send_keyboard_nations),
                CommandHandler("vehicles", self.send_keyboard_vehicules),
                CommandHandler("packs", self.packs),
                CallbackQueryHandler(self.button),
            ]
        )
        self.application.job_queue.run_repeating(self.notify, interval=300, first=0)  # type:ignore

    def _generate_markup(self, enum: EnumType, line_width: int, update: Update):
        keyboard = []
        rows = []

        user_config = self.users_configs[update.effective_chat.id]  # type:ignore

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

            rows.append(InlineKeyboardButton(text=text, callback_data=item.value))  # type:ignore
            if len(rows) == line_width:
                keyboard.append(rows)
                rows = []

        # Last row
        if rows:
            keyboard.append(rows)

        return InlineKeyboardMarkup(keyboard)

    async def _send_keyboard_enum(
        self,
        enum: EnumType,
        line_width: int,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> None:
        reply_markup = self._generate_markup(enum, line_width, update)

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
        await self._send_keyboard_enum(VehiculeType, 3, update, context)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        await query.answer()  # type: ignore

        user_config = self.users_configs[update.effective_chat.id]  # type: ignore

        data = parse_query(query)
        new_markup = None
        match data:
            case Tier():
                add_or_remove(data, user_config.selected_tiers)
                new_markup = self._generate_markup(Tier, 4, update)
            case VehiculeType():
                add_or_remove(data, user_config.selected_types)
                new_markup = self._generate_markup(VehiculeType, 3, update)
            case Nation():
                add_or_remove(data, user_config.selected_nations)
                new_markup = self._generate_markup(Nation, 3, update)

        await query.edit_message_reply_markup(new_markup)  # type: ignore

    def _scrap(self, user_id: int) -> None:
        user_config = self.users_configs[user_id]  # type: ignore

        if user_config is None:
            return

        nations = ",".join(nation.value for nation in user_config.selected_nations)
        tiers = ",".join(tier.value for tier in user_config.selected_tiers)
        vehicles = ",".join(type.value for type in user_config.selected_types)

        url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&search={nations},{vehicles},{tiers}&tag=1"

        page = rq.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        packs = soup.find_all(
            "div", class_="showcase__item product-widget js-cart__cart-item"
        )

        labels = [
            pack.find("div", class_="product-widget-description__title").text.strip()  # type: ignore
            for pack in packs
        ]

        links = [
            str(pack.find("a", class_="product-widget__link").get("href"))  # type: ignore
            for pack in packs
        ]

        prices = []
        # Durant les soldes, le prix est affiché dans une balise différente
        for pack in packs:
            price_tag = pack.find(
                "span", class_="showcase-item-price__default"
            ) or pack.find("span", class_="showcase-item-price__new")

            if price_tag:
                prices.append(price_tag.text.strip())

        packs = []
        for link, name, price in zip(links, labels, prices):
            packs.append(Pack(link, name, price))

        # Replace packs
        user_config.last_packs = user_config.packs
        user_config.packs = packs
        user_config.last_url = user_config.generated_url
        user_config.generated_url = url

    async def packs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._scrap(update.effective_chat.id)  # Scrap packs  # type:ignore
        user_config = self.users_configs[update.effective_chat.id]  # type:ignore

        msg = "\n\n".join(
            f"[{name}]({link})\nPrix : {price}"
            for pack in user_config.packs
            for name, link, price in [format_pack(pack)]
        )

        await update.message.reply_markdown_v2(text=msg)  # type: ignore

    async def notify(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        for id in self.users_configs.keys():
            user_config = self.users_configs[id]
            self._scrap(id)

            if user_config.generated_url != user_config.last_url:
                return

            lines = []

            # Création d’un mapping pour comparaison rapide
            last_packs_by_name = {pack.name: pack for pack in user_config.last_packs}

            for pack in user_config.packs:
                name, link, price = format_pack(pack)
                old_pack = last_packs_by_name.get(pack.name)

                # Nouveau pack
                if old_pack is None:
                    lines.append(
                        f"🚨 Le pack [{name}]({link}) est nouveau \\! 🚨\nPrix : {price}"
                    )
                    continue

                # Changement de prix
                if pack.price != old_pack.price:
                    old_price = escape_md_v2(old_pack.price)
                    lines.append(
                        f"Le prix du pack [{name}]({link}) a changé \\!\n"
                        f"Ancien prix : {old_price}\n"
                        f"Nouveau prix : {price}"
                    )

            msg = "\n\n".join(lines)

            if msg:
                await context.bot.send_message(
                    chat_id=id, text=msg, parse_mode=ParseMode.MARKDOWN_V2
                )
