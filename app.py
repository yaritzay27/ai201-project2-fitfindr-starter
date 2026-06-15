"""
Gradio interface for FitFindr.

Run with:
    python app.py

Then open the local URL shown in the terminal.
"""

import gradio as gr

from agent import reset_style_profile, run_agent
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


APP_CSS = """
:root {
    --fit-purple: #6d3df2;
    --fit-purple-dark: #5629d6;
    --fit-border: #dedeea;
    --fit-muted: #6b7280;
    --fit-ink: #101528;
    --fit-card: #ffffff;
    --fit-bg: #fbfbfe;
}

.gradio-container {
    background:
        radial-gradient(circle at 63% 10%, rgba(109, 61, 242, 0.08), transparent 28%),
        linear-gradient(180deg, #ffffff 0%, var(--fit-bg) 100%);
    color: var(--fit-ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.fit-shell {
    max-width: 1180px;
    margin: 0 auto;
}

.fit-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 8px 0 14px;
}

.fit-brand {
    font-size: 23px;
    font-weight: 800;
    color: var(--fit-purple);
}

.fit-help {
    color: #111827;
    font-size: 13px;
    font-weight: 600;
}

.fit-hero {
    border: 1px solid var(--fit-border);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 22px 70px rgba(25, 28, 45, 0.06);
    padding: 26px 18px 18px;
}

.fit-hero h1 {
    text-align: center;
    font-size: 28px;
    line-height: 1.15;
    margin: 0 0 8px;
}

.fit-hero p {
    text-align: center;
    max-width: 590px;
    margin: 0 auto 20px;
    color: var(--fit-muted);
    font-size: 14px;
    line-height: 1.45;
}

.fit-search-card {
    border: 1px solid var(--fit-border);
    border-radius: 12px;
    background: var(--fit-card);
    padding: 14px;
    overflow: hidden !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

.fit-search-card * {
    box-sizing: border-box !important;
    max-width: 100% !important;
}

.fit-search-card label {
    color: var(--fit-purple) !important;
    font-weight: 700 !important;
    font-size: 12px !important;
}

#wardrobe-radio .wrap,
#wardrobe-radio .radio-group {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    align-items: flex-start !important;
    flex-wrap: nowrap !important;
    overflow: visible !important;
}

#wardrobe-radio label,
#wardrobe-radio .wrap label {
    border: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
    color: #111827 !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
}

#wardrobe-radio {
    overflow: visible !important;
}

@media (max-width: 720px) {
    .fit-hero {
        padding: 22px 14px 14px;
    }

    .fit-hero h1 {
        font-size: 25px;
    }

    .fit-search-card {
        overflow: hidden !important;
    }

    .fit-search-card .gradio-row {
        flex-direction: column !important;
        gap: 14px !important;
    }

    .fit-search-card .gradio-row > *,
    .fit-search-card .form,
    .fit-search-card .block {
        min-width: 0 !important;
        width: 100% !important;
    }

    #wardrobe-radio .wrap,
    #wardrobe-radio .radio-group {
        width: 100% !important;
        max-width: 100% !important;
        overflow: visible !important;
    }

    #wardrobe-radio label,
    #wardrobe-radio .wrap label {
        white-space: normal !important;
        max-width: 100% !important;
    }

    .fit-reset-btn {
        width: 100% !important;
    }
}

#wardrobe-radio input[type="radio"],
.fit-search-card input[type="radio"] {
    width: 14px !important;
    height: 14px !important;
    min-width: 14px !important;
    min-height: 14px !important;
    margin: 0 !important;
    accent-color: var(--fit-purple);
}

.fit-search-card textarea,
.fit-search-card input:not([type="radio"]) {
    border-radius: 7px !important;
    border-color: #d9d9e8 !important;
    min-height: 42px !important;
}

.fit-submit {
    border-radius: 7px !important;
    min-height: 44px !important;
    background: linear-gradient(90deg, var(--fit-purple), var(--fit-purple-dark)) !important;
    border: 0 !important;
    color: white !important;
    font-weight: 700 !important;
}

.fit-results {
    margin-top: 18px;
}

.fit-panel {
    border: 1px solid var(--fit-border);
    border-radius: 12px;
    background: var(--fit-card);
    min-height: 330px;
    padding: 18px;
}

.fit-panel .prose,
.fit-panel .md {
    font-size: 13px;
    line-height: 1.55;
}

.fit-panel h3 {
    color: var(--fit-purple);
    font-size: 14px;
    margin-top: 0;
}

.fit-panel strong {
    color: #111827;
}

.fit-examples {
    margin-top: 18px;
    border: 1px solid var(--fit-border);
    border-radius: 12px;
    background: var(--fit-card);
    padding: 16px;
}

.fit-examples-title {
    color: var(--fit-purple);
    font-weight: 800;
    font-size: 14px;
    margin-bottom: 12px;
}

.fit-example-btn {
    border: 1px solid #dddced !important;
    background: #fff !important;
    color: #141827 !important;
    border-radius: 7px !important;
    min-height: 48px !important;
    font-size: 12px !important;
}

.fit-example-btn:hover {
    border-color: var(--fit-purple) !important;
    color: var(--fit-purple) !important;
}

.fit-reset-btn {
    border: 1px solid #dddced !important;
    background: #fff !important;
    color: var(--fit-purple) !important;
    border-radius: 7px !important;
    min-height: 36px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
}

.fit-status {
    color: var(--fit-muted);
    font-size: 12px;
    min-height: 18px;
}

footer {
    display: none !important;
}
"""


EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "baggy jeans under $25",
    "black hoodie under $20",
    "cargo pants size 32",
]


def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    if not user_query or not user_query.strip():
        return "### Search needed\n\nPlease enter what you want to search for.", "", ""

    if wardrobe_choice == "Empty wardrobe (new user)":
        wardrobe = get_empty_wardrobe()
    else:
        wardrobe = get_example_wardrobe()

    session = run_agent(user_query, wardrobe)

    if session["error"]:
        retry_message = ""
        if session.get("retry_info"):
            retry_message = f"\n\n**Retry:** {session['retry_info']['message']}"
        return f"### No listing found\n\n{session['error']}{retry_message}", "", ""

    item = session["selected_item"]
    price = session.get("price_assessment") or {}
    retry_info = session.get("retry_info")
    style_profile = session.get("style_profile") or {}

    extra_lines = []
    if retry_info:
        extra_lines.append(f"**Retry used:** {retry_info['message']}")
    if price:
        extra_lines.append(
            f"**Price check:** {price.get('assessment', 'unknown').title()} - "
            f"{price.get('reasoning', '')}"
        )
        if price.get("comparable_titles"):
            extra_lines.append(
                "**Compared with:** " + "; ".join(price["comparable_titles"])
            )
    if style_profile.get("preferences"):
        extra_lines.append(
            "**Style memory:** " + ", ".join(style_profile["preferences"])
        )
        if style_profile.get("used_memory"):
            extra_lines.append("Used remembered style preferences from an earlier search.")

    extra_text = ""
    if extra_lines:
        extra_text = "\n\n" + "\n\n".join(extra_lines)

    listing_text = f"""
### {item['title']}

**Price:** ${item['price']:.2f}  
**Platform:** {item['platform']}  
**Size:** {item['size']}  
**Condition:** {item['condition']}  
**Category:** {item['category']}  
**Colors:** {', '.join(item.get('colors') or [])}  
**Style tags:** {', '.join(item.get('style_tags') or [])}

---

{item['description']}
{extra_text}
"""

    outfit_text = f"### Outfit ideas\n\n{session['outfit_suggestion']}"
    fit_card_text = f"### Your fit card\n\n{session['fit_card']}"

    return listing_text, outfit_text, fit_card_text


def handle_reset_memory() -> str:
    return reset_style_profile()


def build_interface():
    with gr.Blocks(title="FitFindr", css=APP_CSS) as demo:
        with gr.Column(elem_classes=["fit-shell"]):
            gr.HTML(
                """
                <div class="fit-topbar">
                    <div class="fit-brand">FitFindr</div>
                    <div class="fit-help">How it works</div>
                </div>
                """
            )

            with gr.Column(elem_classes=["fit-hero"]):
                gr.HTML(
                    """
                    <h1>Find your fit. Your way.</h1>
                    <p>Find secondhand pieces and get outfit ideas based on your wardrobe.
                    Describe what you're looking for - include size and price if you want to filter.</p>
                    """
                )

                with gr.Column(elem_classes=["fit-search-card"]):
                    query_input = gr.Textbox(
                        label="What are you looking for?",
                        placeholder="e.g. vintage graphic tee under $30, size M",
                        lines=1,
                    )
                    wardrobe_choice = gr.Radio(
                        choices=["Example wardrobe", "Empty wardrobe (new user)"],
                        value="Example wardrobe",
                        label="Wardrobe",
                        elem_id="wardrobe-radio",
                    )

                    with gr.Row():
                        reset_memory_btn = gr.Button(
                            "Reset style memory",
                            elem_classes=["fit-reset-btn"],
                            scale=0,
                        )
                        reset_status = gr.Markdown("", elem_classes=["fit-status"])

                    submit_btn = gr.Button(
                        "Find it  ->",
                        variant="primary",
                        elem_classes=["fit-submit"],
                    )

                with gr.Row(elem_classes=["fit-results"]):
                    with gr.Column(elem_classes=["fit-panel"]):
                        listing_output = gr.Markdown("### Top listing found")
                    with gr.Column(elem_classes=["fit-panel"]):
                        outfit_output = gr.Markdown("### Outfit ideas")
                    with gr.Column(elem_classes=["fit-panel"]):
                        fitcard_output = gr.Markdown("### Your fit card")

                with gr.Column(elem_classes=["fit-examples"]):
                    gr.HTML('<div class="fit-examples-title">Try these queries</div>')
                    with gr.Row():
                        example_buttons = [
                            gr.Button(query, elem_classes=["fit-example-btn"])
                            for query in EXAMPLE_QUERIES
                        ]

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        reset_memory_btn.click(
            fn=handle_reset_memory,
            inputs=[],
            outputs=reset_status,
        )

        for button, query in zip(example_buttons, EXAMPLE_QUERIES):
            button.click(
                fn=lambda q=query: q,
                inputs=[],
                outputs=query_input,
            )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
