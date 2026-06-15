from tools import compare_price, create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all("title" in item for item in results)


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)

    assert all(item["price"] <= 10 for item in results)


def test_suggest_outfit_with_example_wardrobe(monkeypatch):
    def fake_llm(prompt, temperature=0.7):
        assert "Baggy straight-leg jeans" in prompt
        return "Pair it with your baggy straight-leg jeans and chunky white sneakers."

    monkeypatch.setattr("tools._call_llm", fake_llm)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    suggestion = suggest_outfit(new_item, get_example_wardrobe())

    assert "baggy straight-leg jeans" in suggestion
    assert suggestion.strip()


def test_suggest_outfit_empty_wardrobe(monkeypatch):
    def fake_llm(prompt, temperature=0.7):
        assert "has not entered wardrobe items" in prompt
        return "Try wide-leg jeans, chunky sneakers, and a cropped jacket."

    monkeypatch.setattr("tools._call_llm", fake_llm)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    suggestion = suggest_outfit(new_item, get_empty_wardrobe())

    assert "wide-leg jeans" in suggestion
    assert suggestion.strip()


def test_suggest_outfit_missing_item():
    suggestion = suggest_outfit({}, get_example_wardrobe())

    assert "enough item details" in suggestion


def test_create_fit_card_returns_caption(monkeypatch):
    def fake_llm(prompt, temperature=0.95):
        assert temperature == 0.95
        assert "Outfit suggestion" in prompt
        return "Thrifted this tee on Depop and styled it with baggy denim."

    monkeypatch.setattr("tools._call_llm", fake_llm)
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    fit_card = create_fit_card("Style it with baggy denim and boots.", new_item)

    assert "Thrifted" in fit_card


def test_create_fit_card_empty_outfit():
    fit_card = create_fit_card("", {"title": "Vintage Band Tee"})

    assert fit_card == "I need an outfit suggestion before I can write a fit card."


def test_compare_price_returns_reasoning():
    new_item = search_listings("vintage graphic tee", max_price=50)[0]

    assessment = compare_price(new_item)

    assert assessment["assessment"] in {"good deal", "fair price", "pricey", "unknown"}
    assert assessment["item_price"] == new_item["price"]
    assert assessment["comparable_count"] > 0
    assert "similar" in assessment["reasoning"]
