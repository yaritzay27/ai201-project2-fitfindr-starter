# FitFindr

FitFindr is a multi-tool AI agent that helps a user search mock secondhand clothing listings, decide how to style a selected item with their wardrobe, and generate a short shareable outfit caption. The main point of the project is the planning loop: the agent does not call every tool automatically. It checks what happened at each step and only moves forward when the previous tool returned usable data.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_key_here
```

Run the tests:

```bash
python -m pytest tests
```

Run the app:

```bash
python app.py
```

Then open the local URL Gradio prints, usually `http://127.0.0.1:7860`.

## Tool Inventory

### search_listings(description, size, max_price)

Purpose: searches `data/listings.json` for thrift listings that match the user's request.

Inputs:

- description (str): search phrase, such as "vintage graphic tee"
- size (str or None): optional size filter, such as "M", "S/M", "W30", or "US 8"
- max_price (float or None): optional price ceiling

Output:

- A list of listing dictionaries sorted by relevance. Each result includes id, title, description, category, style_tags, size, condition, price, colors, brand, and platform.
- If nothing matches, it returns an empty list.

### suggest_outfit(new_item, wardrobe)

Purpose: uses the selected listing and the user's wardrobe to suggest a practical outfit.

Inputs:

- new_item (dict): one listing returned by `search_listings`
- wardrobe (dict): a wardrobe dictionary with an items list from `get_example_wardrobe()` or `get_empty_wardrobe()`

Output:

- A non-empty outfit suggestion string.
- If the wardrobe is empty, it still returns general styling advice instead of crashing.
- If the item is missing details, it returns a specific message explaining that there is not enough item information.

### create_fit_card(outfit, new_item)

Purpose: turns an outfit suggestion into a short social-caption-style fit card.

Inputs:

- outfit (str): the outfit suggestion from `suggest_outfit`
- new_item (dict): the selected listing from `search_listings`

Output:

- A 1-3 sentence caption that mentions the thrifted item, price/platform when available, and the outfit vibe.
- If the outfit string is empty, it returns: "I need an outfit suggestion before I can write a fit card."

### compare_price(new_item)

Purpose: compares the selected listing's price against similar listings in the dataset.

Inputs:

- new_item (dict): the selected listing from `search_listings`

Output:

- A dictionary with assessment, reasoning, item_price, average_comparable_price, comparable_count, and comparable_titles.
- The assessment is "good deal", "fair price", "pricey", or "unknown".

Comparisons are made by looking for listings in the same category that share at least one style tag with the selected item. If there are no tag-level matches, the tool falls back to other listings in the same category. It then compares the selected item's price to the average comparable price.

## Planning Loop

The planning loop lives in `agent.py` inside `run_agent(query, wardrobe)`.

The agent starts by creating a session dictionary. It parses the user query into description, size, and max_price, then calls `search_listings`.

After search, the first major branch happens:

- If search returns an empty list, the agent sets `session["error"]` with a helpful message and returns early.
- If search returns results, the agent stores the full list in `session["search_results"]` and stores the top result in `session["selected_item"]`.

If the first search returns no results, the agent retries automatically with loosened filters before giving up. First it removes the size filter if one was provided. If that still fails and a max price was provided, it removes both size and price filters. The session stores this in `session["retry_info"]` so the app can tell the user what was adjusted.

Only after a selected item exists does the agent call `compare_price` and `suggest_outfit`. The price assessment is stored in `session["price_assessment"]`, and the outfit suggestion is stored in `session["outfit_suggestion"]`.

Only after an outfit suggestion exists does the agent call `create_fit_card`. The final caption is stored in `session["fit_card"]`.

This means the agent's behavior changes based on tool output. For example, the impossible query "designer ballgown size XXS under $5" stops after search and never calls the styling or fit-card tools.

## State Management

The session dictionary is the shared state object for one full interaction. It stores:

- query: the original user request
- parsed: extracted description, size, and max_price
- search_results: all matching listings returned by search
- selected_item: the top listing selected from search_results
- price_assessment: the result from compare_price for the selected item
- wardrobe: the wardrobe passed into the agent
- style_profile: remembered style preferences for the current running app session
- retry_info: what filter was loosened if fallback search was used
- outfit_suggestion: text returned by suggest_outfit
- fit_card: caption returned by create_fit_card
- error: message set when the workflow stops early

The important state flow is:

```text
search_listings -> selected_item -> suggest_outfit -> outfit_suggestion -> create_fit_card -> fit_card
```

The user does not have to re-enter the selected item or outfit between steps. The agent passes the stored session values forward.

## Stretch Features

### Price comparison

After the agent selects the top listing, it calls `compare_price(selected_item)`. The tool compares that item to other listings from the same category and, when possible, the same style tags. The app displays whether the selected listing looks like a good deal, fair price, or pricey, along with the average price and example comparable listings.

Example: if the selected item is a top priced at $18 and similar tops average around $25, the tool can mark it as a good deal and explain that it is below the comparable average.

### Style profile memory

FitFindr stores a lightweight style profile in memory while the app is running. The profile is a list of style keywords found in previous user queries, such as baggy, chunky, grunge, streetwear, y2k, or minimal.

For example, if the first query says "I mostly wear baggy jeans and chunky sneakers," the agent stores baggy and chunky. In a later query like "black tee under $30," the user does not have to repeat those preferences. The agent passes the remembered profile into `suggest_outfit`, and the app shows the remembered style memory in the listing panel.

