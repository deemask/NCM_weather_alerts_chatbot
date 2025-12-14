import streamlit as st
import requests
import os
import sqlite3
import json
from datetime import datetime
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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

init_db()



NCM_URL = "https://meteo.ncm.gov.sa/public/ews/latest.json"

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

def extract_city(q):
    q = q.lower()
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
    prompt = f"""لخص التنبيه التالي من المركز الوطني للأرصاد بشكل بسيط وواضح:

{alert}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    return response.choices[0].message.content



st.title("NCM Weather Alerts Chatbot")
st.write("اسألني عن آخر تنبيهات المركز الوطني للأرصاد.")

user_q = st.text_input("اكتب سؤالك هنا:")

if user_q:
    city = extract_city(user_q)

    if not city:
        st.error("الرجاء ذكر اسم المدينة.")
    else:
        matched = filter_alerts(alerts, city)

        if not matched:
            st.success("لا توجد تنبيهات حالياً لهذه المدينة.")
        else:
            st.subheader("التنبيهات:")
            for alert in matched:
                # save raw alert
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute(
                    "INSERT INTO alerts_log (timestamp, city, raw_alert_json) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), city, json.dumps(alert))
                )
                conn.commit()
                conn.close()

                summary = summarize_alert(alert)
                st.info(summary)

