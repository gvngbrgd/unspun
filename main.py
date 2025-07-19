 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/main.py b/main.py
index 27bfa2e490a6d15f2a0cc1e8c4dbdab2658f4fbb..472ef6782efc7a9e9c836808068a687b607632f5 100644
--- a/main.py
+++ b/main.py
@@ -1,98 +1,106 @@
 from flask import Flask, request, jsonify
 from html import escape
-import requests
+from firecrawl import FirecrawlApp
+from openai import OpenAI
 import os
-import openai
-from bs4 import BeautifulSoup
 
 app = Flask(__name__)
 
-FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
 OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
-openai.api_key = OPENAI_API_KEY
+FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxxxx"
 
-# Analysis prompt
-GPT_PROMPT_TEMPLATE = """
-You are a historian, sociologist, and political analyst. Analyze this news article content in five sections. Use clear, neutral language. Do not speculate unless explicitly labeled as hypothetical.
+openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
+fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
 
-CONTENT TO ANALYZE:
-{article_text}
-
-STRUCTURE YOUR OUTPUT:
-1. Official Narrative
-2. Jargon & Spin Decode Table
-3. Human Story Snapshot
-4. Follow the Money
-5. What It Really Means
-
-Label each section clearly and follow the tone and style of a professional researcher writing for a public literacy tool.
-"""
 
 def scrape_article(url: str) -> str | None:
     """Retrieve and clean article content using the Firecrawl API."""
     try:
-        response = requests.post(
-            "https://api.firecrawl.dev/v1/scrape",
-            headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
-            json={"url": url, "formats": ["extract"]},
-            timeout=30,
+        result = fc_app.scrape_url(
+            url=url,
+            formats=["text"],
+            only_main_content=True,
+            parse_pdf=True,
+            max_age=14400000,
         )
-        response.raise_for_status()
-        data = response.json()
-        content = data.get("extract") or data.get("markdown") or data.get("html")
+
+        content = result.textContent
         if not content:
+            print("No textContent found in Firecrawl response:", vars(result))
             return None
-        cleaned = BeautifulSoup(content, "html.parser").get_text()
-        return cleaned[:5000]
+
+        raw_content = content
+        clean_paragraphs = [
+            p.strip()
+            for p in raw_content.split("\n")
+            if len(p.strip()) > 60 and p.count("http") < 2
+        ]
+        filtered_content = "\n\n".join(clean_paragraphs)
+        return filtered_content
     except Exception as exc:
         print("Error during scraping:", exc)
         return None
 
-def analyze_with_gpt(text: str) -> str:
-    """Send cleaned text to GPT-4 for analysis."""
-    try:
-        prompt = GPT_PROMPT_TEMPLATE.format(article_text=text)
-        response = openai.ChatCompletion.create(
-            model="gpt-4",
-            messages=[
-                {"role": "system", "content": "You are a helpful analyst."},
-                {"role": "user", "content": prompt},
-            ],
-            temperature=0.3,
-        )
-        return response.choices[0].message.content
-    except Exception as exc:
-        print("GPT error:", exc)
-        return "Error generating analysis."
 
 @app.route("/")
 def home():
     return "Unspun is live!"
 
-@app.route("/analyze")
-def analyze():
+@app.route("/analyze", methods=["GET"])
+def analyze_article():
     url = request.args.get("url")
     if not url:
-        return jsonify({"error": "Missing URL"}), 400
+        return jsonify({"error": "URL parameter is required"}), 400
+
+    try:
+        filtered_content = scrape_article(url)
+        if not filtered_content:
+            return jsonify({"error": "Could not extract article content"}), 500
+
+        summary = None
+        if openai_client:
+            system_prompt = (
+                "You are an expert media analyst. Analyze the following article.\n"
+                "- Focus only on the **main body of the article**\n"
+                "- Ignore sidebars, unrelated headlines, and navigation links\n"
+                "- Return a clear, concise summary focused on the article’s core message and human impact"
+            )
+            try:
+                summary_response = openai_client.chat.completions.create(
+                    model="gpt-4",
+                    messages=[
+                        {"role": "system", "content": system_prompt},
+                        {"role": "user", "content": filtered_content[:4000]},
+                    ],
+                )
+                summary = summary_response.choices[0].message.content
+            except Exception as e:
+                print("❌ OpenAI error:", e)
+                summary = "Analysis unavailable (OpenAI error)"
+        else:
+            summary = "Analysis unavailable (no OpenAI key configured)"
 
-    article_content = scrape_article(url)
-    if not article_content:
-        return jsonify({"error": "Failed to extract article content."}), 500
+        return jsonify({
+            "url": url,
+            "summary": summary,
+            "raw_text": filtered_content,
+        })
 
-    analysis = analyze_with_gpt(article_content)
-    return jsonify({"url": url, "raw_text": article_content, "analysis": analysis})
+    except Exception as e:
+        print("❌ Error during article analysis:", str(e))
+        return jsonify({"error": str(e)}), 500
 
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
 
EOF
)
