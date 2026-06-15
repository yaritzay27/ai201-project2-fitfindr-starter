# FitFindr - planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation - the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

FitFindr will use the three required tools below. Each tool can be tested on its own before it is connected to the planning loop.

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset for items that match the user's requested item description, optional size, and optional maximum price. It uses the load_listings() helper from utils/data_loader.py to load the data, filters by price and size first, then scores remaining listings by keyword overlap with the requested description.

**Input parameters:**
- description (str): The item the user wants, such as "vintage graphic tee" or "black platform shoes". This should be compared against searchable listing fields including title, description, category, style_tags, colors, brand, and platform.
- size (str | None): The user's requested size, such as "M", "S/M", "W30", or "US 8". If None, no size filter is applied. If provided, matching should be case-insensitive and allow partial matches so "M" can match listing sizes like "M/L" or "S/M".
- max_price (float | None): The user's maximum budget in dollars. If None, no price ceiling is applied. If provided, listings with price <= max_price are allowed.

**What it returns:**
A list of matching listing dictionaries, sorted with the strongest matches first. Each dictionary is one original listing from data/listings.json and contains:
- id (str): Unique listing id, such as "lst_033".
- title (str): Listing title.
- description (str): Seller-style item description.
- category (str): One of tops, bottoms, outerwear, shoes, or accessories.
- style_tags (list[str]): Style keywords such as ["vintage", "grunge", "graphic tee"].
- size (str): Listing size text.
- condition (str): excellent, good, or fair.
- price (float): Listing price in dollars.
- colors (list[str]): Color names.
- brand (str | None): Brand name or None.
- platform (str): Marketplace name, such as depop, thredUp, or poshmark.

The returned list can contain multiple results. For the agent workflow, the planning loop will use results[0] as the selected item.

**What happens if it fails or returns nothing:**
The tool returns an empty list instead of raising an exception when no listing matches. The agent sets session["error"] to a helpful message, such as "I couldn't find a vintage graphic tee under $30. Try raising your budget, removing the size filter, or using a broader phrase like 'graphic tee'.", then returns the session early without calling suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Suggests one or two complete outfits using the selected thrift listing and the user's wardrobe. If the wardrobe has items, the suggestion should name specific wardrobe pieces; if the wardrobe is empty, it should still give general styling advice instead of failing.

**Input parameters:**
- new_item (dict): A listing dictionary selected from search_listings, with fields such as title, category, style_tags, size, condition, price, colors, brand, and platform.
- wardrobe (dict): A wardrobe dictionary with an items key. wardrobe["items"] is a list of wardrobe item dictionaries. Each wardrobe item has:
  - id (str): Unique wardrobe item id.
  - name (str): User-friendly item name.
  - category (str): One of tops, bottoms, outerwear, shoes, or accessories.
  - colors (list[str]): Colors in the item.
  - style_tags (list[str]): Style descriptors.
  - notes (str | None): Optional fit or styling notes.

**What it returns:**
A non-empty string containing outfit advice. With a filled wardrobe, the string should include:
- The selected thrift item.
- At least one named wardrobe piece from a complementary category.
- A cohesive style explanation, such as 90s grunge, minimal streetwear, or cottagecore layering.
- Practical styling details, such as tuck, cuff, layer, shoe, or accessory suggestions.

Example return:
"Pair the Vintage Band Tee with your baggy straight-leg dark wash jeans, black combat boots, and black crossbody bag for a 90s grunge look. Roll the tee sleeves once and half-tuck the front so the oversized shape still feels intentional."

With an empty wardrobe, the string should not mention nonexistent closet items. It should instead recommend categories the user could pair with the item, such as wide-leg jeans, chunky sneakers, boots, or a denim jacket.

**What happens if it fails or returns nothing:**
If new_item is missing or does not contain enough listing information, the agent should set session["error"] to "I found a listing, but I don't have enough item details to style it yet." and return early. If the wardrobe is empty, that is not a fatal error: the tool should return general styling advice and the agent should continue to create_fit_card.

---

### Tool 3: create_fit_card

**What it does:**
Turns the outfit suggestion and thrift listing into a short, shareable caption that sounds like an outfit post rather than a product description. It should mention the item naturally and vary based on the item and outfit inputs.

