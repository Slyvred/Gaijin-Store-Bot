import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
import dotenv
import os
import bs4
import requests as rq
from functools import wraps

dotenv.load_dotenv()
api_token = os.getenv('API_TOKEN')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class Bot:
    def __init__(self, token):
        self.previous_packs = {} # Dictionnaire qui contient les packs précédents {chat_id: {label: {price: _price_, link: _link_}}
        self.selected_tiers = {} # Les tiers des avions sélectionnés {chat_id: {"%2Cwt_rank8", "%2Cwt_rank7"}}
        self.previous_selected_tiers = {} # Les tiers des avions sélectionnés précédemment
        self.store_url = {} # L'url du store de War Thunder avec les tiers sélectionnés {chat_id: "https://store.gaijin.net/..."}

        self.token = token
        self.application = ApplicationBuilder().token(api_token).build()

        self.start_handler = CommandHandler('start', self.start_callback)
        self.application.add_handler(self.start_handler)

        self.help_handler = CommandHandler('help', self.help_callback)
        self.application.add_handler(self.help_handler)

        self.get_packs_handler = CommandHandler('packs', self.get_packs_callback)
        self.application.add_handler(self.get_packs_handler)

        self.set_tiers_handler = CommandHandler('tiers', self.set_tiers_callback)
        self.application.add_handler(self.set_tiers_handler)

        self.inline_callback_handler = CallbackQueryHandler(self.inline_button_callback)
        self.application.add_handler(self.inline_callback_handler)

        # Automatiser l'envoi des notifications de changement de prix, toutes les 5 minutes
        self.job_queue = self.application.job_queue
        self.job_minute = self.job_queue.run_repeating(self.send_price_change_notification_callback, interval=300, first=0)
        logging.info("Bot démarré!")

    def run(self):
        self.application.run_polling()

    def send_action(action):
        """Sends `action` while processing func command."""

        def decorator(func):
            @wraps(func)
            async def command_func(self, update, context, *args, **kwargs):
                await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
                return await func(self, update, context,  *args, **kwargs)
            return command_func
        
        return decorator

    def __extract_price(self, pack):
        """Extrait le prix d'un pack

        Args:
            pack (dict): Le dictionnaire qui contient les informations du pack {label: {price: _price_, link: _link_}

        Returns:
            float: Le prix du pack
        """
        return float(pack['price'].split(' ')[0])

    def __scrap_packs(self, chat_id):
        """Scrap le site de War Thunder pour récupérer les packs

        Returns:
            dict: Un dictionnaire qui contient le nom de chaque pack (comme clée) avec leur prix et lien comme valeur
        """
        try:
            page = rq.get(self.store_url.get(chat_id))
            soup = bs4.BeautifulSoup(page.content, 'lxml')
            packs = soup.find_all('div', class_='showcase__item product-widget js-cart__cart-item')
            labels = [pack.find('div', class_='product-widget-description__title').text.strip() for pack in packs]
            prices = [pack.find('span', class_='showcase-item-price__default').text.strip() for pack in packs]
            links = [pack.find('a', class_='product-widget__link').get('href') for pack in packs]

            # Map qui contient label (clée), prix et lien comme valeur
            packs = {label: {'price': price, 'link': link} for label, price, link in zip(labels, prices, links)}
            return packs
        except (rq.RequestException, bs4.BeautifulSoup) as e:
            logging.error(f"Erreur lors de la récupération des packs: {e}")
            return {}
        
    @send_action(action=ChatAction.TYPING)
    async def help_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Répond à la commande /help, envoie un message d'aide

        Args:
            update (Update): L'objet Update qui contient les informations de la mise à jour
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """
        text = "Ce bot vous permet de consulter les packs de War Thunder. Voici les commandes disponibles:\n\n/start - Démarre le bot et envoie un message de bienvenue.\n/packs - Affiche les packs disponibles.\n/tiers - Permet de choisir les tiers des avions que vous souhaitez voir dans les packs.\n/help - Affiche ce message d'aide."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    @send_action(action=ChatAction.TYPING)
    async def start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Répond à la commande /start, envoie un message de bienvenue

        Args:
            update (Update): L'objet Update qui contient les informations de la mise à jour
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """
        self.selected_tiers.update({update.effective_chat.id: {"%2Cwt_rank8", "%2Cwt_rank7"}})
        self.previous_selected_tiers = self.selected_tiers.copy()
        self.store_url.update({update.effective_chat.id: "https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&search=wt_air" + ''.join(self.selected_tiers[update.effective_chat.id]) + "&tag=1"})
        self.previous_packs[update.effective_chat.id] = self.__scrap_packs(update.effective_chat.id)

        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bonjour, je suis un bot qui vous permet de consulter les packs de War Thunder. Pour voir les packs disponibles, tapez /packs.\nVous recevrez une notification si le prix d'un pack a changé ou si un nouveau pack est disponible.")

    @send_action(action=ChatAction.TYPING)
    async def get_packs_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Envoie un message contenant les packs de War Thunder, si le prix d'un pack a changé, le message contiendra l'ancien et le nouveau prix

        Args:
            update (Update): L'objet Update qui contient les informations de la mise à jour
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """

        packs = self.__scrap_packs(update.effective_chat.id)
        if not packs:
            logging.error("Erreur lors du scraping des packs.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Erreur lors du scraping des packs.")
            return
        
        text = "\n\n".join([f"<a href='{pack['link']}'><b>{label}</b></a>\nPrix: {pack['price']}" for label, pack in packs.items()])
        for label, pack in packs.items():
            if label not in self.previous_packs[update.effective_chat.id].keys() and self.previous_packs[update.effective_chat.id].keys() != {} and self.previous_selected_tiers[update.effective_chat.id] == self.selected_tiers[update.effective_chat.id]:
                logging.info(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> est nouveau!\nPrix: {pack['price']}"

            if label in self.previous_packs[update.effective_chat.id].keys() and pack['price'] != self.previous_packs[update.effective_chat.id][label]['price']:
                logging.info(f"Le pack {label} a changé de prix.\nAncien prix: {self.previous_packs[label]['price']}\nNouveau prix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {self.previous_packs[update.effective_chat.id][label]['price']}\nNouveau prix: {pack['price']}"

        self.previous_packs[update.effective_chat.id] = packs

        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.HTML)

    @send_action(action=ChatAction.TYPING)
    async def set_tiers_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = []
        counter = 1

        for row in range(2):
            keyboard_row = []
            for col in range(4):
                text = f"{counter} {'✅' if ('%2Cwt_rank' + str(counter)) in self.selected_tiers[update.effective_chat.id] else ''}"
                keyboard_row.append(InlineKeyboardButton(text, callback_data=f"tier_{counter}"))
                counter += 1
            keyboard.append(keyboard_row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Choisissez le tier des avions que vous souhaitez voir dans les packs:", reply_markup=reply_markup)

    async def inline_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        tier = '%2Cwt_rank' + query.data.split('_')[1]

        if tier in self.selected_tiers[update.effective_chat.id]:
            self.previous_selected_tiers[update.effective_chat.id] = self.selected_tiers[update.effective_chat.id].copy()
            self.selected_tiers[update.effective_chat.id].remove(tier)
            self.store_url[update.effective_chat.id] = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&search=wt_air" + ''.join(self.selected_tiers[update.effective_chat.id]) + "&tag=1"
        else:
            self.previous_selected_tiers[update.effective_chat.id] = self.selected_tiers[update.effective_chat.id].copy()
            self.selected_tiers[update.effective_chat.id].add(tier)
            self.store_url[update.effective_chat.id] = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&search=wt_air" + ''.join(self.selected_tiers[update.effective_chat.id]) + "&tag=1"

        await query.answer()

        keyboard = []
        counter = 1

        for row in range(2):
            keyboard_row = []
            for col in range(4):
                text = f"{counter} {'✅' if ('%2Cwt_rank' + str(counter)) in self.selected_tiers[update.effective_chat.id] else ''}"
                keyboard_row.append(InlineKeyboardButton(text, callback_data=f"tier_{counter}"))
                counter += 1
            keyboard.append(keyboard_row)

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)


    @send_action(action=ChatAction.TYPING)
    async def send_price_change_notification_callback(self, context: ContextTypes.DEFAULT_TYPE):
        """Envoie une notification si le prix d'un pack a changé"""
        if not self.selected_tiers.keys():
            logging.error("Aucun utilisateur n'est défini!")
            return

        for chat_id in self.selected_tiers.keys():
            packs = self.__scrap_packs(self.selected_tiers[chat_id])

            if not packs:
                logging.error(f"Erreur lors du scraping des packs pour le chat {chat_id}.")
                await context.bot.send_message(chat_id=chat_id, text="Erreur lors du scraping des packs.")
                continue

            text = "<b>⚠️ Alerte ! ⚠️</b>"

            for label, pack in packs.items():
                if label not in self.previous_packs[chat_id].keys() and self.previous_packs[chat_id].keys() != {} and self.previous_selected_tiers[chat_id] == self.selected_tiers[chat_id]:
                    logging.info(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
                    text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> est nouveau!\nPrix: {pack['price']}"

                if label in self.previous_packs[chat_id].keys() and pack['price'] != self.previous_packs[chat_id][label]['price']:
                    logging.info(f"Le pack {label} a changé de prix.\nAncien prix: {self.previous_packs[chat_id][label]['price']}\nNouveau prix: {pack['price']}")
                    text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {self.previous_packs[chat_id][label]['price']}\nNouveau prix: {pack['price']}"

            self.previous_packs[chat_id] = packs
            if text != "<b>⚠️ Alerte ! ⚠️</b>":
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    bot = Bot(api_token)
    bot.run()
