from flask import Flask, request, jsonify
from html import escape
import requests
import os
import openai
from bs4 import BeautifulSoup

app = Flask(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Analysis prompt
GPT_PROMPT_TEMPLATE = """
You are a historian, sociologist, and political analyst. Analyze this news article content in five sections. Use clear, neutral language. Do not speculate unless explicitly labeled as hypothetical.

CONTENT TO ANALYZE:
{article_text}

STRUCTURE YOUR OUTPUT:
1. Official Narrative
2. Jargon & Spin Decode Table
3. Human Story Snapshot
4. Follow the Money
5. What It Really Means

Label each section clearly and follow the tone and style of a professional researcher writing for a public literacy tool.
"""

def scrape_article(url: str) -> str | None:
    """Retrieve and clean article content using the Firecrawl API."""
    try:
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
            json={"url": url, "formats": ["extract"]},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("extract") or data.get("markdown") or data.get("html")
        if not content:
            return None
        cleaned = BeautifulSoup(content, "html.parser").get_text()
        return cleaned[:8000]
    except Exception as exc:
        print("Error during scraping:", exc)
        return None

def analyze_with_gpt(text: str) -> str:
    """Send cleaned text to GPT-4 for analysis."""
    try:
        prompt = GPT_PROMPT_TEMPLATE.format(article_text=text)
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as exc:
        print("GPT error:", exc)
        return "Error generating analysis."

@app.route("/")
def home():
    return "Unspun is live!"

@app.route("/analyze")
def analyze():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    article_content = scrape_article(url)
    if not article_content:
        return jsonify({"error": "Failed to extract article content."}), 500

    analysis = analyze_with_gpt(article_content)
    return jsonify({"url": url, "raw_text": article_content, "analysis": analysis})

@app.route("/view_code")
def view_code():
    """Display the contents of this file in a textarea."""
    try:
        with open(__file__, "r") as f:
            code = f.read()
        return (
            "<textarea style='width:100%; height:90vh;' readonly>" + escape(code) + "</textarea>"
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

