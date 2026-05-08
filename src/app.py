import streamlit as st
import os, unicodedata, re, requests
import pandas as pd
import numpy as np
import pytz
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="LXT BambooSync Montreal", layout="wide", page_icon="📊")

# Récupération des secrets
API_KEY = st.secrets.get("BAMBOOHR_API_KEY")
SUBDOMAIN = st.secrets.get("BAMBOOHR_SUBDOMAIN", "lxt")
COMPANY_TZ = "America/Toronto"

# ---------- UTILS DE NORMALISATION ----------
def norm_email(s):
    if pd.isna(s): return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\u200B-\u200D\uFEFF]", "", s).replace(" ", "")

def email_localpart(s):
    s = norm_email(s)
    return s.split("@", 1)[0] if "@" in s else s

# ---------- MAPPING COMPLET (Source de vérité) ----------
MAPPING = [
    {"hrid":5917, "name":"Felicia Wong", "courriel":"mu_t1-cab662@sdoperapera.com", "employeeId":1815,"Language":"Australian","rater_id":298069},
    {"hrid":6331, "name":"Alexander Slack", "courriel":"mu_t1-846c88@sdoperapera.com", "employeeId":2343,"Language":"Australian", "rater_id":449089},
    {"hrid":6339, "name":"Ian Zhi Quan Lee", "courriel":"mu_t1-ff4c16@sdoperapera.com", "employeeId":2351,"Language":"Australian", "rater_id":441514},
    {"hrid":6338, "name":"Dean Ash", "courriel":"mu_t1-214777@sdoperapera.com", "employeeId":2350,"Language":"Australian", "rater_id":447374},
    {"hrid":6343, "name":"Hayley Puckeridge", "courriel":"mu_t1-7dbd16@sdoperapera.com", "employeeId":2356,"Language":"Australian", "rater_id":447273},
    {"hrid":6347, "name":"Gilson Cruzat", "courriel":"mu_t1-65a457@sdoperapera.com", "employeeId":2360,"Language":"Australian", "rater_id":434645},
    {"hrid":6354, "name":"Robyn Treacy", "courriel":"mu_t1-d4bdd9@sdoperapera.com", "employeeId":2367,"Language":"Australian", "rater_id":438888},
    {"hrid":1309, "name":"Joshua Ortaleza", "courriel":"mu_t1-df4a19@sdoperapera.com", "employeeId":568,"Language":"Australian", "rater_id":447172},
    {"hrid":6332, "name":"Alexandra de Guzman", "courriel":"mu_t1-469024@sdoperapera.com", "employeeId":2344,"Language":"Australian", "rater_id":448788},
    {"hrid":6010, "name":"Jean Kyle Alvarez", "courriel":"mu_t1-a872b5@sdoperapera.com", "employeeId":1914,"Language":"Australian", "rater_id":352823},
    {"hrid":5718, "name":"Ikechukwu Ejechi", "courriel":"mu_t1-a827ac@sdoperapera.com", "employeeId":1600,"Language":"English", "rater_id":414236},
    {"hrid":5712, "name":"Derrick Narkah", "courriel":"mu_t1-a07134@sdoperapera.com", "employeeId":1597,"Language":"English", "rater_id":413833},
    {"hrid":6129, "name":"Xiaoman Cai", "courriel":"mu_t1-a2b19e@sdoperapera.com", "employeeId":2047,"Language":"Taiwanese", "rater_id":357365},
    {"hrid":6137, "name":"Hsiu Fang Hung", "courriel":"mu_t1-7854df@sdoperapera.com", "employeeId":2055,"Language":"Taiwanese", "rater_id":375453},
    {"hrid":6026, "name":"Weiqiang Wang", "courriel":"mu_t1-3fde0a@sdoperapera.com", "employeeId":1930,"Language":"Taiwanese", "rater_id":406560},
    {"hrid":6126, "name":"Huilei Wang", "courriel":"mu_t1-603f10@sdoperapera.com", "employeeId":2044,"Language":"Taiwanese", "rater_id":439697},
    {"hrid":6184, "name":"Chia Fan Hsu (Fan)", "courriel":"mu_t1-e829a0@sdoperapera.com", "employeeId":2103,"Language":"Taiwanese", "rater_id":381319},
    {"hrid":6265, "name":"Hsinyi Lee", "courriel":"mu_t1-6147ae@sdoperapera.com", "employeeId":2267,"Language":"Taiwanese", "rater_id":441008},
    {"hrid":6266, "name":"Lixiong Wei", "courriel":"mu_t1-8de2fa@sdoperapera.com", "employeeId":2268,"Language":"Cantonese", "rater_id":441109},
    {"hrid":6196, "name":"Yu Kiu Li", "courriel":"mu_t1-426166@sdoperapera.com", "employeeId":2116,"Language":"Cantonese", "rater_id":439899},
    {"hrid":6195, "name":"Lu Yan Li", "courriel":"mu_t1-365930@sdoperapera.com", "employeeId":2115, "Language":"Cantonese", "rater_id":440302},
    {"hrid":6115, "name":"Phouangsouvanh Misaiphon", "courriel":"mu_t1-7eb49e@sdoperapera.com", "employeeId":2021, "Language":"Lao", "rater_id":434242},
    {"hrid":5959, "name":"Sayprasongh Savann", "courriel":"mu_t1-458248@sdoperapera.com", "employeeId":1862, "Language":"Lao", "rater_id":439695},
    {"hrid":5957, "name":"Saleumsith Misaiphon", "courriel":"mu_t1-eacd8c@sdoperapera.com", "employeeId":1860, "Language":"Lao", "rater_id":438079},
    {"hrid":6111, "name":"Ariya Misaiphon", "courriel":"mu_t1-bb9a18@sdoperapera.com", "employeeId":2018, "Language":"Lao", "rater_id":439998},
    {"hrid":6109, "name":"Souriny Phomthavong", "courriel":"mu_t1-1db9ee@sdoperapera.com", "employeeId":2017, "Language":"Lao","rater_id":440301},
    {"hrid":5971, "name":"Budiman Lauw", "courriel":"mu_t1-88a22a@sdoperapera.com", "employeeId":1876, "Language":"Indonesian", "rater_id":352010},
    {"hrid":5941, "name":"Hyun Jeong Park", "courriel":"mu_t1-a85ca4@sdoperapera.com", "employeeId":1841, "Language":"Korean", "rater_id":329787},
    {"hrid":6299, "name":"Lucas Su-hyun Park", "courriel":"mu_t1-a5526c@sdoperapera.com", "employeeId":2305, "Language":"Korean", "rater_id":445252},
    {"hrid":5874, "name":"Jeremy Jaret Cruz", "courriel":"mu_t1-f7be16@sdoperapera.com", "employeeId":1767, "Language":"French", "rater_id":389892},
    {"hrid":1489, "name":"Dudley Orestil", "courriel":"mu_t1-274483@sdoperapera.com", "employeeId":751, "Language":"French", "rater_id":None},
    {"hrid":5868, "name":"Yannis Guibinga", "courriel":"mu_t1-295d80@sdoperapera.com", "employeeId":1761, "Language":"French", "rater_id":354636},
    {"hrid":5866, "name":"Bernard Boucher", "courriel":"mu_t1-380a88@sdoperapera.com", "employeeId":1759, "Language":"French", "rater_id":414438},
    {"hrid":6297, "name":"Alissa Rivera-Laporte", "courriel":"mu_t1-cf4f6f@sdoperapera.com", "employeeId":2303, "Language":"French", "rater_id":445656},
    {"hrid":6314, "name":"Lea Vong", "courriel":"mu_t1-bd5449@sdoperapera.com", "employeeId":2322, "Language":"French", "rater_id":448786},
    {"hrid":6313, "name":"Tidiane Yeo", "courriel":"mu_t1-bc0d65@sdoperapera.com", "employeeId":2321, "Language":"French", "rater_id":448787},
    {"hrid":5899, "name":"Ugo Trelis", "courriel":"mu_t1-d5cb9b@sdoperapera.com", "employeeId":1789, "Language":"French", "rater_id":414034},
    {"hrid":5871, "name":"Hiba El Moataqid", "courriel":"mu_t1-2e8579@sdoperapera.com", "employeeId":1764, "Language":"French", "rater_id":354838},
    {"hrid":5348, "name":"Azizbek Numonov", "courriel":"mu_t1-1af543@sdoperapera.com", "employeeId":1509, "Language":"Uzbek", "rater_id":445154},
    {"hrid":6034, "name":"Khusniyabonu Imomova", "courriel":"mu_t1-33bfb4@sdoperapera.com", "employeeId":1937, "Language":"Uzbek", "rater_id":445555},
    {"hrid":5840, "name":"Abdulatif Nematullaev", "courriel":"mu_t1-ed775f@sdoperapera.com", "employeeId":1732, "Language":"Uzbek", "rater_id":445355},
    {"hrid":6306, "name":"Madina Kodirova", "courriel":"mu_t1-216d9c@sdoperapera.com", "employeeId":2312, "Language":"Uzbek", "rater_id":445050},
    {"hrid":6303, "name":"Asliddin Malikov", "courriel":"mu_t1-633923@sdoperapera.com", "employeeId":2309, "Language":"Uzbek", "rater_id":445356},
    {"hrid":6304, "name":"Khumoyun Ergashev", "courriel":"mu_t1-936f8c@sdoperapera.com", "employeeId":2310, "Language":"Uzbek", "rater_id":445051},
    {"hrid":6357, "name":"Jennafa Rosenblatt", "courriel":"mu_t1-1c3bd3@sdoperapera.com", "employeeId":2370,"Language":"Australian", "rater_id":439392},
    {"hrid":6116, "name":"Soukhinkham Pakdimounivong", "courriel":"mu_t1-93f997@sdoperapera.com", "employeeId":2022,"Language":"Lao", "rater_id":444747},
    {"hrid":6363, "name":"Robin Graham", "courriel":"mu_t1-53daf4@sdoperapera.com", "employeeId":2388,"Language":"Australian", "rater_id":443841},
    {"hrid":5997, "name":"Hafsa Patel", "courriel":"mu_t1-25701a@sdoperapera.com", "employeeId":1902,"Language":"Australian", "rater_id":450402},
    {"hrid":6370, "name":"Patricia Hamilton", "courriel":"mu_t1-09472c@sdoperapera.com", "employeeId":2397,"Language":"French", "rater_id":453735},
    {"hrid":6368, "name":"Yannick Coulibaly", "courriel":"mu_t1-792ce8@sdoperapera.com", "employeeId":2395,"Language":"French", "rater_id":455048},
    {"hrid":6372, "name":"Marc-André Veillette", "courriel":"mu_t1-0e3dc2@sdoperapera.com", "employeeId":2399,"Language":"French", "rater_id":459189},
    {"hrid":6369, "name":"Chamy Diabate", "courriel":"mu_t1-b396e6@sdoperapera.com", "employeeId":2396,"Language":"French", "rater_id":447474},
    {"hrid":6373, "name":"Chih Yu Chou (Jenny)", "courriel":"mu_t1-ae3afd@sdoperapera.com", "employeeId":2408,"Language":"Taiwanese", "rater_id":470301}
]