**Input parameters:**
- outfit (str): The outfit suggestion returned by suggest_outfit. It should describe how the new item is styled.
- new_item (dict): The selected listing dictionary from search_listings, including title, price, platform, condition, colors, and style_tags.

**What it returns:**
A string containing a 1-3 sentence caption. The caption should:
- Mention the thrifted item title or a natural shortened version of it.
- Mention the price and platform when available.
- Capture the styling vibe from the outfit.
- Sound casual and social, like an Instagram/TikTok outfit caption.

Example return:
"Thrifted this faded band tee on Depop for $19 and it was basically made for baggy denim. Wearing it with dark wide-leg jeans, combat boots, and a tiny black bag for full 90s weekend energy."

**What happens if it fails or returns nothing:**
If outfit is empty, whitespace, or None, the tool returns a clear error string instead of crashing: "I need an outfit suggestion before I can write a fit card." The agent treats that as a failed fit-card step, stores it in session["error"], and returns the session with fit_card left as None.

---

### Additional Tools (if any)

### Stretch Tool: compare_price

**What it does:**
Compares the selected listing price against similar listings in the dataset.

**Input parameters:**
- new_item (dict): The selected listing dictionary from search_listings.

**What it returns:**
A dictionary with assessment, reasoning, item_price, average_comparable_price, comparable_count, and comparable_titles. Similar listings are chosen by same category and shared style tags, with same-category listings as a fallback.

**What happens if it fails or returns nothing:**
If the item is missing price details or there are no comparable listings, it returns assessment="unknown" with a reasoning message instead of crashing.

### Stretch Features

- Price comparison: after selected_item is chosen, the agent calls compare_price(selected_item) and stores the result in session["price_assessment"].
- Style profile memory: the agent stores style keywords from previous queries in a module-level style profile while the app is running. Later queries can use those remembered preferences without the user re-entering them.
- Retry logic with fallback: if the first search returns no results, the agent retries by removing the size filter, then by removing both size and max_price if needed. The adjustment is stored in session["retry_info"].

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent uses one session dictionary for a single user request and advances through the workflow only when the previous step produced usable output.

1. Initialize session = _new_session(query, wardrobe).
2. Parse the query into:
   - description: the item phrase to search for. For the first implementation, this can be a cleaned version of the query with budget and size phrases removed.
   - size: a size string if the query contains phrases like size M, size US 8, W30, or medium; otherwise None.
   - max_price: a float if the query contains phrases like under $30, below 30, or max $30; otherwise None.
   Store these values in session["parsed"].
3. Call search_listings(description, size, max_price) and store the returned list in session["search_results"].
4. If session["search_results"] is empty:
   - Retry once with loosened constraints: remove the size filter first, then remove both size and max_price if needed.
   - Store the adjustment in session["retry_info"].
   - If retry still returns no results, set session["error"] to a specific message that includes the main search phrase and any budget/size constraints.
   - Return the session immediately.
   - Do not call suggest_outfit with empty input.
5. If results exist:
   - Set session["selected_item"] = session["search_results"][0].
   - Call compare_price(selected_item) and store it in session["price_assessment"].
   - Continue to the outfit step.
6. Validate that session["selected_item"] has at least title, category, price, and platform.
   - If not, set session["error"] = "I found a listing, but it is missing details I need before I can style it." and return early.
7. Call suggest_outfit(session["selected_item"], session["wardrobe"]) and store the returned string in session["outfit_suggestion"].
8. If session["outfit_suggestion"] is empty or whitespace:
   - Set session["error"] = "I found an item, but I couldn't create an outfit suggestion for it."
   - Return the session immediately.
9. Call create_fit_card(session["outfit_suggestion"], session["selected_item"]) and store the returned string in session["fit_card"].
10. If session["fit_card"] is empty or begins with the known fit-card error message, set session["error"] to that message and set session["fit_card"] = None.
11. Return the session. On success, session["error"] is None and the user-facing response can summarize selected_item, outfit_suggestion, and fit_card.

---

## State Management

**How does information from one tool get passed to the next?**

State is stored in a single session dictionary created by _new_session(query, wardrobe). The session is the source of truth for the current interaction and contains:

