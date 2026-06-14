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
