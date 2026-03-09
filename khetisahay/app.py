from flask import Flask, render_template, request, session, redirect, url_for
import requests
import random
from PIL import Image
import io
import numpy as np
from skimage.color import rgb2hsv
import json

app = Flask(__name__)
app.secret_key = "khetisahay-secret-key"


LANGUAGES = {"en": "English", "hi": "हिन्दी"}

TRANSLATIONS = {
    "en": {
        "KhetiSahay": "KhetiSahay",
        "Home": "Home",
        "Market": "Market",
        "Crops": "Crops",
        "Weather & Crop Advisory": "Weather & Crop Advisory",
        "City / Town": "City / Town",
        "State / UT": "State / UT",
        "Soil Type": "Soil Type",
        "Get Recommendations": "Get Recommendations",
    },
    "hi": {
        "KhetiSahay": "खेतीसहाय",
        "Home": "होम",
        "Market": "बाज़ार",
        "Crops": "फसलें",
        "Weather & Crop Advisory": "मौसम और फसल सलाह",
        "City / Town": "शहर",
        "State / UT": "राज्य",
        "Soil Type": "मिट्टी का प्रकार",
        "Get Recommendations": "सुझाव प्राप्त करें",
    }
}

def get_locale():
    if "lang" not in session:
        session["lang"] = "en"
    return session["lang"]

@app.context_processor
def inject_translation():
    lang = get_locale()
    def _(key):
        return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
    return dict(_=_, languages=LANGUAGES, current_lang=lang)

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in LANGUAGES:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


with open("templates/crops.json", encoding="utf-8") as f:
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

    recommendations=[]

    if 20<=temp<=30 and humidity>60 and rainfall_today>5 and soil_type in ["loamy","clayey"]:
        recommendations.append("Rice / Paddy")

    if 15<=temp<=28 and rainfall_today<3 and soil_type in ["loamy","sandy loam"]:
        recommendations.append("Wheat")
        recommendations.append("Mustard")

    if 25<=temp<=35 and humidity<50 and soil_type=="black":
        recommendations.append("Cotton")

    if soil_type=="red" and temp>22:
        recommendations.append("Groundnut")

    if not recommendations:
        recommendations=["Gram","Maize"]

    return recommendations[:3]


def get_market_prices(crop):

    base_prices={
        "Wheat":2200,
        "Rice":2500,
        "Cotton":6500,
        "Mustard":4800,
        "Gram":5200,
        "Groundnut":6000,
        "Maize":2100
    }

    price=base_prices.get(crop,3000)

    trend=[price+random.randint(-300,300) for _ in range(7)]

    current=trend[-1]

    change=current-trend[0]

    return {"current":current,"trend":trend,"change":change}



def detect_pest_and_remedy(image_bytes):

    try:

        img=Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img=img.resize((256,256))

        img_np=np.array(img)
        hsv=rgb2hsv(img_np)

        avg_sat=np.mean(hsv[:,:,1])

        if avg_sat<0.15:
            return "Nutrient Deficiency","Apply balanced fertilizer"

        elif avg_sat>0.45:
            return "Aphids","Use Neem oil spray"

        elif avg_sat>0.35:
            return "Leaf Spot","Use copper fungicide"

        else:
            return "Healthy Leaf","No treatment required"

    except:
        return "Analysis Failed","Upload clearer image"



def analyze_soil(image_bytes):

    try:

        img=Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img=img.resize((256,256))

        arr=np.array(img)

        avg=np.mean(arr)

        if avg<90:
            return "Black Soil","Good for cotton"

        elif avg>180:
            return "Sandy Soil","Good drainage soil"

        elif 90<avg<150:
            return "Loamy Soil","Highly fertile soil"

        else:
            return "Red Soil","Iron rich soil"

    except:
        return "Error","Upload clearer soil image"



@app.route("/",methods=["GET","POST"])
def index():

    weather_data=None
    recommendations=[]
    prices_data={}
    pest_result=None
    soil_result=None
    error_message=None

    if request.method=="POST":

        city=request.form.get("city","Hyderabad")
        state=request.form.get("state","Telangana")
        soil_type=request.form.get("soil_type","loamy")

        try:

            geo_url=f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
            geo=requests.get(geo_url).json()

            lat=geo["results"][0]["latitude"]
            lon=geo["results"][0]["longitude"]

            weather_url=(
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,precipitation"
                f"&daily=precipitation_sum"
                f"&timezone=Asia%2FKolkata&past_days=7"
            )

            data=requests.get(weather_url).json()

            current=data.get("current",{})
            daily=data.get("daily",{})

            temp=current.get("temperature_2m",28)
            humidity=current.get("relative_humidity_2m",65)
            rain_today=current.get("precipitation",0)

            past_rain=daily.get("precipitation_sum",[0]*7)[-7:]

            weather_data={
                "temp":temp,
                "humidity":humidity,
                "rain_today":rain_today,
                "location":f"{city}, {state}",
                "past_rain":past_rain
            }

            recommendations=recommend_crops(temp,humidity,rain_today,soil_type)

            for crop in recommendations:
                prices_data[crop]=get_market_prices(crop)

        except Exception as e:
            error_message=str(e)

        if "image" in request.files and request.files["image"].filename!="":

            img=request.files["image"].read()
            pest,remedy=detect_pest_and_remedy(img)
            pest_result=f"{pest} — {remedy}"

        if "soil_image" in request.files and request.files["soil_image"].filename!="":

            img=request.files["soil_image"].read()
            soil,desc=analyze_soil(img)
            soil_result=f"{soil} — {desc}"

    return render_template(
        "index.html",
        states=INDIAN_STATES_UTS,
        weather=weather_data,
        recs=recommendations,
        prices=prices_data,
        pest_result=pest_result,
        soil_result=soil_result,
        error=error_message
    )



@app.route("/market",methods=["GET","POST"])
def market():

    trends=get_recent_crop_trends()
    search_query=""

    if request.method=="POST":

        search_query=request.form.get("search","").lower()

        trends=[c for c in trends if search_query in c.get("name","").lower()]

    return render_template("market.html",trends=trends,search_query=search_query)



@app.route("/crops",methods=["GET","POST"])
def crops():

    crop_info=None
    search_query=""
    message=""

    if request.method=="POST":

        search_query=request.form.get("search","").lower()

        for key,info in CROP_GUIDES.items():

            if search_query in key.lower() or search_query in info.get("name","").lower():

                crop_info=info
                break

        if not crop_info:
            message="Crop not found"

    return render_template("crops.html",crop=crop_info,search_query=search_query,message=message)



if __name__=="__main__":
    app.run(debug=True)
