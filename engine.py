import re

from adapters.local_db_adapter import (
    search_local,
)


EMAIL_RE = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)

DOMAIN_RE = re.compile(
    r"^(?:https?://)?"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_RE = re.compile(
    r"^\+?[0-9 ()-]{7,}$"
)


def detect_query_type(
    query: str,
) -> str:
    query = query.strip()

    if EMAIL_RE.fullmatch(query):
        return "email"

    if DOMAIN_RE.fullmatch(query):
        return "domain"

    if PHONE_RE.fullmatch(query):
        return "phone"

    if " " in query:
        return "name"

    return "username_or_text"


def search_local_sources(
    query: str,
):
    return search_local(
        query,
        limit=50,
    )


async def search(
    query: str,
):
    query_type = detect_query_type(
        query
    )

    local_results = search_local_sources(
        query
    )

    return {
        "query": query,
        "type": query_type,
        "local_results": local_results,
        "sources": [
            {
                "name": "Локальные публичные данные",
                "type": "local",
            }
        ],
        "notice": (
            "Результаты ограничены публичными "
            "и законно используемыми источниками."
        ),
    }
