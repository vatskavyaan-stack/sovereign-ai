from flask import Flask, render_template, request, jsonify
from groq import Groq
from tavily import TavilyClient
import re, time

app = Flask(__name__)

# --- CONFIGURATION ---
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"

groq_client = Groq(api_key=GROQ_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# --- PARTNER DATA: Direct-Line Partnerships ---
PARTNERS = [
    {"keyword": "cloud", "title": "Dropbox Business (Partner)", "link": "https://www.dropbox.com/business", "snippet": "Partner Verified: Secure cloud storage for elite teams. Seamless integration.", "is_partner": True},
    {"keyword": "data", "title": "Snowflake Data Cloud (Partner)", "link": "https://www.snowflake.com/", "snippet": "Partner Verified: Mobilize your data with the leading AI Data Cloud.", "is_partner": True}
]

def get_vid_id(url):
    match = re.search(r"(?:v=|\/|embed\/|shorts\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

# --- NEW: WHITE-LABEL API (Sovereign Connect) ---
@app.route('/api/voice', methods=['POST'])
def sovereign_connect():
    data = request.json
    text = data.get('text', '')
    lang = data.get('lang', 'en-US')
    # In a real scenario, you'd trigger TTS here and return an audio stream URL
    return jsonify({"status": "Voice API Ready", "text": text, "lang": lang, "cadence": "human", "timestamp": time.time()})

@app.route('/', methods=['GET', 'POST'])
def home():
    query, results, summary, images, videos = None, [], None, [], []
    detected_lang = request.form.get('lang', 'en-US')
    is_shield_mode = request.form.get('shield_mode') == 'true'

    if request.method == 'POST':
        query = request.form.get('search_query')
        if query:
            # 1. Inject Partner Nodes (if keywords match)
            for p in PARTNERS:
                if p['keyword'] in query.lower():
                    results.append(p)

            # 2. Perform Multi-modal Search (adjusted for Shield Mode)
            # In Shield Mode, Tavily would search specific private domains
            search_data = tavily_client.search(
                query=query, 
                search_depth="advanced", 
                max_results=20, # Fetch more to allow for filtering
                include_images=True,
                # Example: restrict to internal documentation for Shield Mode
                include_domains=["docs.example.com", "intranet.corporate.net"] if is_shield_mode else None 
            )
            
            images.extend(search_data.get('images', [])) # Add images
            raw_web_results = search_data.get('results', [])
            
            # 3. Populate Videos and Web Results (enforcing 10-link limit)
            for r in raw_web_results:
                v_id = get_vid_id(r['url'])
                if v_id and ('youtube' in r['url'] or 'youtu.be' in r['url']):
                    if len(videos) < 8: # Cap videos for UI
                        videos.append({'id': v_id, 'title': r['title'], 'thumb': f"https://img.youtube.com/vi/{v_id}/maxresdefault.jpg"})
                else:
                    # Only add web results if not already a partner link and total < 10
                    if not any(res.get('link') == r['url'] for res in results) and len(results) < 10:
                        results.append({'title': r['title'], 'link': r['url'], 'snippet': r.get('content', '')[:160]})
            
            # 4. AI Synthesis (Bilingual, based on detected language)
            target_lang = "HINDI" if "hi" in detected_lang else "ENGLISH"
            mode_context = "private data only" if is_shield_mode else "web"
            context = "\n".join([res.get('snippet', '') for res in results[:5]])

            try:
                chat = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": f"You are Sovereign. Respond in exactly 50 words in {target_lang}. Mode: {mode_context}. Provide a clinical, human-like summary."},
                        {"role": "user", "content": f"Context: {context}\nQuery: {query}"}
                    ]
                )
                summary = chat.choices[0].message.content
            except Exception as e:
                summary = "क्षमा करें, संप्रभु वर्तमान में डेटा संसाधित करने में असमर्थ है।" if "hi" in detected_lang else "Sovereign is currently unable to process data."

    return render_template('index.html', query=query, results=results, summary=summary, images=images, videos=videos, current_lang=detected_lang, shield_mode=is_shield_mode)
# --- OEM PARTNERSHIP ENDPOINT ---
@app.route('/api/oem/integrate', methods=['POST'])
def oem_integration():
    data = request.json
    device_id = data.get('device_id') # Identify if it's a Samsung, Xiaomi, etc.
    user_query = data.get('query')
    
    # Logic: If the user asks to "Shield my photos", Sovereign triggers device encryption
    if "shield" in user_query.lower():
        return jsonify({
            "action": "TRIGGER_HARDWARE_ENCRYPTION",
            "provider": "Sovereign Shield",
            "status": "Securing Device " + device_id
        })
    
    return jsonify({"status": "Listening", "device": device_id})


import os

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)