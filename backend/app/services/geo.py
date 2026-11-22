"""Radius search without a geocoder: a small table of Dutch cities (lat, lon), straight-line distance. Good enough for "within 30 km of Utrecht"."""
import math

CITIES = {
    "amsterdam": (52.370, 4.895), "rotterdam": (51.924, 4.478), "the hague": (52.078, 4.288), "utrecht": (52.091, 5.122), "eindhoven": (51.441, 5.478), "groningen": (53.219, 6.567),
    "tilburg": (51.556, 5.091), "almere": (52.351, 5.265), "breda": (51.589, 4.776), "nijmegen": (51.842, 5.853), "apeldoorn": (52.211, 5.970), "haarlem": (52.381, 4.637),
    "arnhem": (51.985, 5.899), "enschede": (52.221, 6.894), "amersfoort": (52.156, 5.387), "zaandam": (52.439, 4.829), "den bosch": (51.699, 5.304), "'s-hertogenbosch": (51.699, 5.304),
    "haarlemmermeer": (52.303, 4.690), "hoofddorp": (52.303, 4.690), "zwolle": (52.516, 6.083), "leiden": (52.160, 4.497), "maastricht": (50.851, 5.690), "dordrecht": (51.813, 4.690),
    "delft": (52.011, 4.358), "alkmaar": (52.632, 4.749), "heerlen": (50.888, 5.979), "venlo": (51.370, 6.169), "deventer": (52.255, 6.160), "leeuwarden": (53.201, 5.799),
    "hilversum": (52.223, 5.176), "amstelveen": (52.304, 4.862), "veldhoven": (51.418, 5.403), "helmond": (51.482, 5.661), "enschede ": (52.221, 6.894), "zoetermeer": (52.057, 4.494),
    "ede": (52.040, 5.665), "wageningen": (51.967, 5.664), "gouda": (52.012, 4.711), "roermond": (51.194, 5.987), "sittard": (51.000, 5.869), "nieuwegein": (52.030, 5.080),
    "capelle aan den ijssel": (51.930, 4.578), "schiphol": (52.310, 4.768), "den haag": (52.078, 4.288), "s-hertogenbosch": (51.699, 5.304),
}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    (la1, lo1), (la2, lo2) = a, b; p = math.pi / 180
    h = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def within(city: str, radius_km: float) -> list[str] | None:
    """Lower-case names of every known city within the radius (including the city itself); None if the city is not in the table."""
    c = CITIES.get(city.strip().lower())
    if not c: return None
    return sorted({n.strip() for n, xy in CITIES.items() if km(c, xy) <= radius_km} | {city.strip().lower()})
