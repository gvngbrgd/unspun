from flask import Flask, request, jsonify
from html import escape
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from openai import OpenAI
import os

app = Flask(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxx"

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)


class ArticleSchema(BaseModel):
    main_content: str


def extract_article(url: str) -> str | None:
    """Retrieve and clean article content using the Firecrawl extract endpoint."""
    try:
        response = fc_app.extract(
            urls=[url],
            prompt="Extract only the main article text.",
            schema=ArticleSchema.model_json_schema(),
        )

        data = response.get("data") if isinstance(response, dict) else getattr(response, "data", None)
        if not data or "main_content" not in data:
            print("No data found in Firecrawl response:", response)
            return None

        content = data["main_content"]
        clean_paragraphs = [
            p.strip()
            for p in str(content).split("\n")
            if len(p.strip()) > 60 and p.count("http") < 2
        ]
        return "\n\n".join(clean_paragraphs)
    except Exception as exc:
        print("Error during extraction:", exc)
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
        filtered_content = extract_article(url)
        if not filtered_content:
            return jsonify({"error": "Could not extract article content"}), 500

        summary = None
        if openai_client:
            try:
                system_prompt = (
                    "You are an expert media analyst. Analyze the following article.\n"
                    "- Focus only on the **main body of the article**\n"
                    "- Ignore sidebars, unrelated headlines, and navigation links\n"
                    "- Return a clear, concise summary focused on the article’s core message and human impact"
                )

                content_for_summary = filtered_content
                if len(content_for_summary) > 4000:
                    truncated = content_for_summary[:4000]
                    last_period = truncated.rfind(".")
                    content_for_summary = truncated[: last_period + 1] if last_period != -1 else truncated

                summary_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content_for_summary},
                    ],
                )
                summary = summary_response.choices[0].message.content
            except Exception as e:
                print("❌ OpenAI error:", e)
                summary = "Summary unavailable - OpenAI error"
        else:
            summary = "Summary unavailable - no OpenAI key configured"

        return jsonify({
            "url": url,
            "raw_text": filtered_content,
            "analysis": summary,
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
        return "<textarea style='width:100%; height:90vh;' readonly>" + escape(code) + "</textarea>"
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
