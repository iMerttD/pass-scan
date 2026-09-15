"""
ICAO Doc 9303 / ISO 3166-1 alpha-3 issuing state & nationality code resolution.

Covers every ISO 3166-1 country (via the offline `pycountry` dataset) plus the
ICAO-specific codes that are NOT in ISO 3166 (Doc 9303 Part 3, Section 5):
German 'D', British national classes, UN codes, stateless/refugee codes and
international organisations.
"""
from typing import Dict, Optional

try:
    import pycountry  # offline ISO 3166 dataset, no network access
except ImportError:  # pragma: no cover - dependency is pinned in requirements.txt
    pycountry = None

# ICAO codes that do not exist in ISO 3166-1 alpha-3, plus historical codes
# still found on valid (unexpired) travel documents.
ICAO_SPECIAL_CODES: Dict[str, str] = {
    "D": "Germany",
    "D<<": "Germany",
    "GBD": "United Kingdom (British Overseas Territories Citizen)",
    "GBN": "United Kingdom (British National Overseas)",
    "GBO": "United Kingdom (British Overseas Citizen)",
    "GBP": "United Kingdom (British Protected Person)",
    "GBS": "United Kingdom (British Subject)",
    "RKS": "Republic of Kosovo",
    "EUE": "European Union",
    "UNO": "United Nations Organization",
    "UNA": "United Nations Specialized Agency",
    "UNK": "United Nations Interim Administration Mission in Kosovo",
    "XXA": "Stateless Person (1954 Convention)",
    "XXB": "Refugee (1951 Convention)",
    "XXC": "Refugee (non-Convention)",
    "XXX": "Unspecified Nationality",
    "XOM": "Sovereign Military Order of Malta",
    "XCC": "Caribbean Community",
    "XCO": "Common Market for Eastern and Southern Africa",
    "XEC": "Economic Community of West African States",
    "XPO": "International Criminal Police Organization (INTERPOL)",
    "XDC": "Southern African Development Community",
    "XAC": "African Union Commission",
    "XBA": "African Development Bank",
    "XIM": "African Export-Import Bank",
    "XBB": "African Reinsurance Corporation",
    "XBC": "African Regional Industrial Property Organization",
    "XBD": "African Union",
    "XAA": "Caribbean Development Bank",
    # Historical issuing states still present on documents in circulation
    "YUG": "Yugoslavia (historical)",
    "SCG": "Serbia and Montenegro (historical)",
    "ZAR": "Zaire (historical)",
    "ANT": "Netherlands Antilles (historical)",
    "NTZ": "Neutral Zone (historical)",
}

# 'XXD' is reserved/unassigned in current Doc 9303 editions; treat as unspecified.
ICAO_SPECIAL_CODES["XXD"] = "Unspecified Nationality"


def resolve_country_name(code: Optional[str]) -> Optional[str]:
    """
    Resolve an MRZ 3-letter issuing state / nationality code to a readable name.

    Returns the original code unchanged when it cannot be resolved, so the
    operator always sees exactly what the document contains.
    """
    if not code:
        return None

    normalized = code.strip().upper().replace("<", "")
    if not normalized:
        return None

    special = ICAO_SPECIAL_CODES.get(code.strip().upper()) or ICAO_SPECIAL_CODES.get(normalized)
    if special:
        return special

    if pycountry is not None and len(normalized) == 3:
        country = pycountry.countries.get(alpha_3=normalized)
        if country is not None:
            # `common_name` is the everyday name (e.g. "South Korea" vs the
            # official "Korea, Republic of"); prefer it when present.
            return getattr(country, "common_name", None) or country.name

    return normalized


def demo() -> None:
    assert resolve_country_name("TUR") == "Türkiye"
    assert resolve_country_name("D<<") == "Germany"
    assert resolve_country_name("D") == "Germany"
    assert resolve_country_name("GBR") == "United Kingdom"
    assert resolve_country_name("GBN").startswith("United Kingdom")
    assert resolve_country_name("KOR") == "South Korea"
    assert resolve_country_name("XXB").startswith("Refugee")
    assert resolve_country_name("RKS") == "Republic of Kosovo"
    assert resolve_country_name("ZZZ") == "ZZZ"  # unknown stays verbatim
    assert resolve_country_name("") is None
    assert resolve_country_name(None) is None
    print("countries.demo OK")


if __name__ == "__main__":
    demo()
