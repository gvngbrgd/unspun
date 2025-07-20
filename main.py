from flask import Flask, request, jsonify
from html import escape
from firecrawl import FirecrawlApp
from openai import OpenAI
import os

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxx"

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

GPT_PROMPT_TEMPLATE = """
You are a historian, sociologist, and political analyst. Analyze this news article content in five sections. Use clear, neutral language. Do not speculate unless explicitly labeled as hypothetical.

CONTENT TO ANALYZE:
{article_text}

STRUCTURE YOUR OUTPUT:
1. Official Narrative (2–3 sentences summarizing the main point of the article)
2. Jargon & Spin Decode Table (3–5 rows in a table with 'Term/Phrase' and 'Decoded Meaning')
3. Human Story Snapshot (2–3 sentence description of how a real person or group might be impacted — use “hypothetical” label if invented)
4. Follow the Money (2–3 sentences identifying any financial, power, or institutional interests connected to the topic)
5. What It Really Means (1–2 clear sentences interpreting the issue in real-world terms, from a public interest perspective)

Label each section clearly and follow the tone and style of a professional researcher writing for a public literacy tool.
"""

def scrape_article(url: str) -> str | None:
    """Retrieve and clean article content using the Firecrawl API."""
    try:
        result = fc_app.scrape_url(
            url=url,
            formats=["text"],
            only_main_content=True,
            exclude_tags=[
                "nav",
                "footer",
                "header",
                "aside",
                ".banner",
                ".popup",
                ".menu",
                ".advertisement",
                "#header",
                "#footer",
                "#nav",
                "#sidebar",
            ],
            parse_pdf=True,
            max_age=14400000,
            timeout=30000,
        )

        content = result.textContent
        if not content:
            print("No text content found in Firecrawl response:", vars(result))
            return None

        raw_content = content
        clean_paragraphs = [
            p.strip()
            for p in raw_content.split("\n")
            if len(p.strip()) > 60 and p.count("http") < 2
        ]
        filtered_content = "\n\n".join(clean_paragraphs)
        return filtered_content
    except Exception as exc:
        print("Error during scraping:", exc)
        return None


@app.route("/")
def home():
    return "Unspun is live!"

@app.route("/analyze", methods=["GET"])
def analyze_article():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        filtered_content = scrape_article(url)
        if not filtered_content:
            return jsonify({"error": "Could not extract article content"}), 500

        analysis = None
        if openai_client:
            try:
                prompt = GPT_PROMPT_TEMPLATE.format(article_text=filtered_content[:4000])
                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                )
                analysis = response.choices[0].message.content
            except Exception as e:
                print("❌ OpenAI error:", e)
                analysis = "Analysis unavailable (OpenAI error)"
        else:
            analysis = "Analysis unavailable (no OpenAI key configured)"

        return jsonify({
            "url": url,
            "analysis": analysis,
            "raw_text": filtered_content,
        })

    except Exception as e:
        print("❌ Error during article analysis:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/view_code")
def view_code():
    """Display the contents of this file in a textarea."""
    try:
        with open(__file__, "r") as f:
            code = f.read()
        return (
            "<textarea style='width:100%; height:90vh;' readonly>"
            + escape(code)
            + "</textarea>"
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
