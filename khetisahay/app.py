from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta
import random
from PIL import Image
import io
import numpy as np
from skimage.color import rgb2hsv

app = Flask(__name__)

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


def get_recent_crop_trends():
    return [
        {"name": "Wheat", "modal": 2450, "min": 2200, "max": 2600, "trend": "stable", "past_7_days": [2410, 2380, 2420, 2455, 2470, 2430, 2450]},
        {"name": "Rice (Paddy)", "modal": 3600, "min": 3200, "max": 4200, "trend": "stable", "past_7_days": [3550, 3580, 3620, 3590, 3610, 3630, 3600]},
        {"name": "Maize", "modal": 1850, "min": 1700, "max": 2100, "trend": "down", "past_7_days": [1950, 1920, 1880, 1860, 1840, 1820, 1850]},
        {"name": "Gram (Chana)", "modal": 5250, "min": 4900, "max": 5600, "trend": "up", "past_7_days": [5100, 5150, 5200, 5220, 5280, 5300, 5250]},
        {"name": "Soybean", "modal": 4800, "min": 4500, "max": 5200, "trend": "stable", "past_7_days": [4750, 4780, 4820, 4800, 4790, 4810, 4800]},
        {"name": "Mustard", "modal": 5200, "min": 4900, "max": 5500, "trend": "up", "past_7_days": [5050, 5100, 5150, 5180, 5220, 5250, 5200]},
        {"name": "Groundnut", "modal": 5800, "min": 5200, "max": 6200, "trend": "stable", "past_7_days": [5750, 5700, 5820, 5780, 5850, 5900, 5800]},
        {"name": "Cotton", "modal": 6500, "min": 6000, "max": 7200, "trend": "volatile", "past_7_days": [6200, 6400, 6600, 6800, 6700, 6550, 6500]},
        {"name": "Onion", "modal": 2800, "min": 1500, "max": 4500, "trend": "volatile", "past_7_days": [3200, 3000, 2800, 2600, 2900, 3100, 2800]},
        {"name": "Potato", "modal": 1800, "min": 1200, "max": 2500, "trend": "down", "past_7_days": [2200, 2100, 2000, 1900, 1850, 1820, 1800]},
        {"name": "Tomato", "modal": 2200, "min": 1000, "max": 3500, "trend": "volatile", "past_7_days": [1800, 2000, 2500, 2400, 2100, 1900, 2200]},
        {"name": "Jowar", "modal": 2200, "min": 1900, "max": 2500, "trend": "stable", "past_7_days": [2150, 2180, 2220, 2190, 2210, 2230, 2200]},
        {"name": "Bajra", "modal": 2400, "min": 2100, "max": 2700, "trend": "up", "past_7_days": [2300, 2350, 2400, 2420, 2450, 2480, 2400]},
        {"name": "Ragi", "modal": 3800, "min": 3400, "max": 4200, "trend": "stable", "past_7_days": [3700, 3750, 3800, 3780, 3820, 3850, 3800]},
        {"name": "Arhar / Tur", "modal": 7500, "min": 7000, "max": 8200, "trend": "up", "past_7_days": [7200, 7300, 7400, 7550, 7650, 7700, 7500]},
        {"name": "Moong", "modal": 8600, "min": 8000, "max": 9200, "trend": "stable", "past_7_days": [8500, 8550, 8600, 8580, 8620, 8650, 8600]},
        {"name": "Urad", "modal": 7400, "min": 6800, "max": 8000, "trend": "down", "past_7_days": [7600, 7500, 7400, 7350, 7300, 7250, 7400]},
        {"name": "Sunflower", "modal": 6200, "min": 5800, "max": 6800, "trend": "stable", "past_7_days": [6100, 6150, 6200, 6180, 6220, 6250, 6200]},
        {"name": "Sesame", "modal": 9000, "min": 8500, "max": 9500, "trend": "up", "past_7_days": [8800, 8900, 9000, 9100, 9200, 9300, 9000]},
        {"name": "Barley", "modal": 1950, "min": 1700, "max": 2200, "trend": "stable", "past_7_days": [1900, 1920, 1950, 1930, 1960, 1980, 1950]},
        {"name": "Chilli (Dry)", "modal": 14000, "min": 10000, "max": 18000, "trend": "volatile", "past_7_days": [13000, 13500, 14000, 14500, 14200, 13800, 14000]},
        {"name": "Turmeric", "modal": 13000, "min": 11000, "max": 16000, "trend": "stable", "past_7_days": [12500, 12800, 13000, 12900, 13100, 13200, 13000]},
        {"name": "Ginger", "modal": 12000, "min": 9000, "max": 15000, "trend": "volatile", "past_7_days": [11000, 11500, 12000, 12500, 12200, 11800, 12000]},
        {"name": "Garlic", "modal": 8500, "min": 6000, "max": 11000, "trend": "volatile", "past_7_days": [8000, 8200, 8500, 8700, 8600, 8400, 8500]},
        {"name": "Coriander", "modal": 7000, "min": 5500, "max": 8500, "trend": "stable", "past_7_days": [6800, 6900, 7000, 6950, 7050, 7100, 7000]},
        {"name": "Cumin", "modal": 18000, "min": 15000, "max": 22000, "trend": "up", "past_7_days": [17000, 17500, 18000, 18500, 18200, 17800, 18000]},
        {"name": "Fennel", "modal": 9000, "min": 7000, "max": 11000, "trend": "stable", "past_7_days": [8800, 8900, 9000, 8950, 9050, 9100, 9000]},
        {"name": "Watermelon", "modal": 1200, "min": 800, "max": 1800, "trend": "down", "past_7_days": [1400, 1300, 1200, 1100, 1050, 1000, 1200]},
        {"name": "Muskmelon", "modal": 1800, "min": 1200, "max": 2500, "trend": "volatile", "past_7_days": [1600, 1700, 1800, 1900, 1850, 1750, 1800]},
        {"name": "Mango", "modal": 3500, "min": 2000, "max": 5000, "trend": "volatile", "past_7_days": [3000, 3200, 3500, 3800, 3700, 3400, 3500]},
        {"name": "Banana", "modal": 1800, "min": 1200, "max": 2500, "trend": "stable", "past_7_days": [1700, 1750, 1800, 1780, 1820, 1850, 1800]},
        {"name": "Papaya", "modal": 1500, "min": 1000, "max": 2200, "trend": "down", "past_7_days": [1700, 1600, 1500, 1400, 1350, 1300, 1500]},
        {"name": "Guava", "modal": 2200, "min": 1500, "max": 3000, "trend": "stable", "past_7_days": [2100, 2150, 2200, 2180, 2220, 2250, 2200]},
        {"name": "Apple", "modal": 12000, "min": 9000, "max": 16000, "trend": "up", "past_7_days": [11000, 11500, 12000, 12500, 12200, 11800, 12000]},
        {"name": "Grapes", "modal": 8000, "min": 5000, "max": 11000, "trend": "volatile", "past_7_days": [7000, 7500, 8000, 8500, 8200, 7800, 8000]},
        {"name": "Pomegranate", "modal": 9000, "min": 6000, "max": 13000, "trend": "volatile", "past_7_days": [8000, 8500, 9000, 9500, 9200, 8800, 9000]},
        {"name": "Orange", "modal": 4000, "min": 2500, "max": 5500, "trend": "stable", "past_7_days": [3800, 3900, 4000, 3950, 4050, 4100, 4000]},
        {"name": "Lemon", "modal": 5000, "min": 3000, "max": 7000, "trend": "volatile", "past_7_days": [4500, 4800, 5000, 5200, 5100, 4900, 5000]},
        {"name": "Cauliflower", "modal": 1800, "min": 800, "max": 3000, "trend": "volatile", "past_7_days": [1500, 1600, 1800, 2000, 1900, 1700, 1800]},
        {"name": "Cabbage", "modal": 1500, "min": 700, "max": 2500, "trend": "down", "past_7_days": [1800, 1700, 1600, 1500, 1400, 1300, 1500]},
        {"name": "Brinjal", "modal": 2000, "min": 1000, "max": 3200, "trend": "volatile", "past_7_days": [1800, 1900, 2000, 2100, 2050, 1950, 2000]},
        {"name": "Okra", "modal": 3500, "min": 2000, "max": 5000, "trend": "stable", "past_7_days": [3300, 3400, 3500, 3450, 3550, 3600, 3500]},
        {"name": "Chilli (Green)", "modal": 6000, "min": 4000, "max": 9000, "trend": "volatile", "past_7_days": [5500, 5800, 6000, 6200, 6100, 5900, 6000]},
    ]

