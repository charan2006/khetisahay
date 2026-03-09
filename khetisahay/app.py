from flask import Flask, render_template, request, session, redirect, url_for
import requests
from datetime import datetime, timedelta
import random
from PIL import Image
import io
import numpy as np
from skimage.color import rgb2hsv
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production-12345'  # ← REQUIRED for session

# ────────────────────────────────────────────────────────────────
#  Language support
# ────────────────────────────────────────────────────────────────

LANGUAGES = {
    'en': 'English',
    'hi': 'हिन्दी'
}

# Basic translations (expand this as needed)
TRANSLATIONS = {
    'en': {
        'KhetiSahay': 'KhetiSahay',
        'Home': 'Home',
        'Market': 'Market',
        'Crops': 'Crops',
        'Dashboard': 'Dashboard',
        'Weather & Crop Advisory': 'Weather & Crop Advisory',
        'City / Town': 'City / Town',
        'State / UT': 'State / UT',
        'Soil Type (for crop suggestion)': 'Soil Type (for crop suggestion)',
        'Loamy': 'Loamy',
        'Clayey': 'Clayey',
        'Sandy Loam': 'Sandy Loam',
        'Black': 'Black',
        'Red': 'Red',
        'Get Recommendations': 'Get Recommendations',
        'Recommended Crops:': 'Recommended Crops:',
        'Pest / Disease Detector': 'Pest / Disease Detector',
        'Upload Plant Photo': 'Upload Plant Photo',
        'Analyze Plant': 'Analyze Plant',
        'Soil Type Analyzer': 'Soil Type Analyzer',
        'Upload Soil Photo': 'Upload Soil Photo',
        'Analyze Soil': 'Analyze Soil',
        'Past 7 Days Rainfall (mm):': 'Past 7 Days Rainfall (mm):',
        'Day': 'Day',
    },
    'hi': {
        'KhetiSahay': 'खेतीसहाय',
        'Home': 'होम',
        'Market': 'बाज़ार',
        'Crops': 'फसलें',
        'Dashboard': 'डैशबोर्ड',
        'Weather & Crop Advisory': 'मौसम और फसल सलाह',
        'City / Town': 'शहर / कस्बा',
        'State / UT': 'राज्य / केंद्र शासित प्रदेश',
        'Soil Type (for crop suggestion)': 'मिट्टी का प्रकार',
        'Loamy': 'दोमट',
        'Clayey': 'चिकनी',
        'Sandy Loam': 'रेतीली दोमट',
        'Black': 'काली',
        'Red': 'लाल',
        'Get Recommendations': 'सुझाव प्राप्त करें',
        'Recommended Crops:': 'सुझाई गई फसलें:',
        'Pest / Disease Detector': 'कीट / रोग पता लगाने वाला',
        'Upload Plant Photo': 'पौधे की फोटो अपलोड करें',
        'Analyze Plant': 'पौधे का विश्लेषण करें',
        'Soil Type Analyzer': 'मिट्टी प्रकार विश्लेषक',
        'Upload Soil Photo': 'मिट्टी की फोटो अपलोड करें',
        'Analyze Soil': 'मिट्टी का विश्लेषण करें',
        'Past 7 Days Rainfall (mm):': 'पिछले ७ दिनों की बारिश (मिमी):',
        'Day': 'दिन',
    }
}

def get_locale():
    if 'lang' not in session:
        session['lang'] = 'en'
    return session['lang']

@app.context_processor
def inject_translation():
    lang = get_locale()
    def _(key):
        return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return dict(
        _=_,
        current_lang=lang,
        languages=LANGUAGES
    )

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# ────────────────────────────────────────────────────────────────
#  Your original data & functions
# ────────────────────────────────────────────────────────────────

with open("templates/crops.json", encoding="utf-8") as f:           # ← path fix suggestion
    CROP_GUIDES = json.load(f)

