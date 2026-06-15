import agent
from agent import run_agent
from utils.data_loader import get_example_wardrobe


def test_run_agent_happy_path_passes_state(monkeypatch):
    listing = {
        "id": "lst_test",
        "title": "Test Graphic Tee",
        "description": "A faded graphic tee.",
        "category": "tops",
        "style_tags": ["vintage", "graphic tee"],
        "size": "M",
        "condition": "good",
        "price": 22.0,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }

    def fake_search(description, size=None, max_price=None):
        assert description == "vintage graphic tee"
        assert size is None
        assert max_price == 30.0
        return [listing]

    def fake_suggest(new_item, wardrobe):
        assert new_item is listing
        assert wardrobe == get_example_wardrobe()
        return "Wear it with baggy jeans and combat boots."

    def fake_fit_card(outfit, new_item):
        assert outfit == "Wear it with baggy jeans and combat boots."
        assert new_item is listing
        return "Thrifted this tee on Depop for $22."

    monkeypatch.setattr("agent.search_listings", fake_search)
    monkeypatch.setattr("agent.suggest_outfit", fake_suggest)
    monkeypatch.setattr("agent.create_fit_card", fake_fit_card)

    session = run_agent(
        "I'm looking for a vintage graphic tee under $30.",
        get_example_wardrobe(),
    )

    assert session["error"] is None
    assert session["selected_item"] is listing
    assert session["outfit_suggestion"] == "Wear it with baggy jeans and combat boots."
    assert session["fit_card"] == "Thrifted this tee on Depop for $22."


def test_run_agent_no_results_returns_early(monkeypatch):
    called = {"suggest": False, "fit_card": False}

    def fake_search(description, size=None, max_price=None):
        return []

    def fake_suggest(new_item, wardrobe):
        called["suggest"] = True
        return "Should not be called"

    def fake_fit_card(outfit, new_item):
        called["fit_card"] = True
        return "Should not be called"

    monkeypatch.setattr("agent.search_listings", fake_search)
    monkeypatch.setattr("agent.suggest_outfit", fake_suggest)
    monkeypatch.setattr("agent.create_fit_card", fake_fit_card)

    session = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert session["error"] is not None
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    assert called == {"suggest": False, "fit_card": False}


def test_run_agent_retries_with_loosened_filters(monkeypatch):
    listing = {
        "id": "lst_retry",
        "title": "Retry Jacket",
        "description": "A 90s jacket.",
        "category": "outerwear",
        "style_tags": ["90s"],
        "size": "M",
        "condition": "good",
        "price": 45.0,
        "colors": ["navy"],
        "brand": None,
        "platform": "depop",
    }
    calls = []

    def fake_search(description, size=None, max_price=None):
        calls.append((description, size, max_price))
        if size is None and max_price is None:
            return [listing]
        return []

    monkeypatch.setattr("agent.search_listings", fake_search)
    monkeypatch.setattr("agent.compare_price", lambda item: {"assessment": "fair price"})
    monkeypatch.setattr("agent.suggest_outfit", lambda item, wardrobe: "Wear it with jeans.")
    monkeypatch.setattr("agent.create_fit_card", lambda outfit, item: "Great jacket fit.")

    session = run_agent("90s jacket size XS under $10", get_example_wardrobe())

    assert session["error"] is None
    assert session["selected_item"] is listing
    assert session["retry_info"]["adjustment"] == "removed size and price filters"
    assert calls[-1] == ("90s jacket", None, None)


def test_run_agent_style_profile_memory(monkeypatch):
    agent.STYLE_PROFILE["preferences"] = []
    listing = {
        "id": "lst_style",
        "title": "Style Tee",
        "description": "A tee.",
        "category": "tops",
        "style_tags": ["vintage"],
        "size": "M",
        "condition": "good",
        "price": 20.0,
        "colors": ["black"],
        "brand": None,
        "platform": "depop",
    }
    seen_profiles = []

    monkeypatch.setattr("agent.search_listings", lambda *args, **kwargs: [listing])
    monkeypatch.setattr("agent.compare_price", lambda item: {"assessment": "fair price"})

    def fake_suggest(item, wardrobe):
        seen_profiles.append(wardrobe.get("style_profile", {}))
        return "Styled with remembered preferences."

    monkeypatch.setattr("agent.suggest_outfit", fake_suggest)
    monkeypatch.setattr("agent.create_fit_card", lambda outfit, item: "Remembered style caption.")

    first = run_agent("vintage tee under $30. I mostly wear baggy jeans and chunky sneakers.", get_example_wardrobe())
    second = run_agent("black tee under $30", get_example_wardrobe())

    assert first["style_profile"]["remembered_now"]
    assert second["style_profile"]["used_memory"] is True
    assert "baggy" in seen_profiles[-1]["preferences"]
    assert "chunky" in seen_profiles[-1]["preferences"]
