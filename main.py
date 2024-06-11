import logging
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
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

        self.chat_id = 0
        self.store_url = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&search=wt_air%2Cwt_rank8%2Cwt_rank7&tag=1"
        self.previous_packs = {}

        self.token = token
        self.application = ApplicationBuilder().token(api_token).build()

        self.start_handler = CommandHandler('start', self.__start)
        self.application.add_handler(self.start_handler)

        self.get_packs_handler = CommandHandler('packs', self.__get_packs)
        self.application.add_handler(self.get_packs_handler)

        # Automatiser l'envoi des notifications de changement de prix, toutes les 5 minutes
        self.job_queue = self.application.job_queue
        self.job_minute = self.job_queue.run_repeating(self.__send_price_change_notification, interval=300, first=0)
        logging.info("Bot démarré!")

    def run(self):
        self.application.run_polling()

    def __send_action(action):
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

    def __scrap_packs(self):
        """Scrap le site de War Thunder pour récupérer les packs

        Returns:
            dict: Un dictionnaire qui contient le nom de chaque pack (comme clée) avec leur prix et lien comme valeur
        """
        try:
            page = rq.get(self.store_url)
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

    @__send_action(action=ChatAction.TYPING)
    async def __start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Répond à la commande /start, envoie un message de bienvenue

        Args:
            update (Update): L'objet Update qui contient les informations de la mise à jour
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """
        self.chat_id = update.effective_chat.id
        self.previous_packs = self.__scrap_packs()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bonjour, je suis un bot qui vous permet de consulter les packs de War Thunder. Pour voir les packs disponibles, tapez /packs.\nVous recevrez une notification si le prix d'un pack a changé ou si un nouveau pack est disponible.")

    @__send_action(action=ChatAction.TYPING)
    async def __get_packs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Envoie un message contenant les packs de War Thunder, si le prix d'un pack a changé, le message contiendra l'ancien et le nouveau prix

        Args:
            update (Update): L'objet Update qui contient les informations de la mise à jour
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """
        self.chat_id = update.effective_chat.id

        packs = self.__scrap_packs()
        if not packs:
            logging.error("Erreur lors du scraping des packs.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Erreur lors du scraping des packs.")
            return
        
        text = "\n\n".join([f"<a href='{pack['link']}'><b>{label}</b></a>\nPrix: {pack['price']}" for label, pack in packs.items()])
        for label, pack in packs.items():
            if label not in self.previous_packs.keys():
                logging.info(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> est nouveau!\nPrix: {pack['price']}"

            elif pack['price'] != self.previous_packs[label]['price']:
                logging.info(f"Le pack {label} a changé de prix.\nAncien prix: {self.previous_packs[label]['price']}\nNouveau prix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {self.previous_packs[label]['price']}\nNouveau prix: {pack['price']}"

        self.previous_packs = packs

        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.HTML)

    @__send_action(action=ChatAction.TYPING)
    async def __send_price_change_notification(self, context: ContextTypes.DEFAULT_TYPE):
        """Envoie une notification si le prix d'un pack a changé avec le lien du pack concerné, l'ancien et le nouveau prix

        Args:
            context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
        """

        if self.chat_id == 0:
            logging.error("chat_id n'est pas défini!")
            return

        packs = self.__scrap_packs()

        if not packs:
            logging.error("Erreur lors du scraping des packs.")
            await context.bot.send_message(chat_id=self.chat_id, text="Erreur lors du scraping des packs.")
            return

        if not packs:
            logging.error("Erreur lors du scraping des packs.")
            return

        text = "<b>⚠️Alerte !⚠️</b>"

        for label, pack in packs.items():
            if label not in self.previous_packs.keys():
                logging.info(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> est nouveau!\nPrix: {pack['price']}"

            elif pack['price'] != self.previous_packs[label]['price']:
                logging.info(f"Le pack {label} a changé de prix.\nAncien prix: {self.previous_packs[label]['price']}\nNouveau prix: {pack['price']}")
                text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {self.previous_packs[label]['price']}\nNouveau prix: {pack['price']}"

        self.previous_packs = packs
        if text != "<b>⚠️Alerte !⚠️</b>":
            await context.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    bot = Bot(api_token)
    bot.run()