# ---------- LOGIQUE API AVEC CACHE ----------
@st.cache_data(ttl=300)
def fetch_data(start, end, employee_ids):
    base_url = f"https://{SUBDOMAIN}.bamboohr.com/api/v1/time_tracking/timesheet_entries"
    ids_csv = ",".join(map(str, employee_ids))
    r = requests.get(base_url, params={"start": start, "end": end, "employeeIds": ids_csv},
                     headers={"Accept": "application/json"}, auth=(API_KEY, "x"), timeout=30)
    r.raise_for_status()
    return r.json() if isinstance(r.json(), list) else r.json().get("entries", [])

# --- PREPARATION DES DONNÉES DE BASE ---
map_df = pd.DataFrame(MAPPING)
map_df["courriel_norm"] = map_df["courriel"].apply(norm_email)
map_df["email_local"] = map_df["courriel_norm"].apply(email_localpart)
emp_ids = map_df["employeeId"].tolist()

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuration")
    selected_date = st.date_input("Date d'analyse", value=datetime.now(pytz.timezone(COMPANY_TZ)))
    csv_file = st.file_uploader("Fichier CSV de vitesse", type="csv")
    st.divider()
    refresh_btn = st.button("🔄 Actualiser tout", type="primary")

# --- ONGLETS ---
tab1, tab2 = st.tabs(["📊 Performance & Vitesse", "🕒 Présence Live"])

