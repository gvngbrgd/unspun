from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

FIRECRAWL_API_KEY = "fc-8b541da169e64d6b9f706ebc80a55dd2"
FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v1/scrape-url"

@app.route('/')
def home():
    return "Unspun backend is running."

@app.route('/analyze', methods=['GET'])
def analyze():
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'Missing URL parameter'}), 400

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": url,
        "formats": ["markdown"],
        "only_main_content": True,
        "parse_pdf": True,
        "max_age": 14400000  # Optional caching optimization
    }

    try:
        response = requests.post(FIRECRAWL_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        markdown = result.get("data", {}).get("markdown")
        if not markdown:
            print("⚠️ 'markdown' key not found. Full response data keys:", result.get("data", {}).keys())
            return jsonify({'error': "No 'markdown' content found"}), 500

        return jsonify({'content': markdown})

    except requests.exceptions.HTTPError as e:
        print(f"🔥 HTTP error: {e} - Response: {response.text}")
        return jsonify({'error': 'HTTP error occurred while contacting Firecrawl'}), 500

    except ValueError as e:
        print(f"🔥 JSON decode error: {e} - Raw response: {response.text}")
        return jsonify({'error': 'Invalid JSON response from Firecrawl'}), 500

    except Exception as e:
        print(f"🔥 General error: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True)
