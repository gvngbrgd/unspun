from flask import Flask, request, jsonify
from firecrawl import FirecrawlApp
import openai
import os

app = Flask(__name__)

# Set your API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

openai.api_key = OPENAI_API_KEY
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
        content = result.get("data", {}).get("textContent")

        if not content:
            print("No 'textContent' found. Full Firecrawl response:", result)
            return jsonify({"error": "Could not extract article content"}), 500

        # Optional: summarize with OpenAI
        summary_prompt = f"Summarize this article:\n\n{content[:4000]}"
        summary_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": summary_prompt}]
        )
        summary = summary_response.choices[0].message['content']

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