CROP_GUIDES = {
    "rice": {
        "name": "Rice / Paddy (धान)",
        "season": "Kharif (main), some summer/rabi",
        "climate": "Warm & humid; 20–35°C, high rainfall or assured irrigation",
        "soil": "Clayey or clay-loam with good water retention; pH 5.5–7.5",
        "sowing_time": "June–July (nursery/transplanting)",
        "seed_rate": "30–40 kg/ha (transplanting)",
        "spacing": "20×15 cm",
        "fertilizer": "N:P:K = 120:60:60 kg/ha (split doses)",
        "irrigation": "Continuous flooding 5 cm during growth; alternate wetting-drying later",
        "major_pests_diseases": "Stem borer, leaf folder, blast, brown spot, sheath blight",
        "harvesting": "Oct–Nov (80–85% grains golden)",
        "yield": "5–8 t/ha",
        "tips": "Use hybrid seeds; maintain water carefully to control weeds"
    },
    "wheat": {
        "name": "Wheat (गेहूं)",
        "season": "Rabi",
        "climate": "Cool & dry; 15–25°C growth, 20–25°C grain filling",
        "soil": "Well-drained fertile loamy/clayey loam; pH 6.0–7.5",
        "sowing_time": "Mid-Oct to mid-Dec (best Nov)",
        "seed_rate": "100–125 kg/ha",
        "spacing": "Row 20–22 cm, depth 4–6 cm",
        "fertilizer": "N:P:K = 120:60:40 kg/ha (half N at sowing)",
        "irrigation": "5–6 irrigations (CRI, tillering, flowering critical)",
        "major_pests_diseases": "Aphids, termites, rust, loose smut, Karnal bunt",
        "harvesting": "March–April (grain moisture 12–14%)",
        "yield": "4–6 t/ha",
        "tips": "Use certified seeds (HD 2967, PBW 550); avoid late sowing"
    },
    "maize": {
        "name": "Maize / Corn (मक्का)",
        "season": "Kharif, rabi, spring",
        "climate": "Warm; 21–30°C, rainfall 500–800 mm",
        "soil": "Well-drained loamy/sandy loam; pH 5.5–7.5",
        "sowing_time": "June–July (kharif), Oct–Nov (rabi)",
        "seed_rate": "20–25 kg/ha",
        "spacing": "60–75 cm rows, 20–25 cm plants",
        "fertilizer": "N:P:K = 120:60:40 kg/ha + zinc",
        "irrigation": "Critical at tasseling & silking",
        "major_pests_diseases": "Stem borer, armyworm, downy mildew, rust",
        "harvesting": "90–120 days (husks dry, grains hard)",
        "yield": "4–7 t/ha",
        "tips": "Hybrid seeds; ridge planting in high rainfall areas"
    },
    "gram": {
        "name": "Gram / Chickpea (चना)",
        "season": "Rabi",
        "climate": "Cool & dry; 15–25°C",
        "soil": "Sandy loam to clay loam; pH 6.0–7.5",
        "sowing_time": "Oct–Nov",
        "seed_rate": "75–100 kg/ha",
        "spacing": "30–45 cm rows",
        "fertilizer": "N:P:K = 20:40:20 kg/ha + Rhizobium",
        "irrigation": "1–2 (flowering & pod filling critical)",
        "major_pests_diseases": "Pod borer, wilt, blight",
        "harvesting": "Feb–April",
        "yield": "1.5–2.5 t/ha",
        "tips": "Inoculate with Rhizobium; drought tolerant"
    },
    "mustard": {
        "name": "Mustard / Rapeseed (सरसों)",
        "season": "Rabi",
        "climate": "Cool; 10–25°C",
        "soil": "Loamy; pH 6.0–7.5",
        "sowing_time": "Oct–Nov",
        "seed_rate": "4–6 kg/ha",
        "spacing": "30 cm rows",
        "fertilizer": "N:P:K = 80:40:40 kg/ha",
        "irrigation": "2–3 (critical at flowering)",
        "major_pests_diseases": "Aphids, alternaria blight",
        "harvesting": "Feb–March",
        "yield": "1.5–2.5 t/ha",
        "tips": "Sow in rows; control aphids early"
    },
    "groundnut": {
        "name": "Groundnut / Peanut (मूंगफली)",
        "season": "Kharif / Rabi",
        "climate": "Warm; 25–35°C",
        "soil": "Light sandy loam; pH 6.0–7.5",
        "sowing_time": "May–June / Nov–Dec",
        "seed_rate": "80–100 kg/ha",
        "spacing": "30×10 cm",
        "fertilizer": "N:P:K = 20:40:30 kg/ha + gypsum",
        "irrigation": "4–5 (pod development critical)",
        "major_pests_diseases": "Tikka, leaf miner, termite",
        "harvesting": "90–120 days",
        "yield": "2–3 t/ha",
        "tips": "Apply gypsum for better pod filling"
    },
    "cotton": {
        "name": "Cotton (कपास)",
        "season": "Kharif",
        "climate": "Warm; 21–30°C, 6–8 frost-free months",
        "soil": "Black cotton soil / well-drained; pH 6.0–8.0",
        "sowing_time": "April–June",
        "seed_rate": "15–20 kg/ha",
        "spacing": "60–90 cm rows",
        "fertilizer": "N:P:K = 120:60:60 kg/ha",
        "irrigation": "4–6 (boll formation critical)",
        "major_pests_diseases": "Bollworm, sucking pests, wilt",
        "harvesting": "Oct–Jan (multiple pickings)",
        "yield": "2–4 t/ha lint",
        "tips": "Use Bt cotton; timely pest management"
    },
    "sugarcane": {
        "name": "Sugarcane (गन्ना)",
        "season": "Pre-season / main",
        "climate": "Tropical/sub-tropical; 20–35°C",
        "soil": "Deep loamy; pH 6.5–7.5",
        "sowing_time": "Feb–March / Oct–Nov",
        "seed_rate": "35,000–40,000 setts/ha",
        "spacing": "75–90 cm rows",
        "fertilizer": "N:P:K = 250:100:100 kg/ha",
        "irrigation": "15–20 (frequent)",
        "major_pests_diseases": "Borer, red rot, wilt",
        "harvesting": "10–18 months",
        "yield": "70–100 t/ha",
        "tips": "Use setts from top portion; trash mulching"
    },
    "soybean": {
        "name": "Soybean (सोयाबीन)",
        "season": "Kharif",
        "climate": "Warm; 20–30°C",
        "soil": "Well-drained loam; pH 6.0–7.5",
        "sowing_time": "June–July",
        "seed_rate": "60–80 kg/ha",
        "spacing": "45 cm rows",
        "fertilizer": "N:P:K = 20:60:40 kg/ha + Rhizobium",
        "irrigation": "2–3 (pod filling critical)",
        "major_pests_diseases": "Girdle beetle, rust, pod borer",
        "harvesting": "Oct–Nov",
        "yield": "2–3 t/ha",
        "tips": "Inoculate seeds; avoid water stress at flowering"
    },
    "barley": {
        "name": "Barley (जौ)",
        "season": "Rabi",
        "climate": "Cool; 10–25°C",
        "soil": "Loamy; pH 6.0–8.0",
        "sowing_time": "Oct–Nov",
        "seed_rate": "75–100 kg/ha",
        "yield": "3–4 t/ha",
        "tips": "Good for malt & feed; tolerant to salinity"
    },
    "jowar": {"name": "Jowar / Sorghum (ज्वार)", "season": "Kharif/Rabi", "yield": "2–4 t/ha", "tips": "Drought tolerant"},
    "bajra": {"name": "Bajra / Pearl Millet (बाजरा)", "season": "Kharif", "yield": "2–3 t/ha", "tips": "Very drought resistant"},
    "ragi": {"name": "Ragi / Finger Millet (रागी)", "season": "Kharif", "yield": "2–4 t/ha", "tips": "Nutritious, grows on poor soils"},
    "arhar": {"name": "Arhar / Pigeon Pea (अरहर)", "season": "Kharif", "yield": "1.5–2.5 t/ha", "tips": "Long duration, intercropping"},
    "moong": {"name": "Moong / Green Gram (मूंग)", "season": "Kharif/Zaid", "yield": "1–1.5 t/ha", "tips": "Short duration"},
    "urad": {"name": "Urad / Black Gram (उड़द)", "season": "Kharif", "yield": "1–1.5 t/ha", "tips": "Nitrogen fixer"},
    "sunflower": {"name": "Sunflower (सूरजमुखी)", "season": "Kharif/Rabi", "yield": "1.5–2.5 t/ha", "tips": "High oil content"},
    "sesame": {"name": "Sesame / Til (तिल)", "season": "Kharif", "yield": "0.5–1 t/ha", "tips": "Short duration oilseed"},
    "jute": {"name": "Jute (जूट)", "season": "Kharif", "yield": "20–25 q/ha fibre", "tips": "Requires high humidity"},
    "tea": {"name": "Tea (चाय)", "season": "Perennial", "yield": "1500–2500 kg/ha", "tips": "Plucking every 7–10 days"},
    "coffee": {"name": "Coffee (कॉफी)", "season": "Perennial", "yield": "800–1500 kg/ha", "tips": "Shade loving"},
    "rubber": {"name": "Rubber (रबर)", "season": "Perennial", "yield": "1500–2000 kg/ha latex", "tips": "Tapping starts after 6 years"},
    "coconut": {"name": "Coconut (नारियल)", "season": "Perennial", "yield": "80–150 nuts/tree/year", "tips": "Tall/dwarf varieties"},
    "onion": {"name": "Onion (प्याज)", "season": "Rabi/Kharif", "yield": "15–25 t/ha", "tips": "Short day for bulb formation"},
    "potato": {"name": "Potato (आलू)", "season": "Rabi", "yield": "20–40 t/ha", "tips": "Seed treatment essential"},
    "tomato": {"name": "Tomato (टमाटर)", "season": "Kharif/Rabi", "yield": "20–50 t/ha", "tips": "Staking & pruning"},
    "brinjal": {"name": "Brinjal / Eggplant (बैंगन)", "season": "Kharif/Rabi", "yield": "20–30 t/ha", "tips": "Fruit borer common"},
    "okra": {"name": "Okra / Ladyfinger (भिंडी)", "season": "Kharif/Zaid", "yield": "10–15 t/ha", "tips": "Pick every 2–3 days"},
    "cauliflower": {"name": "Cauliflower (फूलगोभी)", "season": "Rabi", "yield": "15–25 t/ha", "tips": "Curd protection from sun"},
    "cabbage": {"name": "Cabbage (पत्ता गोभी)", "season": "Rabi", "yield": "20–35 t/ha", "tips": "Head rot control"},
    "chilli": {"name": "Chilli (मिर्च)", "season": "Kharif", "yield": "1.5–3 t/ha dry", "tips": "Capsicum varieties for green"},
    "turmeric": {"name": "Turmeric (हल्दी)", "season": "Kharif", "yield": "20–30 t/ha fresh", "tips": "Rhizome crop, 8–9 months"},
    "ginger": {"name": "Ginger (अदरक)", "season": "Kharif", "yield": "15–25 t/ha", "tips": "Shade in early stage"},
    "garlic": {"name": "Garlic (लहसुन)", "season": "Rabi", "yield": "8–12 t/ha", "tips": "Clove treatment"},
    "coriander": {"name": "Coriander (धनिया)", "season": "Rabi", "yield": "1–1.5 t/ha seed", "tips": "Dual purpose (leaf/seed)"},
    "cumin": {"name": "Cumin (जीरा)", "season": "Rabi", "yield": "0.5–1 t/ha", "tips": "Aromatic, low water"},
    "fennel": {"name": "Fennel (सौंफ)", "season": "Rabi", "yield": "1–2 t/ha", "tips": "Seed spice"},
    "watermelon": {"name": "Watermelon (तरबूज)", "season": "Zaid", "yield": "20–40 t/ha", "tips": "Short duration, high water"},
    "muskmelon": {"name": "Muskmelon (खरबूजा)", "season": "Zaid", "yield": "15–25 t/ha", "tips": "Sweet varieties"},
    "mango": {"name": "Mango (आम)", "season": "Perennial", "yield": "8–15 t/ha", "tips": "King of fruits"},
    "banana": {"name": "Banana (केला)", "season": "Perennial", "yield": "30–50 t/ha", "tips": "High K requirement"},
    "papaya": {"name": "Papaya (पपीता)", "season": "Perennial", "yield": "50–100 t/ha", "tips": "Fast growing"},
    "guava": {"name": "Guava (अमरूद)", "season": "Perennial", "yield": "15–25 t/ha", "tips": "Multiple crops/year"},
    "apple": {"name": "Apple (सेब)", "season": "Temperate perennial", "yield": "10–30 t/ha", "tips": "High altitude"},
    "grapes": {"name": "Grapes (अंगूर)", "season": "Perennial", "yield": "15–25 t/ha", "tips": "Pruning essential"},
    "pomegranate": {"name": "Pomegranate (अनार)", "season": "Perennial", "yield": "10–20 t/ha", "tips": "Drought tolerant"},
    "citrus": {"name": "Citrus (Orange/Lemon) (संतरा/नींबू)", "season": "Perennial", "yield": "15–30 t/ha", "tips": "Citrus canker control"},
    "cashew": {"name": "Cashew (काजू)", "season": "Perennial", "yield": "1–2 t/ha nuts", "tips": "Coastal crop"},
    "arecanut": {"name": "Arecanut (सुपारी)", "season": "Perennial", "yield": "2–4 t/ha", "tips": "Shade crop"},
    "black pepper": {"name": "Black Pepper (काली मिर्च)", "season": "Perennial", "yield": "0.5–1 t/ha", "tips": "Spice vine"},
    "cardamom": {"name": "Cardamom (इलायची)", "season": "Perennial", "yield": "0.3–0.8 t/ha", "tips": "Shade loving"},
    "clove": {"name": "Clove (लौंग)", "season": "Perennial", "yield": "2–5 kg/tree", "tips": "Bud spice"}
}


