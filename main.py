import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import dotenv
import os
import bs4
import requests as rq

dotenv.load_dotenv()
api_token = os.getenv('API_TOKEN')
chat_id = 0
store_url = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&search=wt_air%2Cwt_rank8%2Cwt_rank7&tag=1"
previous_packs = {}
# previous_packs = {'MiG-23ML Pack': {'price': '19.99 €', 'link': 'https://store.gaijin.net/story.php?id=11807'}, 'F-4S Phantom II Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=12048'}, 'F-20A Tigershark Pack': {'price': '74.99 €', 'link': 'https://store.gaijin.net/story.php?id=13237'}, 'Tornado IDS WTD 61 Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=13035'}, 'Saab J35XS Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11813'}, 'Mirage F1C-200 Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11810'}, 'A-10A Thunderbolt (Early) Pack': {'price': '59.99 €', 'link': 'https://store.gaijin.net/story.php?id=10896'}, 'Pre-order - MiG-21 Bison Pack': {'price': '74.99 €', 'link': 'https://store.gaijin.net/story.php?id=13512'}, 'Su-25K Pack': {'price': '59.99 €', 'link': 'https://store.gaijin.net/story.php?id=11444'}, 'F-5C Pack': {'price': '64.99 €', 'link': 'https://store.gaijin.net/story.php?id=10174'}, 'MiG-21bis "Lazur-M" Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11806'}, 'Su-39 Pack': {
#     'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=12204'}, 'F-4EJ Phantom II ADTW Pack': {'price': '99.99 €', 'link': 'https://store.gaijin.net/story.php?id=11826'}, 'Wyvern Pack': {'price': '29.99 €', 'link': 'https://store.gaijin.net/story.php?id=5267'}, 'F-4J(UK) Phantom II Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11808'}, 'Kfir Canard Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11812'}, 'F-104S TAF Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11809'}, 'A-6E TRAM Intruder Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11805'}, 'Mustang Pack': {'price': '29.99 €', 'link': 'https://store.gaijin.net/story.php?id=4194'}, 'Dora Pack': {'price': '29.99 €', 'link': 'https://store.gaijin.net/story.php?id=3528'}, 'A-5C Pack': {'price': '59.99 €', 'link': 'https://store.gaijin.net/story.php?id=10408'}, "Ezer Weizman's Spitfire Pack": {'price': '29.99 €', 'link': 'https://store.gaijin.net/story.php?id=10590'}, 'J-7D Pack': {'price': '69.99 €', 'link': 'https://store.gaijin.net/story.php?id=11811'}}


def extract_price(pack):
    """Extrait le prix d'un pack

    Args:
        pack (dict): Le dictionnaire qui contient les informations du pack {label: {price: _price_, link: _link_}

    Returns:
        float: Le prix du pack
    """
    return float(pack['price'].split(' ')[0])


def scrap_packs():
    """Scrap le site de War Thunder pour récupérer les packs

    Returns:
        dict: Un dictionnaire qui contient le nom de chaque pack (comme clée) avec leur prix et lien comme valeur
    """
    page = rq.get(store_url)
    soup = bs4.BeautifulSoup(page.content, 'lxml')
    packs = soup.find_all(
        'div', class_='showcase__item product-widget js-cart__cart-item')
    labels = [pack.find(
        'div', class_='product-widget-description__title').text.strip() for pack in packs]
    prices = [pack.find(
        'span', class_='showcase-item-price__default').text.strip() for pack in packs]
    links = [pack.find('a', class_='product-widget__link').get('href')
             for pack in packs]

    # Map qui contient label (clée), prix et lien comme valeur
    packs = {label: {'price': price, 'link': link}
             for label, price, link in zip(labels, prices, links)}

    # Trie les packs par ordre prix croissant
    # Commenté car les packs sont déjà triés par prix croissant avec le nouvel url
    # packs = dict(sorted(packs.items(), key=lambda item: extract_price(item[1])))

    return packs


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Répond à la commande /start, envoie un message de bienvenue

    Args:
        update (Update): L'objet Update qui contient les informations de la mise à jour
        context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
    """
    global chat_id
    global previous_packs
    chat_id = update.effective_chat.id
    previous_packs = scrap_packs()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bonjour, je suis un bot qui vous permet de consulter les packs de War Thunder. Pour voir les packs disponibles, tapez /packs.\nVous recevrez une notification si le prix d'un pack a changé ou si un nouveau pack est disponible.")


async def get_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envoie un message contenant les packs de War Thunder, si le prix d'un pack a changé, le message contiendra l'ancien et le nouveau prix

    Args:
        update (Update): L'objet Update qui contient les informations de la mise à jour
        context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
    """
    global previous_packs
    global chat_id
    chat_id = update.effective_chat.id

    packs = scrap_packs()
    text = "\n\n".join([f"<a href='{pack['link']}'><b>{
                       label}</b></a>\nPrix: {pack['price']}" for label, pack in packs.items()])

    for label, pack in packs.items():
        if label not in previous_packs.keys():
            print(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
            text += f"\n\nLe pack <a href='{pack['link']}'>{
                label}</a> est nouveau!\nPrix: {pack['price']}"
        elif pack['price'] != previous_packs[label]['price']:
            print(f"Le pack {label} a changé de prix.\nAncien prix: {
                  previous_packs[label]['price']}\nNouveau prix: {pack['price']}")
            text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {
                previous_packs[label]['price']}\nNouveau prix: {pack['price']}"

    previous_packs = packs

    await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode=ParseMode.HTML)


async def send_price_change_notification(context: ContextTypes.DEFAULT_TYPE):
    """Envoie une notification si le prix d'un pack a changé avec le lien du pack concerné, l'ancien et le nouveau prix

    Args:
        context (ContextTypes.DEFAULT_TYPE): Le contexte de l'application
    """

    global previous_packs
    global chat_id

    if chat_id == 0:
        print("chat_id n'est pas défini!")
        return

    packs = scrap_packs()
    text = "<b>⚠️Alerte !⚠️</b>"

    for label, pack in packs.items():
        if label not in previous_packs.keys():
            print(f"Le pack {label} est nouveau!\nPrix: {pack['price']}")
            text += f"\n\nLe pack <a href='{pack['link']}'>{
                label}</a> est nouveau!\nPrix: {pack['price']}"
        elif pack['price'] != previous_packs[label]['price']:
            print(f"Le pack {label} a changé de prix.\nAncien prix: {
                  previous_packs[label]['price']}\nNouveau prix: {pack['price']}")
            text += f"\n\nLe pack <a href='{pack['link']}'>{label}</a> a changé de prix.\nAncien prix: {
                previous_packs[label]['price']}\nNouveau prix: {pack['price']}"

    previous_packs = packs
    if text != "<b>⚠️Alerte !⚠️</b>":
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)

if __name__ == '__main__':

    application = ApplicationBuilder().token(api_token).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    get_packs_handler = CommandHandler('packs', get_packs)
    application.add_handler(get_packs_handler)

    # Automatiser l'envoi des notifications de changement de prix, toutes les 5 minutes
    job_queue = application.job_queue
    job_minute = job_queue.run_repeating(
        send_price_change_notification, interval=300, first=0)

    application.run_polling()