def get_recent_crop_trends():
    with open("templates/mandi_market_dataset_300.json", encoding="utf-8") as f:
        return json.load(f)

INDIAN_STATES_UTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

def recommend_crops(temp, humidity, rainfall_today, soil_type):
    recommendations = []
    if 20 <= temp <= 30 and humidity > 60 and rainfall_today > 5 and soil_type in ["loamy", "clayey"]:
        recommendations.append("Rice / Paddy")
    if 15 <= temp <= 28 and rainfall_today < 3 and soil_type in ["loamy", "sandy loam"]:
        recommendations.append("Wheat")
        recommendations.append("Mustard")
    if 25 <= temp <= 35 and humidity < 50 and soil_type == "black":
        recommendations.append("Cotton")
    if soil_type == "red" and temp > 22:
        recommendations.append("Groundnut")
        recommendations.append("Millets")
    
    if not recommendations:
        recommendations = ["Gram", "Maize", "Pulses (general)"]
    
    return recommendations[:3]

def get_market_prices(crop):
    base_prices = {
        "Wheat": 2200, "Rice": 2500, "Cotton": 6500, "Mustard": 4800,
        "Gram": 5200, "Groundnut": 6000, "Maize": 2100, "Rice / Paddy": 2500
    }
    price = base_prices.get(crop, 3000)
    trend = [price + random.randint(-300, 300) for _ in range(7)]
    current = trend[-1]
    change = current - trend[0]
    return {"current": current, "trend": trend, "change": change}