# --- LOGIQUE GLOBALE ---
day_str = selected_date.strftime("%Y-%m-%d")

# 1. FETCH LIVE STATUS (Toujours à jour pour Tab 2)
try:
    with st.spinner("Vérification des présences..."):
        # On vérifie aujourd'hui pour le live
        now_str = datetime.now(pytz.timezone(COMPANY_TZ)).strftime("%Y-%m-%d")
        live_entries = fetch_data(now_str, now_str, emp_ids)
        open_ids = {int(e.get("employeeId")) for e in live_entries if e.get("end") is None and e.get("employeeId")}
except:
    open_ids = set()

# --- TAB 2 : PRÉSENCE LIVE ---
with tab2:
    st.subheader(f"Statut 'Clocked in' — {datetime.now(pytz.timezone(COMPANY_TZ)).strftime('%H:%M')}")
    presence_df = map_df[["hrid", "name", "Language", "employeeId"]].copy()
    presence_df["Statut"] = presence_df["employeeId"].apply(lambda x: "✅ Clocked in" if int(x) in open_ids else "⛔ Not clocked in")
    
    # Couleurs pour le statut
    def color_status(val):
        color = '#2ecc71' if "✅" in val else '#e74c3c'
        return f'color: {color}; font-weight: bold'
    
    #st.dataframe(presence_df.drop(columns="employeeId").style.applymap(color_status, subset=['Statut']), use_container_width=True)
    # On remplace .applymap par .map
    st.dataframe(presence_df.drop(columns="employeeId").style.map(color_status, subset=['Statut']), use_container_width=True)
    
    nb_in = len(open_ids)
    st.metric("Total en ligne", nb_in)

