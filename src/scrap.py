from concurrent.futures import ThreadPoolExecutor, as_completed

import requests as rq
from bs4 import BeautifulSoup

from helpers import Pack, UserConfig

# def _page_thread(
#     session: rq.Session, page_num: int, nations: str, vehicles: str, tiers: str
# ) -> list[Pack]:
#     url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&page={page_num}&search={nations},{vehicles},{tiers}&dir=asc&order=price&tag=1"
#     page = session.get(url)
#     soup = BeautifulSoup(page.content, "html.parser")
#     return _get_packs_for_page(soup)


def _get_packs_for_page(soup: BeautifulSoup) -> list[Pack]:
    all_packs: list[Pack] = []
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

    for link, name, price in zip(links, labels, prices):
        all_packs.append(Pack(link, name, price))

    return all_packs


def scrap(user_config: UserConfig) -> None:
    nations = ",".join(nation.value for nation in user_config.selected_nations)
    tiers = ",".join(tier.value for tier in user_config.selected_tiers)
    vehicles = ",".join(type.value for type in user_config.selected_types)

    url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&page=1&search={nations},{vehicles},{tiers}&dir=asc&order=price&tag=1"
    all_packs: list[Pack] = []

    # Process page 1
    session = rq.Session()  # shared session for speed
    page = session.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    all_packs.extend(_get_packs_for_page(soup))

    # Get other pages
    pages = soup.find_all("a", class_="pager__page hover-link hover-link_blue")
    pages = [
        int(page.get_text(strip=True)) for page in pages if page.get_text(strip=True)
    ]

    # if len(pages) != 0:
    #     # Process them in parrallel
    #     with ThreadPoolExecutor(max_workers=min(8, len(pages))) as executor:
    #         futures = [
    #             executor.submit(_page_thread, session, page, nations, vehicles, tiers)
    #             for page in pages
    #         ]

    #         for future in as_completed(futures):
    #             all_packs.extend(future.result())

    for page in pages:
        url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&page={page}&search={nations},{vehicles},{tiers}&dir=asc&order=price&tag=1"
        page = session.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        all_packs.extend(_get_packs_for_page(soup))

    # Sort packs by price
    all_packs.sort(key=lambda p: float(p.price.split(" ")[0]))

    # Replace packs
    user_config.last_packs = user_config.packs
    user_config.packs = all_packs
    user_config.last_url = user_config.generated_url
    user_config.generated_url = url