def detect_pest_and_remedy(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((256, 256))

        img_np = np.array(img)
        hsv = rgb2hsv(img_np)

        saturation = hsv[:,:,1]
        avg_sat = np.mean(saturation)

        if avg_sat < 0.15:
            return "Possible Nutrient Deficiency", 0.55, "Apply balanced NPK fertilizer and check soil nutrients."
        elif avg_sat > 0.45:
            return "Aphid / Sap Sucking Pest", 0.78, "Use Neem oil spray or Imidacloprid."
        elif avg_sat > 0.35:
            return "Leaf Spot Disease", 0.72, "Spray Mancozeb or Copper fungicide."
        else:
            return "healthy leaf", 0.98, ""
    except Exception as e:
        return "Analysis failed", 0.0, f"Error: {str(e)}"

def analyze_soil(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((256, 256))
        img_array = np.array(img)
        hsv = rgb2hsv(img_array)

        regions = [
            hsv[64:192, 64:192],
            hsv[0:64, 0:64],
            hsv[0:64, 192:256],
            hsv[192:256, 0:64],
            hsv[192:256, 192:256]
        ]

        h, s, v = [], [], []
        for region in regions:
            h.append(np.mean(region[:, :, 0]) * 360)
            s.append(np.mean(region[:, :, 1]))
            v.append(np.mean(region[:, :, 2]))

        h_mean = np.mean(h)
        s_mean = np.mean(s)
        v_mean = np.mean(v)

        confidence = max(40, min(95, 100 - np.std([h_mean] + h) * 50))

        if 20 < h_mean < 60 and s_mean > 0.25:
            soil_type = "Mixed / Uncertain"
            desc = "Could not confidently classify. Try photo of dry, uniform soil in natural daylight."
        elif v_mean < 0.45 and s_mean < 0.35:
            soil_type = "Black soil (Regur)"
            desc = "Black cotton soil – high clay, good water retention. Ideal for cotton, soybean, wheat."
        elif s_mean < 0.25 and v_mean > 0.65:
            soil_type = "Sandy / Sandy Loam"
            desc = "Light texture, good drainage. Best for groundnut, bajra, vegetables."
        elif 0.25 < s_mean < 0.55 and 0.45 < v_mean < 0.75:
            soil_type = "Loamy / Alluvial"
            desc = "Balanced, fertile. Ideal for rice, wheat, maize, sugarcane."
        elif h_mean > 180 and s_mean > 0.3 and v_mean < 0.6:
            soil_type = "Laterite / Wet alluvial"
            desc = "Acidic, rich in iron. Good for tea, coffee, rubber."
        else:
            soil_type = "Red Soil"
            desc = "Red soil – develops in warm, humid climates."

        return soil_type, f"{desc} (approx. confidence: {confidence:.0f}%)"

    except Exception as e:
        return "Error", f"Image analysis failed: {str(e)}. Please upload a clear photo."

# ────────────────────────────────────────────────────────────────
#  Routes
# ────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
def index():
    weather_data = None
    recommendations = []
    prices_data = {}
    pest_result = None
    soil_result = None
    error_message = None

    if request.method == "POST":
        city = request.form.get("city", "Hyderabad").strip()
        state = request.form.get("state", "Telangana").strip()
        soil_type = request.form.get("soil_type", "loamy")

        # Weather (hardcoded Hyderabad for simplicity – improve later)
        lat, lon = 17.3850, 78.4867
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation"
            f"&daily=precipitation_sum"
            f"&timezone=Asia%2FKolkata&past_days=7"
        )

        try:
            resp = requests.get(weather_url, timeout=10).json()
            current = resp.get("current", {})
            daily = resp.get("daily", {})

            temp = current.get("temperature_2m", 28)
            humidity = current.get("relative_humidity_2m", 65)
            rain_today = current.get("precipitation", 0)
            past_rain = daily.get("precipitation_sum", [0]*8)[-7:] if daily.get("precipitation_sum") else [0]*7

            weather_data = {
                "temp": temp,
                "humidity": humidity,
                "rain_today": rain_today,
                "location": f"{city}, {state}",
                "past_rain": past_rain
            }

            recommendations = recommend_crops(temp, humidity, rain_today, soil_type)
            for crop in recommendations:
                prices_data[crop] = get_market_prices(crop)

        except Exception as e:
            error_message = f"Weather fetch failed: {str(e)}"

        # Plant image
        if "image" in request.files and request.files["image"].filename:
            try:
                img_bytes = request.files["image"].read()
                pest, conf, remedy = detect_pest_and_remedy(img_bytes)
                pest_result = f"<strong>Detected:</strong> {pest} ({conf:.1%})<br><strong>Remedy:</strong> {remedy}"
            except Exception as e:
                pest_result = f"Error: {str(e)}"

        # Soil image
        if "soil_image" in request.files and request.files["soil_image"].filename:
            try:
                img_bytes = request.files["soil_image"].read()
                soil_type_name, desc = analyze_soil(img_bytes)
                soil_result = f"<strong>Soil Type:</strong> {soil_type_name}<br>{desc}"
            except Exception as e:
                soil_result = f"Error: {str(e)}"

    return render_template("index.html",
                           states=INDIAN_STATES_UTS,
                           weather=weather_data,
                           recs=recommendations,
                           prices=prices_data,
                           pest_result=pest_result,
                           soil_result=soil_result,
                           error=error_message)

@app.route("/market", methods=["GET", "POST"])
def market():
    trends = get_recent_crop_trends()
    search_query = ""
    if request.method == "POST":
        search_query = request.form.get("search", "").strip().lower()
        if search_query:
            trends = [c for c in trends if search_query in c.get("name", "").lower()]
    return render_template("market.html", trends=trends, search_query=search_query)

@app.route("/crops", methods=["GET", "POST"])
def crops():
    crop_info = None
    search_query = ""
    message = ""
    if request.method == "POST":
        search_query = request.form.get("search", "").strip().lower()
        if search_query:
            for key, info in CROP_GUIDES.items():
                if search_query in key.lower() or search_query in info.get("name", "").lower():
                    crop_info = info
                    break
            if not crop_info:
                message = f"No guide found for '{search_query}'. Try wheat, rice, tomato, etc."
    return render_template("crops.html", crop=crop_info, search_query=search_query, message=message)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)