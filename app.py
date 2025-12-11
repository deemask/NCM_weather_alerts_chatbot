import streamlit as st
import requests
import sqlite3
import json
import os
from datetime import datetime
from openai import OpenAI



client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


DB_PATH = "alerts.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            city TEXT,
            raw_alert_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_alert_to_db(city, alert):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO alerts_log (timestamp, city, raw_alert_json) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), city, json.dumps(alert))
    )
    conn.commit()
    conn.close()

init_db()


NCM_URL = "https://meteo.ncm.gov.sa/public/ews/latest.json"

st.set_page_config(page_title="NCM Weather Alerts Chatbot", layout="wide")
st.title("NCM Weather Alerts Chatbot")
st.write("اسألني عن آخر تنبيهات المركز الوطني للأرصاد.")

def load_alerts():
    try:
        res = requests.get(NCM_URL, timeout=10)
        if res.status_code == 200:
            return res.json()
        return []
    except:
        return []

alerts = load_alerts()



CITIES = {
    "جدة": ["جدة", "Jeddah"],
    "مكة": ["مكة", "Makkah", "Mecca"],
    "الرياض": ["الرياض", "Riyadh"],
    "جازان": ["جازان", "جيزان", "Jazan"],
    "المدينة": ["المدينة", "المدينة المنورة", "Medina"],
    "تبوك": ["تبوك", "Tabuk"],
    "الدمام": ["الدمام", "Dammam"],
    "الطائف": ["الطائف", "Taif"],
}

def extract_city(question):
    q = question.strip().lower()
    for city, keywords in CITIES.items():
        for k in keywords:
            if k.lower() in q:
                return city
    return None



def alert_matches_city(alert, city_name):
    city_keys = [k.lower() for k in CITIES[city_name]]

    region_en = str(alert.get("regionEn", "")).lower()
    region_ar = str(alert.get("regionAR", "")).lower()

    
    for ck in city_keys:
        if ck in region_en or ck in region_ar:
            return True

    
    for gov in alert.get("governorates", []):
        gov_ar = str(gov.get("nameAr", "")).lower()
        gov_en = str(gov.get("nameEn", "")).lower()
        for ck in city_keys:
            if ck in gov_ar or ck in gov_en:
                return True

    return False


def filter_alerts(alerts, city_name):
    if not city_name:
        return []
    return [a for a in alerts if alert_matches_city(a, city_name)]



def summarize_alert(alert):
    prompt = f"""
لخص التنبيه التالي من المركز الوطني للأرصاد بطريقة بسيطة وواضحة بدون إضافة معلومات غير موجودة:

{json.dumps(alert, ensure_ascii=False)}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    return response.choices[0].message.content



user_q = st.text_input("اكتب سؤالك هنا:")

if user_q:
    with st.spinner("جاري التحقق من التنبيهات..."):
        city = extract_city(user_q)

        if not city:
            st.error("الرجاء ذكر اسم المدينة في سؤالك.")
        else:
            matched = filter_alerts(alerts, city)

            if not matched:
                st.success("لا توجد أي تنبيهات حالياً لهذه المدينة.")
            else:
                st.subheader("التنبيهات الحالية:")

                for alert in matched:
                    save_alert_to_db(city, alert)  # Log to DB
                    summary = summarize_alert(alert)
                    st.info(summary)