This memory is stored in a module-level dictionary in `agent.py`, so it lasts while the app process is running. It is not saved permanently after the app stops.

### Retry logic with fallback

If search returns no results, the agent retries automatically with loosened constraints. For example, a query like:

```text
90s jacket size XS under $10
```

may fail because the size and budget are too strict. The agent then retries by removing the size filter, and if needed removes both size and price filters. If the retry succeeds, the app explains what was adjusted. If it still fails, the agent returns a helpful no-results message.

## Error Handling

### No listings found

Direct tool test:

```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
```

Result:

```text
[]
```

Full agent test:

```bash
python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe; session = run_agent('designer ballgown size XXS under $5', get_example_wardrobe()); print(session['error']); print(session['fit_card'])"
```

Result: the agent prints a helpful message suggesting changes and `fit_card` stays `None`. This confirms the agent stops instead of calling later tools with empty input.

### Empty wardrobe

When `suggest_outfit` receives `get_empty_wardrobe()`, it asks the LLM for general styling advice. It does not pretend the user owns items, and it does not crash.

Example test:

```bash
python -c "from tools import search_listings, suggest_outfit; from utils.data_loader import get_empty_wardrobe; results = search_listings('vintage graphic tee', size=None, max_price=50); print(suggest_outfit(results[0], get_empty_wardrobe()))"
```

### Empty outfit input

When `create_fit_card` receives an empty outfit string, it returns a clear message:

```text
I need an outfit suggestion before I can write a fit card.
```

This avoids a Python exception and makes the failure understandable.

## Testing

The tests are in the `tests/` folder.

`tests/test_tools.py` checks each tool in isolation, including no search results, empty wardrobe behavior, missing item details, and empty outfit input. The LLM calls are mocked in these tests so they do not use API credits.

`tests/test_agent.py` checks the planning loop. One test verifies that the selected item from search is the same object passed into `suggest_outfit` and `create_fit_card`. Another test verifies that when search returns no results, the agent returns early and does not call the later tools.

Run all tests with:

```bash
python -m pytest tests
```

## Demo Guide

For the demo video, show one happy path and one failure path.

Happy path query:

```text
vintage graphic tee under $30
```

Narration points:

- The agent parses the query into search filters.
- `search_listings` returns matching listings.
- The top listing becomes `selected_item`.
- `suggest_outfit` uses that selected item and the wardrobe.
- `create_fit_card` uses the outfit suggestion and same selected item.

Failure path query:

```text
designer ballgown size XXS under $5
```

Narration points:

- Search returns no results.
- The agent sets an error message.
- The outfit and fit-card panels stay empty because the later tools are not called.

## Spec Reflection

Writing `planning.md` first made the implementation clearer because the tool inputs, outputs, and failure paths were already decided before coding. The most important design decision was making search the gatekeeper. If there is no selected item, the agent should stop instead of trying to style empty data.

The other useful decision was keeping session state explicit. Instead of passing loose variables around, the agent stores parsed input, search results, selected item, outfit suggestion, fit card, and errors in one dictionary. That makes it easier to debug and easier to explain in the demo.

One place the implementation diverged slightly from the original spec was query parsing. The spec described parsing the user's request into description, size, and max_price, but did not fully define every wording pattern a user might type. In the implementation, I used a simple regex-based parser in `agent.py` for common patterns like "under $30", "size M", "US 8", and "W30" instead of using the LLM to parse queries. I chose this because it is easier to test and keeps the planning loop predictable.

## AI Usage

**Instance 1**

- *What I gave the AI:* I gave Codex the Milestone 3 requirements, the Tool Inventory specs, and the existing stubs in `tools.py` for `search_listings`, `suggest_outfit`, and `create_fit_card`.
- *What it produced:* Codex produced the implementations in `tools.py`: dataset search with price/size filtering, Groq-based outfit suggestions using `llama-3.3-70b-versatile`, and Groq-based fit card generation.
- *What I changed or overrode:* I reviewed the code to make sure `search_listings` used `load_listings()` instead of re-reading the JSON file, that empty search results returned `[]`, that empty wardrobes produced general styling advice, and that empty outfit input returned a clear message instead of crashing.

**Instance 2**

- *What I gave the AI:* I gave Codex the Milestone 3 testing requirement and asked for pytest coverage for the required tool behavior and failure modes.
- *What it produced:* Codex produced `tests/test_tools.py`, including tests for search results, empty search results, price filtering, empty wardrobe behavior, missing item details, fit card generation, and empty outfit input.
- *What I changed or overrode:* I kept the LLM tests mocked with `monkeypatch` so the tests would not spend Groq API calls or fail because of network/API issues. I ran the tests in my virtual environment and confirmed they passed.

**Instance 3**

- *What I gave the AI:* I gave Codex the Milestone 4 requirements, the Planning Loop, State Management, and Architecture sections, plus the TODOs in `agent.py` and `app.py`.
- *What it produced:* Codex produced the `run_agent()` planning loop in `agent.py` and the `handle_query()` function in `app.py`, connecting the tools to the Gradio interface.
- *What I changed or overrode:* I checked that `run_agent()` branches when `search_listings` returns no results, stores `selected_item`, `outfit_suggestion`, and `fit_card` in the session dictionary, and does not call all three tools unconditionally. I also added agent tests to confirm the no-results branch returns early.
