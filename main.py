from flask import Flask, request, jsonify
from html import escape
from firecrawl import FirecrawlApp
from openai import OpenAI
import os

app = Flask(__name__)

# Set your API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxx"
                "xxxxxxx"

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

@app.route('/')
def home():
    return "Unspun is live!"

@app.route('/view_code', methods=['GET'])
def view_code():
    """Display the contents of this file in a simple textarea."""
    try:
        with open(__file__, 'r') as f:
            code = f.read()
        # Using a textarea makes it easy for users to copy the source
        html_content = (
            "<textarea style='width:100%; height:90vh;' readonly>" +
            escape(code) +
            "</textarea>"
        )
        return html_content
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        content = result.markdown

        if not content:
            print("No content found in Firecrawl response:", vars(result))
            return jsonify({"error": "Could not extract article content"}), 500

        # Optional: summarize with OpenAI
        summary = None
        if openai_client:
            try:
                # Use first 4000 characters but try to cut at sentence boundary
                content_for_summary = content[:4000]
                if len(content) > 4000:
                    # Try to cut at last sentence to avoid truncation mid-sentence
                    last_period = content_for_summary.rfind('.')
                    if last_period > 3000:  # Only if we find a period reasonably close to the end
                        content_for_summary = content_for_summary[:last_period + 1]

                summary_prompt = f"Summarize this article:\n\n{content_for_summary}"
                summary_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": summary_prompt}]
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
            "raw_text": content
        })

    except Exception as e:
        print("❌ Error during article analysis:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
