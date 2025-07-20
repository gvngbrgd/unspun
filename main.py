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
        # Use Firecrawl's extract endpoint to obtain the main article text
        extract_result = fc_app.extract(
            urls=[url],
            prompt="Extract the main article text as plain text."
        )
        # extract() returns a dictionary with success flag and data payload
        content = ""
        if isinstance(extract_result, dict):
            content = extract_result.get("data") or ""
            if isinstance(content, dict):
                # If a schema was not specified, the text may be under the
                # first key in the data dictionary
                content = next(iter(content.values()), "")

        # Filter out very short lines or link-heavy text to keep only the main body
        raw_content = content
        clean_paragraphs = [
            p.strip() for p in raw_content.split("\n")
            if len(p.strip()) > 60 and p.count("http") < 2
        ]
        filtered_content = "\n\n".join(clean_paragraphs)

        if not content:
            print("No content found in Firecrawl response:", extract_result)
            return jsonify({"error": "Could not extract article content"}), 500

        # Optional: summarize with OpenAI
        summary = None
        if openai_client:
            try:
                # Use first 4000 characters but try to cut at sentence boundary
                content_for_summary = filtered_content[:4000]
                if len(filtered_content) > 4000:
                    # Try to cut at last sentence to avoid truncation mid-sentence
                    last_period = content_for_summary.rfind('.')
                    if last_period > 3000:  # Only if we find a period reasonably close to the end
                        content_for_summary = content_for_summary[:last_period + 1]

                summary_prompt = f"""You are a historian, sociologist, and investigative journalist analyzing this article for bias, omissions, and human impact.

Your job is to:
1. Identify the core event or claim.
2. Highlight signs of bias, spin, or framing techniques.
3. Note what perspectives are missing or underrepresented.
4. Provide broader social, historical, or political context.
5. Explain the real-world human impact, if applicable.

Use plain, accessible language — as if explaining to an engaged but non-expert reader. Avoid technical or academic jargon. Be analytical, not just summarizing. Your job is to decode, contextualize, and surface what the article isn’t saying out loud.

Article:
{content_for_summary}
"""
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
