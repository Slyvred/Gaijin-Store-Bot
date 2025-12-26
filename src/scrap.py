import os

# from concurrent.futures import ThreadPoolExecutor, as_completed
import requests as rq
from bs4 import BeautifulSoup
from requests.sessions import Session

from helpers import Pack, UserConfig

flaresolverr_url = str(os.getenv("FLARESOLVERR_URL"))


# def _page_thread(
#     session: rq.Session, page_num: int, nations: str, vehicles: str, tiers: str
# ) -> list[Pack]:
#     url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&page={page_num}&search={nations}%2C{vehicles}%2C{tiers}&tag=1"
#     page = session.get(url)

#     if page.status_code != 200:
#         print(f"ERROR: Failed to scrap page, status_code={page.status_code}")
#         page = _scrap_with_flaresolverr(url, session)

#     soup = BeautifulSoup(page.text, "html.parser")
#     return _get_packs_for_page(soup)


def _scrap_with_flaresolverr(url: str, session: Session) -> dict[str, str] | None:
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": 10000,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = session.post(flaresolverr_url, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("status") == "ok":
            html_content = response_data["solution"]["response"]
            # cookies = response_data["solution"]["cookies"]
            print("Cloudflare challenge solved !")
            return {"text": html_content}
        else:
            print(f"FlareSolverr failed: {response_data.get('message')}")
            return None

    except Exception as e:
        print(f"Error : {e}")
        return None


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
    nations = "%2C".join(nation.value for nation in user_config.selected_nations)
    tiers = "%2C".join(tier.value for tier in user_config.selected_tiers)
    vehicles = "%2C".join(type.value for type in user_config.selected_types)

    url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&page=1&search={nations}%2C{vehicles}%2C{tiers}&tag=1"
    all_packs: list[Pack] = []
    print(url)

    # Process page 1
    session = rq.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        }
    )
    page = session.get(url)
    if page.status_code != 200:
        print(f"ERROR: Failed to scrap page, status_code={page.status_code}")
        page = _scrap_with_flaresolverr(url, session)

    if page is None:
        print("ERROR: Failed to scrap page with flaresolverr, aborting")
        return

    soup = BeautifulSoup(page.text, "html.parser")
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
        url = f"https://store.gaijin.net/catalog.php?category=WarThunderPacks&dir=asc&order=price&page={page}&search={nations}%2C{vehicles}%2C{tiers}&tag=1"
        print(url)
        page = session.get(url)

        if page.status_code != 200:
            print(f"ERROR: Failed to scrap page, status_code={page.status_code}")
            page = _scrap_with_flaresolverr(url, session)

        if page is None:
            print("ERROR: Failed to scrap page with flaresolverr, aborting")
            return

        soup = BeautifulSoup(page.text, "html.parser")
        all_packs.extend(_get_packs_for_page(soup))

    # Sort packs by price
    all_packs.sort(key=lambda p: float(p.price.split(" ")[0]))

    # Replace packs
    user_config.last_packs = user_config.packs
    user_config.packs = all_packs
    user_config.last_url = user_config.generated_url
    user_config.generated_url = url
