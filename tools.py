"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _call_llm(prompt: str, temperature: float = 0.7) -> str:
    """Call Groq's Llama model and return the assistant text."""
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a concise secondhand fashion stylist. "
                    "Give specific, practical styling advice in a casual voice."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _normalize_words(text: str) -> list[str]:
    """Return searchable lowercase words from a short text string."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _listing_search_text(listing: dict) -> str:
    fields = [
        listing.get("title"),
        listing.get("description"),
        listing.get("category"),
        listing.get("size"),
        listing.get("condition"),
        listing.get("brand"),
        listing.get("platform"),
    ]
    fields.extend(listing.get("style_tags") or [])
    fields.extend(listing.get("colors") or [])
    return " ".join(str(field) for field in fields if field)


def _format_item(item: dict) -> str:
    return json.dumps(item, indent=2, ensure_ascii=True)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    if not description or not description.strip():
        return []

    query = description.lower().strip()
    query_words = set(_normalize_words(query))
    matches = []

    for listing in load_listings():
        if max_price is not None and listing.get("price", 0) > max_price:
            continue

        if size:
            requested_size = size.lower().strip()
            listing_size = str(listing.get("size", "")).lower()
            if requested_size not in listing_size and listing_size not in requested_size:
                continue

        search_text = _listing_search_text(listing).lower()
        search_words = set(_normalize_words(search_text))
        overlap = query_words & search_words
        score = len(overlap)

        if query in search_text:
            score += 3

        title = str(listing.get("title", "")).lower()
        tags = " ".join(listing.get("style_tags") or []).lower()
        for word in query_words:
            if word in title:
                score += 2
            if word in tags:
                score += 2

        if score > 0:
            matches.append((score, listing))

    matches.sort(key=lambda scored: (-scored[0], scored[1].get("price", 0)))
    return [listing for _, listing in matches]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not new_item or not isinstance(new_item, dict):
        return "I found a listing, but I don't have enough item details to style it yet."

    title = new_item.get("title")
    if not title:
        return "I found a listing, but I don't have enough item details to style it yet."

    wardrobe_items = (wardrobe or {}).get("items") or []

    if not wardrobe_items:
        prompt = f"""
Suggest 1 complete outfit idea for this thrifted item.

New item:
{_format_item(new_item)}

The user has not entered wardrobe items yet, so do not pretend they own specific pieces.
Recommend general categories, silhouettes, colors, shoes, and styling details that would pair well.
Keep it to 3-5 sentences.
"""
    else:
        wardrobe_text = "\n".join(
            f"- {item.get('name')} ({item.get('category')}; colors: {', '.join(item.get('colors') or [])}; "
            f"tags: {', '.join(item.get('style_tags') or [])}; notes: {item.get('notes') or 'none'})"
            for item in wardrobe_items
        )
        prompt = f"""
Suggest 1-2 complete outfits using this thrifted item and named pieces from the user's wardrobe.

New item:
{_format_item(new_item)}

User wardrobe:
{wardrobe_text}

Use specific wardrobe item names when possible. Include practical styling details like cuffing,
tucking, layering, shoes, or accessories. Keep the answer concise and useful.
"""

    try:
        return _call_llm(prompt, temperature=0.7)
    except Exception as exc:
        return f"I couldn't generate an outfit suggestion right now: {exc}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not str(outfit).strip():
        return "I need an outfit suggestion before I can write a fit card."

    if not new_item or not isinstance(new_item, dict):
        return "I need item details before I can write a fit card."

    prompt = f"""
Write a short shareable outfit caption for a thrifted find.

New item:
{_format_item(new_item)}

Outfit suggestion:
{outfit}

Requirements:
- 1-3 sentences.
- Casual and authentic, like an outfit post caption.
- Mention the item name, price, and platform naturally if available.
- Capture the outfit vibe with specific styling language.
- Do not sound like a store product description.
"""

    try:
        return _call_llm(prompt, temperature=0.95)
    except Exception as exc:
        return f"I couldn't create a fit card right now: {exc}"
