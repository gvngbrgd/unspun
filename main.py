from flask import Flask, request, jsonify
from html import escape
from firecrawl import FirecrawlApp
from openai import OpenAI
import os

app = Flask(__name__)

# Set your API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxx"

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

@app.route('/')
def home():
    return "Unspun is live!"

@app.route('/analyze', methods=['GET'])
def analyze_article():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400

    try:
        result = fc_app.scrape_url(
            url=url,
            formats=["markdown"],
            only_main_content=True,
            parse_pdf=True,
            max_age=14400000
        )
        # Extract main article content
        content = result.markdown

        if not content or len(content.strip()) == 0:
            print("No content found in Firecrawl response:", vars(result))
            return jsonify({"error": "Could not extract article content"}), 500

        # Trim to stay under token limit and cut at sentence boundary if possible
        content_for_prompt = content[:4000]
        if len(content) > 4000:
            last_period = content_for_prompt.rfind('.')
            if last_period > 3000:
                content_for_prompt = content_for_prompt[:last_period + 1]

        analysis = None

        if openai_client:
            try:
                expert_prompt = f"""
You are an investigative analyst trained in history, sociology, journalism, and political science.

Using the article content below, produce your analysis in this exact structure:

1. Official Narrative (2–3 sentences): Summarize how the article presents the issue. Stay neutral.

2. Jargon & Spin Decode Table (3–5 rows): For each term or phrase, show:
– Phrase
– Literal Meaning
– What It Might Be Hiding

3. Human Story Snapshot (2–3 sentences): Describe, in plain language, how the events likely impact ordinary people. Label as hypothetical if you cannot verify.

4. Follow the Money (2–3 sentences): Briefly note who financially, politically, or commercially benefits from this event or framing.

5. What It Really Means (2 sentences): Succinctly rephrase the core reality behind the headline, in plain language.

Avoid speculation unless labeled. Avoid assuming motives without evidence. Use clear, neutral language.

ARTICLE:
'''
{content_for_prompt}
'''
"""

                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": expert_prompt}]
                )
                analysis = response.choices[0].message.content
            except Exception as openai_error:
                print("❌ OpenAI error:", openai_error)
                analysis = "Analysis unavailable (OpenAI error)"
        else:
            analysis = "Analysis unavailable (no OpenAI key configured)"

        return jsonify({
            "url": url,
            "raw_text": content,
            "analysis": analysis
        })

    except Exception as e:
        print("❌ Error during article analysis:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/view_code', methods=['GET'])
def view_code():
    """Display the contents of this file in a simple textarea."""
    try:
        with open(__file__, 'r') as f:
            code = f.read()
        html_content = (
            "<textarea style='width:100%; height:90vh;' readonly>" +
            escape(code) +
            "</textarea>"
        )
        return html_content
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
