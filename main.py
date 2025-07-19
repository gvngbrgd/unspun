 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/main.py b/main.py
index 472ef6782efc7a9e9c836808068a687b607632f5..d6af91274e4a408aeea02535ff24fcad71890059 100644
--- a/main.py
+++ b/main.py
@@ -1,91 +1,110 @@
 from flask import Flask, request, jsonify
 from html import escape
 from firecrawl import FirecrawlApp
 from openai import OpenAI
 import os
 
 app = Flask(__name__)
 
 OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
 FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY") or "fc-xxxxxxxxxxxxxxxxxxxxxxxx"
 
 openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
 fc_app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
 
 
 def scrape_article(url: str) -> str | None:
     """Retrieve and clean article content using the Firecrawl API."""
     try:
         result = fc_app.scrape_url(
             url=url,
-            formats=["text"],
+            formats=["markdown"],
             only_main_content=True,
+            exclude_tags=[
+                "nav",
+                "footer",
+                "header",
+                "aside",
+                ".banner",
+                ".popup",
+                ".menu",
+                ".advertisement",
+                "#header",
+                "#footer",
+                "#nav",
+                "#sidebar",
+            ],
             parse_pdf=True,
             max_age=14400000,
+            timeout=30000,
         )
 
-        content = result.textContent
+        content = result.markdown
         if not content:
-            print("No textContent found in Firecrawl response:", vars(result))
+            print("No markdown content found in Firecrawl response:", vars(result))
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
-                "You are an expert media analyst. Analyze the following article.\n"
-                "- Focus only on the **main body of the article**\n"
-                "- Ignore sidebars, unrelated headlines, and navigation links\n"
-                "- Return a clear, concise summary focused on the article’s core message and human impact"
+                "You are a historian, journalist, sociologist, and ethicist analyzing this article for bias, omissions, and human impact.\n"
+                "Your job is to:\n"
+                "1. Identify the core event or claim.\n"
+                "2. Highlight signs of bias, spin, or framing techniques.\n"
+                "3. Note what perspectives are missing or underrepresented.\n"
+                "4. Provide broader social, historical, or political context.\n"
+                "5. Explain the real-world human impact, if applicable.\n\n"
+                "Use plain, accessible language. Interpret and analyze rather than just summarizing."
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
 
EOF
)