def detect_pest_and_remedy(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize((256,256))

        img_np = np.array(img)
        hsv = rgb2hsv(img_np)

        hue = hsv[:,:,0]
        saturation = hsv[:,:,1]

        avg_sat = np.mean(saturation)

        if avg_sat < 0.15:
            pest = "Possible Nutrient Deficiency"
            confidence = 0.55
            remedy = "Apply balanced NPK fertilizer and check soil nutrients."

        elif avg_sat > 0.35:
            pest = "Leaf Spot Disease"
            confidence = 0.72
            remedy = "Spray Mancozeb or Copper fungicide."

        elif avg_sat > 0.45:
            pest = "Aphid / Sap Sucking Pest"
            confidence = 0.78
            remedy = "Use Neem oil spray or Imidacloprid."
        else :
            pest = "healthy leaf"
            confidence = 0.98
            remedy = ""

        return pest, confidence, remedy

    except Exception as e:
        return "Analysis failed", 0.0, f"Error: {str(e)}"


def analyze_soil(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)


        img = img.resize((256, 256))
        img_array = np.array(img)


        hsv = rgb2hsv(img_array)


        h, s, v = [], [], []
        regions = [
            hsv[64:192, 64:192],           
            hsv[0:64, 0:64],              
            hsv[0:64, 192:256],          
            hsv[192:256, 0:64],            
            hsv[192:256, 192:256]        
        ]

        for region in regions:
            h.append(np.mean(region[:, :, 0]) * 360)  
            s.append(np.mean(region[:, :, 1]))       
            v.append(np.mean(region[:, :, 2]))       

        h_mean = np.mean(h)
        s_mean = np.mean(s)
        v_mean = np.mean(v)

        confidence = 100 - np.std([h_mean] + h) * 50 

        # Classification
        if 20 < h_mean < 60 and s_mean > 0.25:
            soil_type = "Mixed / Uncertain"
            desc = "Could not confidently classify. Try photo of dry, uniform soil in natural daylight (no plants/shadows)."
        elif v_mean < 0.45 and s_mean < 0.35:
            soil_type = "Black soil (Regur)"
            desc = "Black cotton soil – high clay content. Excellent water retention, ideal for cotton, soybean, wheat, pigeon pea. Cracks in summer."
        elif s_mean < 0.25 and v_mean > 0.65:
            soil_type = "Sandy / Sandy Loam"
            desc = "Sandy loam – light texture, good drainage. Best for groundnut, bajra, vegetables, watermelon. Needs frequent irrigation."
        elif 0.25 < s_mean < 0.55 and 0.45 < v_mean < 0.75:
            soil_type = "Loamy / Alluvial"
            desc = "Loamy / alluvial soil – balanced, fertile. Ideal for rice, wheat, maize, sugarcane, vegetables. High productivity."
        elif h_mean > 180 and s_mean > 0.3 and v_mean < 0.6:
            soil_type = "Laterite / Wet alluvial"
            desc = "Laterite or wet alluvial – acidic, rich in iron/aluminum. Good for tea, coffee, rubber, cashew in high rainfall areas."
        else:
            soil_type = "Red Soil"
            desc = "Red soil is a type of soil that develops in warm, temperate, and humid climates, covering about 13% of the Earth's soil"

        return soil_type, f"{desc} (approx. confidence: {max(40, min(95, confidence)):.0f}%)"

    except Exception as e:
        return "Error", f"Image analysis failed: {str(e)}. Please upload a clear soil photo."

# ────────────────────────────────────────────────
# Home route
# ────────────────────────────────────────────────
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

        # Weather fetch
        lat, lon = 17.3850, 78.4867  # Hyderabad
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,precipitation"
            f"&daily=temperature_2m_max,precipitation_sum"
            f"&timezone=Asia%2FKolkata&past_days=7"
        )

        try:
            resp = requests.get(weather_url, timeout=10).json()
            current = resp.get("current", {})
            daily = resp.get("daily", {})

            temp = current.get("temperature_2m", 28)
            humidity = current.get("relative_humidity_2m", 65)
            rain_today = current.get("precipitation", 0)
            past_rain = daily.get("precipitation_sum", [0] * 8)[-7:] if daily else [0] * 7

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

        if "image" in request.files and request.files["image"].filename:
            file = request.files["image"]
            try:
                img_bytes = file.read()
                pest, conf, remedy = detect_pest_and_remedy(img_bytes)
                pest_result = f"<strong>Detected:</strong> {pest} ({conf:.1%})<br><strong>Remedy:</strong> {remedy}"
            except Exception as e:
                pest_result = f"Pest error: {str(e)}"

        if "soil_image" in request.files and request.files["soil_image"].filename:
            file = request.files["soil_image"]
            try:
                img_bytes = file.read()
                soil_type_name, desc = analyze_soil(img_bytes)
                soil_result = f"<strong>Soil Type:</strong> {soil_type_name}<br>{desc}"
            except Exception as e:
                soil_result = f"Soil analysis error: {str(e)}"

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
            trends = [c for c in trends if search_query in c["name"].lower()]
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
                if search_query in key or search_query in info["name"].lower():
                    crop_info = info
                    break
            if not crop_info:
                message = f"No guide found for '{search_query}'. Try wheat, rice, tomato, etc."
    return render_template("crops.html", crop=crop_info, search_query=search_query, message=message)

if __name__ == "__main__":
    app.run(debug=True)