- query (str): Original user request.
- parsed (dict): Parsed search parameters, with keys description, size, and max_price.
- search_results (list[dict]): Full list returned by search_listings.
- selected_item (dict | None): The top search result, passed into suggest_outfit and create_fit_card.
- price_assessment (dict | None): Price comparison for selected_item.
- wardrobe (dict): The user's wardrobe input, usually from get_example_wardrobe() or get_empty_wardrobe().
- style_profile (dict): Remembered style preferences from previous queries during the same app run.
- retry_info (dict | None): The loosened filters used if fallback search was needed.
- outfit_suggestion (str | None): Text returned by suggest_outfit.
- fit_card (str | None): Caption returned by create_fit_card.
- error (str | None): A user-facing explanation when the workflow stops early.

The agent does not ask the user to re-enter data between steps. search_listings returns listing dictionaries, the loop stores the top one in selected_item, and that same dictionary flows into the outfit and fit-card tools. If any step fails, error is set and the session returns early with later fields still None.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Retry with loosened filters first and store the adjustment in session["retry_info"]. If retry still finds nothing, set session["error"] to a message like "I couldn't find a vintage graphic tee under $30. Try raising your budget, removing the size filter, or searching for a broader phrase like 'graphic tee'." Return the session and do not call later tools. |
| suggest_outfit | Wardrobe is empty | Continue instead of failing. The tool returns general styling advice for the selected item, naming useful categories or silhouettes instead of specific wardrobe pieces, then the agent still calls create_fit_card. |
| suggest_outfit | Selected listing is missing required item details | Set session["error"] to "I found a listing, but I don't have enough item details to style it yet." Return early before fit-card generation. |
| create_fit_card | Outfit input is missing or incomplete | Store "I need an outfit suggestion before I can write a fit card." in session["error"], leave session["fit_card"] = None, and return the session. |

---

## Architecture

```text
User query
    |
    v
Planning Loop: run_agent(query, wardrobe) ----------------------------.
    |                                                                 |
    | parse query                                                     |
    v                                                                 |
Session: parsed = {description, size, max_price}                      |
    |                                                                 |
    |--> search_listings(description, size, max_price)                |
    |       | results=[]                                              |
    |       |--> [ERROR] "No listings found..." -> return session     |
    |       |                                                         |
    |       | results=[item, ...]                                     |
    |       v                                                         |
    |   Session: search_results = results                             |
    |       |                                                         |
    |   Session: selected_item = results[0]                           |
    |       | missing required item fields                            |
    |       |--> [ERROR] "Missing item details..." -> return session  |
    |       |                                                         |
    |--> suggest_outfit(selected_item, wardrobe)                      |
    |       | outfit=""                                               |
    |       |--> [ERROR] "Could not create outfit..." -> return       |
    |       |                                                         |
    |       v                                                         |
    |   Session: outfit_suggestion = "..."                            |
    |       |                                                         |
    |--> create_fit_card(outfit_suggestion, selected_item)            |
    |       | fit_card missing/error                                  |
    |       |--> [ERROR] "Need outfit suggestion..." -> return        |
    |       |                                                         |
    |       v                                                         |
    |   Session: fit_card = "..."                                     |
    |       |                                                         |
    v                                                                 |
Return successful session <-------------------------------------------'
```

---

## AI Tool Plan

**Milestone 3 - Individual tool implementations:**

I will use ChatGPT/Codex to implement the three tool functions in tools.py. For each tool, I will give the AI the matching Tool section from planning.md, the relevant helper details from utils/data_loader.py, and the expected function signature from tools.py.

- For search_listings, I will provide the Tool 1 spec and ask for an implementation that uses load_listings(), filters by size and max_price, scores description matches against the listing fields, and returns sorted listing dictionaries. I will verify it with at least three direct calls: a happy path like "vintage graphic tee" under 30, a size/price-filtered query, and a no-results query.
- For suggest_outfit, I will provide the Tool 2 spec plus the wardrobe schema. I will ask for a function that handles both get_example_wardrobe() and get_empty_wardrobe(). I will verify that the example wardrobe path names real wardrobe items and the empty wardrobe path gives general styling advice without crashing.
- For create_fit_card, I will provide the Tool 3 spec and ask for a caption generator that checks missing outfit input before using the LLM. I will verify it with a real selected item and outfit string, then with an empty outfit string to confirm it returns the expected error message.

Before trusting generated code, I will read it to confirm it matches the planned inputs, return types, and failure modes. Then I will run the tools independently from WSL with python3 before connecting them to the agent.

**Milestone 4 - Planning loop and state management:**

