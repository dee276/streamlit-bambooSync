import streamlit as st
import os, unicodedata, re, requests
import pandas as pd
import numpy as np
import pytz
from datetime import datetime

# --- IMPORTATION DES MAPPINGS DEPUIS TON FICHIER EXTERNE ---
try:
    from teams import MAPPINGS
except ImportError:
    st.error("⚠️ Le fichier 'src/teams.py' est introuvable. Assurez-vous qu'il existe dans votre dossier de projet.")
    st.stop()

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="LXT BambooSync", layout="wide", page_icon="📊")

# --- HACK CSS POUR LE CALENDRIER ---
st.markdown("""
    <style>
    div[data-baseweb="datepicker"] { z-index: 999999 !important; }
    .stSidebar [data-testid="stVerticalBlock"] { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Mot de passe requis", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Mot de passe requis", type="password", on_change=password_entered, key="password")
        st.error("😕 Mot de passe incorrect.")
        return False
    return True

if not check_password():
    st.stop()

# --- RÉCUPÉRATION DES SECRETS ---
API_KEY = st.secrets.get("BAMBOOHR_API_KEY")
SUBDOMAIN = st.secrets.get("BAMBOOHR_SUBDOMAIN", "lxt")
COMPANY_TZ = "America/Toronto"

# ---------- UTILS ----------
def norm_email(s):
    if pd.isna(s): return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[\u200B-\u200D\uFEFF]", "", s).replace(" ", "")

def email_localpart(s):
    s = norm_email(s)
    return s.split("@", 1)[0] if "@" in s else s

# ---------- LOGIQUE API ----------
@st.cache_data(ttl=300)
def fetch_data(start, end, employee_ids):
    base_url = f"https://{SUBDOMAIN}.bamboohr.com/api/v1/time_tracking/timesheet_entries"
    ids_csv = ",".join(map(str, employee_ids))
    try:
        r = requests.get(base_url, params={"start": start, "end": end, "employeeIds": ids_csv},
                         headers={"Accept": "application/json"}, auth=(API_KEY, "x"), timeout=30)
        r.raise_for_status()
        return r.json() if isinstance(r.json(), list) else r.json().get("entries", [])
    except Exception as e:
        st.error(f"Erreur API BambooHR : {e}")
        return []

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("👥 Sélection Équipe")
    # Utilise maintenant les clés de ton dictionnaire importé
    team_choice = st.selectbox("Équipe à analyser :", list(MAPPINGS.keys()))
    current_team_mapping = MAPPINGS[team_choice]
    
    st.divider()
    st.header("⚙️ Configuration")
    selected_date = st.date_input("Date d'analyse", value=datetime.now(pytz.timezone(COMPANY_TZ)))
    csv_file = st.file_uploader("Fichier CSV de vitesse", type="csv")
    st.divider()
    refresh_btn = st.button("🔄 Actualiser tout", type="primary")

# --- PRÉPARATION DES DONNÉES DU MAPPING ---
map_df = pd.DataFrame(current_team_mapping)
map_df["courriel_norm"] = map_df["courriel"].apply(norm_email)
map_df["email_local"] = map_df["courriel_norm"].apply(email_localpart)
emp_ids = map_df["employeeId"].tolist()

# --- ONGLETS ---
tab1, tab2 = st.tabs(["📊 Performance & Vitesse", "🕒 Présence Live"])

# --- LOGIQUE GLOBALE ---
day_str = selected_date.strftime("%Y-%m-%d")

# 1. FETCH LIVE STATUS (Heure actuelle)
now_str = datetime.now(pytz.timezone(COMPANY_TZ)).strftime("%Y-%m-%d")
live_entries = fetch_data(now_str, now_str, emp_ids)
open_ids = {int(e.get("employeeId")) for e in live_entries if e.get("end") is None and e.get("employeeId")}

# --- TAB 2 : PRÉSENCE LIVE ---
with tab2:
    st.subheader(f"Statut 'Clocked in' — {datetime.now(pytz.timezone(COMPANY_TZ)).strftime('%H:%M')}")
    presence_df = map_df[["hrid", "name", "Language", "employeeId"]].copy()
    presence_df["Statut"] = presence_df["employeeId"].apply(lambda x: "✅ Clocked in" if int(x) in open_ids else "⛔ Not clocked in")
    
    def color_status(val):
        color = '#2ecc71' if "✅" in val else '#e74c3c'
        return f'color: {color}; font-weight: bold'
    
    st.dataframe(presence_df.drop(columns="employeeId").style.map(color_status, subset=['Statut']), use_container_width=True)
    st.metric("Total en ligne", len(open_ids))

# --- TAB 1 : PERFORMANCE ---
with tab1:
    if not csv_file:
        st.info("Veuillez uploader le fichier CSV pour voir l'analyse de performance.")
    else:
        try:
            # Récupération heures Bamboo
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
                hours_agg = pd.DataFrame(columns=["employeeId", "heures_totales", "heures_génériques_plus_break"])

            # Traitement Vitesse CSV
            raw_csv = pd.read_csv(csv_file)
            raw_csv["email_norm"] = raw_csv["Rater Email"].apply(norm_email)
            csv_agg = raw_csv.groupby("email_norm", as_index=False).agg(
                answered_sum=("Answered","sum"), 
                answered_time_hr=("Answer Time(hr)","sum")
            )
            csv_agg["speed_qph"] = np.where(csv_agg["answered_time_hr"] > 0, csv_agg["answered_sum"] / csv_agg["answered_time_hr"], 0.0).round(2)

            # Fusion finale
            final = map_df.merge(hours_agg, on="employeeId", how="left").merge(csv_agg, left_on="courriel_norm", right_on="email_norm", how="left")
            
            # Calculs KPIs
            final['Utilization'] = ((final['answered_time_hr'] / final['heures_génériques_plus_break'].replace(0, np.nan)) * 100).fillna(0)
            final['Productivité'] = ((final['answered_time_hr'] / final['heures_totales'].replace(0, np.nan)) * 100).fillna(0)

            # Dashboard
            st.subheader(f"Analyse {team_choice} - {day_str}")
            active_final = final[final['speed_qph'] > 0]
            
            if not active_final.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Utilisation Moy.", f"{active_final['Utilization'].mean():.1f}%")
                c2.metric("Productivité Moy.", f"{active_final['Productivité'].mean():.1f}%")
                c3.metric("Heures Totales", f"{final['heures_totales'].sum():.1f}h")

                st.dataframe(active_final[["name", "Language", "heures_totales", "answered_sum", "speed_qph", "Utilization", "Productivité"]].sort_values("speed_qph", ascending=False), use_container_width=True)
            else:
                st.warning("Aucune donnée de vitesse trouvée pour cette équipe dans le CSV.")

        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")