# --- TAB 1 : PERFORMANCE ---
with tab1:
    if not csv_file:
        st.info("Veuillez uploader le fichier CSV pour voir l'analyse de performance.")
    else:
        try:
            # Récupération heures
            entries = fetch_data(day_str, day_str, emp_ids)
            bdf = pd.DataFrame(entries) if entries else pd.DataFrame(columns=["employeeId","hours","projectInfo"])
            
            if not bdf.empty:
                bdf["hours"] = pd.to_numeric(bdf["hours"], errors="coerce").fillna(0.0)
                bdf["taskName"] = bdf.apply(lambda r: (r.get("projectInfo") or {}).get("task", {}).get("name"), axis=1)
                
                bdf["generic_part"] = bdf["hours"].where(bdf["projectInfo"].isna(), 0.0)
                bdf["break_part"] = bdf["hours"].where(bdf["taskName"] == "Break (Paid)", 0.0)
                bdf["specific_nobreak"] = bdf["hours"].where(bdf["projectInfo"].notna() & (bdf["taskName"] != "Break (Paid)"), 0.0)
                
                hours_agg = bdf.groupby("employeeId", as_index=False).agg(
                    heures_génériques=("generic_part","sum"),
                    break_heures=("break_part","sum"),
                    heures_spécifiques=("specific_nobreak","sum")
                )
                hours_agg["heures_génériques_plus_break"] = hours_agg["heures_génériques"] + hours_agg["break_heures"]
                hours_agg["heures_totales"] = hours_agg["heures_génériques_plus_break"] + hours_agg["heures_spécifiques"]
            else:
                hours_agg = pd.DataFrame(columns=["employeeId", "heures_totales"])

            # Traitement Vitesse
            raw_csv = pd.read_csv(csv_file)
            raw_csv["email_norm"] = raw_csv["Rater Email"].apply(norm_email)
            csv_agg = raw_csv.groupby("email_norm", as_index=False).agg(
                answered_sum=("Answered","sum"), 
                answered_time_hr=("Answer Time(hr)","sum")
            )
            csv_agg["speed_qph"] = np.where(csv_agg["answered_time_hr"] > 0, csv_agg["answered_sum"] / csv_agg["answered_time_hr"], 0.0).round(2)

            # Fusion
            final = map_df.merge(hours_agg, on="employeeId", how="left").merge(csv_agg, left_on="courriel_norm", right_on="email_norm", how="left")
            
            # KPIs
            final['Utilization'] = ((final['answered_time_hr'] / final['heures_génériques_plus_break']) * 100).replace([np.inf, -np.inf], 0).fillna(0)
            final['Productivité'] = ((final['answered_time_hr'] / final['heures_totales']) * 100).replace([np.inf, -np.inf], 0).fillna(0)

            # Dashboard
            st.subheader(f"Analyse du {day_str}")
            
            c1, c2, c3 = st.columns(3)
            active_final = final[final['speed_qph'] > 0]
            c1.metric("Utilisation Moy.", f"{active_final['Utilization'].mean():.1f}%")
            c2.metric("Productivité Moy.", f"{active_final['Productivité'].mean():.1f}%")
            c3.metric("Heures Totales", f"{final['heures_totales'].sum():.1f}h")

            st.dataframe(active_final[["name", "Language", "heures_totales", "answered_sum", "speed_qph", "Utilization", "Productivité"]].sort_values("speed_qph", ascending=False), use_container_width=True)

        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")