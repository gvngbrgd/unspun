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


def scrape_article(url: str) -> str | None:
    """Retrieve and clean article content using the Firecrawl API."""
    try:
        result = fc_app.scrape_url(
            url=url,
            formats=["text"],
            only_main_content=True,
            parse_pdf=True,
            max_age=14400000,
        )

        content = result.textContent
        if not content:
            print("No textContent found in Firecrawl response:", vars(result))
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

        summary = None
        if openai_client:
            system_prompt = (
                "You are an expert media analyst. Analyze the following article.\n"
                "- Focus only on the **main body of the article**\n"
                "- Ignore sidebars, unrelated headlines, and navigation links\n"
                "- Return a clear, concise summary focused on the article’s core message and human impact"
            )
            try:
                summary_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": filtered_content[:4000]},
                    ],
                )
                summary = summary_response.choices[0].message.content
            except Exception as e:
                print("❌ OpenAI error:", e)
                summary = "Analysis unavailable (OpenAI error)"
        else:
            summary = "Analysis unavailable (no OpenAI key configured)"

        return jsonify({
            "url": url,
            "summary": summary,
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
