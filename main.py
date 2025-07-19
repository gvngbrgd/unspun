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
        # The firecrawl SDK returns a ScrapeResponse object
        content = result.textContent

        raw_content = content
        clean_paragraphs = [
            p.strip() for p in raw_content.split("\n")
            if len(p.strip()) > 60 and p.count("http") < 2
        ]
        filtered_content = "\n\n".join(clean_paragraphs)

        if not content:
            print("No content found in Firecrawl response:", vars(result))
            return jsonify({"error": "Could not extract article content"}), 500

        # Optional: summarize with OpenAI using filtered content
        summary = None
        if openai_client:
            try:
                system_prompt = (
                    "Read this article and summarize it through the lens of a historian, "
                    "a sociologist, a media literacy expert, and a local journalist. "
                    "Analyze for bias, framing, human impact, and what may have been omitted. "
                    "If funding or political influence is visible, note it. "
                    "Then return a short summary (5–7 sentences) in plain English that "
                    "captures the full picture."
                )

                content_for_gpt = filtered_content
                if len(content_for_gpt) > 4000:
                    truncated = content_for_gpt[:4000]
                    last_period = truncated.rfind('.')
                    if last_period > 3000:
                        truncated = truncated[:last_period + 1]
                    content_for_gpt = truncated

                summary_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Article:\n" + content_for_gpt}
                    ]
                )
                summary = summary_response.choices[0].message.content
            except Exception as openai_error:
                print(f"❌ OpenAI API error: {str(openai_error)}")
                summary = "Summary unavailable - OpenAI API error"
        else:
            summary = "Summary unavailable - OpenAI API key not configured"
        return jsonify({
            "url": url,
            "summary": summary,
            "raw_text": filtered_content
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
