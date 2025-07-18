import os
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# Initialize Flask app
app = Flask(__name__)

# Load secrets
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")

# Init OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# The Unspun analysis prompt
def build_prompt(article_text):
    return f"""
You are Unspun. Analyze this article with journalistic, sociological, political, and historical insight. Be objective. Provide context, motivations, human impact, historical patterns, and questions readers should ask. Return only the analysis, with references.

Article:
{article_text}
""".strip()

def scrape_article(url):
    response = requests.post(
        "https://api.firecrawl.dev/v1/scrape",
        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
        json={"url": url}
    )

    print("Firecrawl status:", response.status_code)
    print("Firecrawl raw response:", response.text)

    try:
        result = response.json()
    except Exception as e:
        print("JSON decode error:", str(e))
        return None

    print("Firecrawl parsed JSON:", result)

    # ✅ Updated fallback for Firecrawl keys
    content = (
        result.get("pageContent") or
        result.get("data", {}).get("textContent") or
        result.get("articleText") or
        result.get("content")
    )

    if not content:
        print("No article content found. Available keys:", result.keys())

    return content  # <-- must be indented to match the function!

# Main route: /analyze?url=https://...
@app.route('/analyze', methods=['GET'])
def analyze():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    article_text = scrape_article(url)
    if not article_text:
        return jsonify({"error": "Could not extract article"}), 500

    prompt = build_prompt(article_text)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )
        answer = response.choices[0].message.content
        return jsonify({"analysis": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    article_text = scrape_article(url)
    if not article_text:
        return jsonify({"error": "Could not extract article"}), 500

    return jsonify({"text": article_text})

# Health check
@app.route('/')
def index():
    return '✅ Unspun backend is live.'

# Run the Flask server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
