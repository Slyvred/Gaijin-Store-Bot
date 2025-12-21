from dataclasses import dataclass, field
from enum import Enum

from telegram import CallbackQuery


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
    # ALL = "all"


class VehiculeType(Enum):
    ARMY = "wt_tanks"
    AVIATION = "wt_air"
    FLEET = "wt_navy"
    HELICOPTER = "wt_helicopters"


@dataclass
class Pack:
    link: str
    name: str
    price: str


@dataclass
class UserConfig:
    selected_tiers: list[Tier] = field(default_factory=list)
    selected_types: list[VehiculeType] = field(default_factory=list)
    selected_nations: list[Nation] = field(default_factory=list)
    packs: list[Pack] = field(default_factory=list)
    last_packs: list[Pack] = field(default_factory=list)
    generated_url: str = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&search=wt_tanks%2Cwt_rank7%2Cwt_rank8%2Cwt_air%2Cwt_helicopters&tag=1"
    last_url: str = "https://store.gaijin.net/catalog.php?category=WarThunderPacks&search=wt_tanks%2Cwt_rank7%2Cwt_rank8%2Cwt_air%2Cwt_helicopters&tag=1"


def escape_md_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{c}" if c in escape_chars else c for c in text)


def format_pack(pack):
    name = escape_md_v2(pack.name)
    link = escape_md_v2(pack.link)
    price = escape_md_v2(pack.price)
    return name, link, price


def parse_query(query: CallbackQuery | None):
    if query is None:
        return None
    raw = query.data.split(" ")[-1]  # type:ignore

    for enum_cls in (Tier, VehiculeType, Nation):
        try:
            return enum_cls(raw)
        except ValueError:
            pass

    raise ValueError(f"Valeur inconnue : {raw}")


def add_or_remove(
    data: Tier | VehiculeType | Nation,
    list: list[Tier] | list[VehiculeType] | list[Nation],
):
    if data in list:
        list.remove(data)  # type: ignore
    else:
        list.append(data)  # type: ignore
