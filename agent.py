"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import compare_price, search_listings, suggest_outfit, create_fit_card


STYLE_PROFILE = {
    "preferences": [],
}

STYLE_KEYWORDS = [
    "baggy",
    "chunky",
    "classic",
    "cottagecore",
    "dark academia",
    "earth tones",
    "grunge",
    "minimal",
    "oversized",
    "preppy",
    "streetwear",
    "vintage",
    "wide-leg",
    "y2k",
]


def reset_style_profile() -> str:
    """Clear remembered style preferences for the running app session."""
    STYLE_PROFILE["preferences"] = []
    return "Style memory reset."


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "price_assessment": None,    # price comparison for selected_item
        "wardrobe": wardrobe,        # user's wardrobe dict
        "style_profile": {},         # remembered style preferences for this app session
        "retry_info": None,          # explains fallback search if one was used
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract a searchable description, optional size, and optional max price.

    This parser is intentionally simple so the planning loop is easy to debug.
    It handles the common project examples like "under $30", "size M",
    "US 8", and "W30".
    """
    original = query.strip()
    search_part = original.split(".")[0]

    max_price = None
    price_match = re.search(
        r"(?:under|below|less than|max|maximum|up to)\s*\$?\s*(\d+(?:\.\d+)?)",
        search_part,
        flags=re.IGNORECASE,
    )
    if price_match:
        max_price = float(price_match.group(1))

    size = None
    size_match = re.search(
        r"\b(?:in\s+)?size\s+([a-zA-Z0-9./-]+)",
        search_part,
        flags=re.IGNORECASE,
    )
    if size_match:
        size = size_match.group(1).upper()
    else:
        us_size_match = re.search(r"\bUS\s*\d+(?:\.\d+)?\b", search_part, re.IGNORECASE)
        waist_match = re.search(r"\bW\d+\b", search_part, re.IGNORECASE)
        if us_size_match:
            size = us_size_match.group(0).upper()
        elif waist_match:
            size = waist_match.group(0).upper()

    description = search_part
    description = re.sub(
        r"(?:under|below|less than|max|maximum|up to)\s*\$?\s*\d+(?:\.\d+)?",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"\b(?:in\s+)?size\s+[a-zA-Z0-9./-]+",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\bUS\s*\d+(?:\.\d+)?\b", " ", description, flags=re.IGNORECASE)
    description = re.sub(r"\bW\d+\b", " ", description, flags=re.IGNORECASE)
    description = re.sub(
        r"\b(i am|i'm|im|looking for|look for|find me|show me|i want|want|a|an|the|please)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"[^a-zA-Z0-9\s-]", " ", description)
    description = re.sub(r"\s+", " ", description).strip()

    if not description:
        description = original

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def _format_search_error(parsed: dict) -> str:
    description = parsed.get("description") or "that item"
    constraints = []
    if parsed.get("size"):
        constraints.append(f"size {parsed['size']}")
    if parsed.get("max_price") is not None:
        constraints.append(f"under ${parsed['max_price']:.0f}")

    constraint_text = ""
    if constraints:
        constraint_text = " " + " ".join(constraints)

    return (
        f"I couldn't find {description}{constraint_text}. "
        "Try raising your budget, removing the size filter, or searching with a broader phrase."
    )


def _remember_style_preferences(query: str) -> list[str]:
    query_lower = query.lower()
    found = []
    for keyword in STYLE_KEYWORDS:
        if keyword in query_lower and keyword not in STYLE_PROFILE["preferences"]:
            STYLE_PROFILE["preferences"].append(keyword)
            found.append(keyword)
    return found


def _profile_for_session(query: str) -> dict:
    remembered_now = _remember_style_preferences(query)
    return {
        "preferences": list(STYLE_PROFILE["preferences"]),
        "remembered_now": remembered_now,
        "used_memory": bool(STYLE_PROFILE["preferences"] and not remembered_now),
    }


def _wardrobe_with_style_profile(wardrobe: dict, style_profile: dict) -> dict:
    if not style_profile.get("preferences"):
        return wardrobe

    enriched = dict(wardrobe or {})
    enriched["style_profile"] = style_profile
    return enriched


def _search_with_retry(parsed: dict) -> tuple[list[dict], dict | None]:
    original = {
        "description": parsed["description"],
        "size": parsed["size"],
        "max_price": parsed["max_price"],
    }

    results = search_listings(
        original["description"],
        size=original["size"],
        max_price=original["max_price"],
    )
    if results:
        return results, None

    attempts = []

    if original["size"] is not None:
        attempts.append({
            "description": original["description"],
            "size": None,
            "max_price": original["max_price"],
            "adjustment": f"removed size filter {original['size']}",
        })

    if original["max_price"] is not None:
        attempts.append({
            "description": original["description"],
            "size": None,
            "max_price": None,
            "adjustment": "removed size and price filters",
        })

    for attempt in attempts:
        retry_results = search_listings(
            attempt["description"],
            size=attempt["size"],
            max_price=attempt["max_price"],
        )
        if retry_results:
            retry_info = {
                "original": original,
                "adjustment": attempt["adjustment"],
                "retried_with": {
                    "description": attempt["description"],
                    "size": attempt["size"],
                    "max_price": attempt["max_price"],
                },
                "message": f"No exact match found, so I retried and {attempt['adjustment']}.",
            }
            return retry_results, retry_info

    return [], {
        "original": original,
        "adjustment": "removed size and price filters",
        "retried_with": {
            "description": original["description"],
            "size": None,
            "max_price": None,
        },
        "message": "I retried with loosened filters but still could not find a match.",
    }


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    parsed = _parse_query(query)
    session["parsed"] = parsed
    session["style_profile"] = _profile_for_session(query)

    results, retry_info = _search_with_retry(parsed)
    session["search_results"] = results
    session["retry_info"] = retry_info

    if not results:
        session["error"] = _format_search_error(parsed)
        return session

    session["selected_item"] = results[0]
    session["price_assessment"] = compare_price(session["selected_item"])
    required_fields = ("title", "category", "price", "platform")
    if any(field not in session["selected_item"] for field in required_fields):
        session["error"] = "I found a listing, but it is missing details I need before I can style it."
        return session

    wardrobe_for_outfit = _wardrobe_with_style_profile(
        session["wardrobe"],
        session["style_profile"],
    )
    outfit = suggest_outfit(session["selected_item"], wardrobe_for_outfit)
    session["outfit_suggestion"] = outfit
    if not outfit or not outfit.strip():
        session["error"] = "I found an item, but I couldn't create an outfit suggestion for it."
        return session

    fit_card = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    if not fit_card or fit_card.startswith("I need an outfit suggestion"):
        session["error"] = fit_card or "I need an outfit suggestion before I can write a fit card."
        session["fit_card"] = None
        return session

    session["fit_card"] = fit_card
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