I will use ChatGPT/Codex to implement run_agent() in agent.py. I will give it the Planning Loop section, State Management section, Error Handling table, and the Architecture diagram from this file. I expect it to produce a loop that creates a session, parses the query, calls tools conditionally, stores each result in the session, and returns early on error paths.

I will verify the planning loop with three runs:
- Happy path: "I'm looking for a vintage graphic tee under $30" with get_example_wardrobe(), expecting selected_item, outfit_suggestion, and fit_card to be filled and error to be None.
- Empty wardrobe path: the same query with get_empty_wardrobe(), expecting a general outfit suggestion and a fit card, not a crash.
- No-results path: "designer ballgown size XXS under $5" with get_example_wardrobe(), expecting error to be set and outfit_suggestion and fit_card to stay None.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish - tool call by tool call. Use a specific example query.

FitFindr should turn a natural-language thrift request into a tool-guided shopping and styling flow: first it searches the listings dataset using the item description, size, and budget, then it uses the selected listing plus the user's wardrobe to suggest a complete outfit, and finally it turns that outfit into a short shareable fit card. Each tool is triggered only when the previous step produced usable data; if search returns no matches, the agent explains what the user can try differently and stops instead of calling the outfit or fit-card tools with empty input.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Parse the query**
The planning loop creates a new session and extracts:
- description = "vintage graphic tee"
- size = None
- max_price = 30.0

The loop stores this as session["parsed"] = {"description": "vintage graphic tee", "size": None, "max_price": 30.0}.

**Step 2: Call search_listings**
The agent calls search_listings(description="vintage graphic tee", size=None, max_price=30.0).

The tool filters out listings over $30, scores remaining listings against "vintage graphic tee", and returns a sorted list. Likely results include:
- lst_033: Vintage Band Tee - Faded Grey, tops, size L, fair condition, $19, Depop, tags ["vintage", "grunge", "band tee", "graphic tee", "streetwear"].
- lst_006: Graphic Tee - 2003 Tour Bootleg Style, tops, size L, good condition, $24, Depop, tags ["graphic tee", "vintage", "grunge", "streetwear", "band tee"].
- lst_002: Y2K Baby Tee - Butterfly Print, tops, size S/M, excellent condition, $18, Depop, tags including ["y2k", "vintage", "graphic tee", "cottagecore"].

The loop stores the returned list in session["search_results"].

**Step 3: Select the best item**
Because results are not empty, the agent sets session["selected_item"] = session["search_results"][0]. In this walkthrough, assume the selected item is lst_033, Vintage Band Tee - Faded Grey.

If search had returned an empty list, the agent would set session["error"] to a no-results message and return immediately.

**Step 4: Call suggest_outfit**
The agent calls suggest_outfit(new_item=session["selected_item"], wardrobe=get_example_wardrobe()).

The tool receives the selected band tee plus wardrobe items such as:
- Baggy straight-leg jeans, dark wash
- Chunky white sneakers
- Black combat boots
- Vintage black denim jacket
- Black crossbody bag

It returns an outfit suggestion like:
"Pair the faded grey band tee with your baggy straight-leg dark wash jeans, black combat boots, and black crossbody bag for a 90s grunge look. Add the vintage black denim jacket if you want more structure, and half-tuck the tee so the oversized pieces still have shape."

The loop stores this string in session["outfit_suggestion"].

**Step 5: Call create_fit_card**
The agent calls create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"]).

The tool returns a caption like:
"Thrifted this faded band tee on Depop for $19 and it was made for baggy denim. Styling it with dark straight-leg jeans, combat boots, and a black crossbody for that easy 90s grunge uniform."

The loop stores this in session["fit_card"].

**Final output to user:**
The user sees:
- Found item: Vintage Band Tee - Faded Grey, $19, Depop, fair condition.
- Outfit idea: Pair it with baggy dark-wash jeans, black combat boots, the vintage black denim jacket, and the black crossbody bag.
- Fit card: "Thrifted this faded band tee on Depop for $19 and it was made for baggy denim. Styling it with dark straight-leg jeans, combat boots, and a black crossbody for that easy 90s grunge uniform."

If search_listings returns no matches, the user instead sees a helpful message such as: "I couldn't find a vintage graphic tee under $30. Try raising your budget, removing the size filter, or searching for a broader phrase like 'graphic tee'."
