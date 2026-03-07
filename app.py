import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import calendar
import ast
import os
import math
import bcrypt
import google.generativeai as genai
from PIL import Image
import json

# --- CONFIG & STYLE ---
st.set_page_config(page_title="Athlète OS", page_icon="logo.png", layout="wide")
if not os.path.exists("uploads"): os.makedirs("uploads")

st.markdown("""
    <style>
    /* 1. Police et design de base */
    body { font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #1A1A1D; padding: 15px; border-radius: 8px; border-left: 4px solid #4A90E2; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #E0E0E0; font-weight: 500; }
    hr { border-color: #333; }
    
    /* 2. MODE APPLICATION NATIVE (Masquer l'interface Streamlit) */
    #MainMenu {visibility: hidden;} /* Masque le menu hamburger en haut à droite */
    footer {visibility: hidden;} /* Masque le "Made with Streamlit" en bas */
    header {visibility: hidden;} /* Masque la barre supérieure (Deploy, etc.) */
    
    /* 3. OPTIMISATION SMARTPHONE */
    /* Empêche l'iPhone de zoomer automatiquement quand on tape dans une case */
    input[type="text"], input[type="number"], textarea {
        font-size: 16px !important;
    }
    /* Ajoute un peu de marge en haut pour éviter l'encoche/caméra du téléphone */
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION CLOUD & API IA ---
db_url = st.secrets["DATABASE_URL"]
engine = create_engine(db_url)
Base = declarative_base()

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_best_gemini_model():
    """Fonction Radar : Trouve automatiquement le modèle autorisé par Google"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # On cherche en priorité les modèles rapides et récents (qui font texte et image)
        for m in models:
            if 'flash' in m.lower() or 'pro' in m.lower():
                return m
        return models[0] if models else "gemini-1.5-flash"
    except:
        return "gemini-1.5-flash"

# --- TABLES AVEC USER_ID ---
class Utilisateur(Base):
    __tablename__ = 'utilisateurs'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)

class Seance(Base):
    __tablename__ = 'seances'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date = Column(Date)
    type_seance = Column(String)
    rpe = Column(Integer)
    duree = Column(Integer)
    exercices = Column(Text)
    intervalles = Column(Text)
    dist_totale = Column(Float)
    allure_moy = Column(String)
    fc_moy = Column(Integer)
    sommeil_heures = Column(Float)
    sommeil_qualite = Column(Integer)
    vfc = Column(Integer)
    fc_nocturne = Column(Integer)
    chaussures = Column(String)
    pre_check = Column(Text)
    image_fc = Column(String)

class Sante(Base):
    __tablename__ = 'sante'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date = Column(Date)
    poids = Column(Float)
    taille = Column(Float)
    cou = Column(Float)
    ventre = Column(Float)
    mg_estimee = Column(Float)
    calories = Column(Integer)
    proteines = Column(Integer)
    blessure_nom = Column(String)
    blessure_gravite = Column(Integer)
    note_sante = Column(Text)

class Planification(Base):
    __tablename__ = 'planification'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    date = Column(Date)
    titre = Column(String)
    description = Column(Text)
    statut = Column(String)

class RecordManuel(Base):
    __tablename__ = 'records_manuels'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    nom_exo = Column(String)
    valeur_1rm = Column(Float)
    
class FavorisCoach(Base):
    __tablename__ = 'favoris_coach'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    coach_id = Column(Integer)
    athlete_id = Column(Integer)
class Commentaire(Base):
    __tablename__ = 'commentaires'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True)
    seance_id = Column(Integer)
    texte = Column(Text)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db = Session()

# ==========================================
# SYSTEME D'AUTHENTIFICATION & BRANDING
# ==========================================
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)
else:
    st.sidebar.markdown("### 🧬 Athlète OS")

if 'user_id' not in st.session_state:
    st.title("Portail d'Accès")
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Se connecter")
        with st.form("login_form"):
            user_in = st.text_input("Identifiant")
            pwd_in = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Entrer"):
                u = db.query(Utilisateur).filter(Utilisateur.username == user_in).first()
                if u and bcrypt.checkpw(pwd_in.encode('utf-8'), u.password_hash.encode('utf-8')):
                    st.session_state.user_id = u.id
                    st.session_state.username = u.username
                    st.rerun()
                else: st.error("Identifiants incorrects.")
    with col2:
        st.subheader("Créer un compte")
        with st.form("register_form"):
            new_user = st.text_input("Nouvel Identifiant")
            new_pwd = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("S'inscrire"):
                if db.query(Utilisateur).filter(Utilisateur.username == new_user).first(): st.error("Identifiant pris.")
                elif len(new_pwd) < 4: st.warning("Mot de passe trop court.")
                else:
                    h_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db.add(Utilisateur(username=new_user, password_hash=h_pwd))
                    db.commit(); st.success("Compte créé ! Connecte-toi à gauche.")
    st.stop()

uid = st.session_state.user_id
st.sidebar.success(f"Pilote : **{st.session_state.username}**")
if st.sidebar.button("Déconnexion"):
    del st.session_state.user_id
    del st.session_state.username
    st.rerun()

# --- UTILS ---
def get_options_exos():
    res = db.query(Seance.exercices).filter(Seance.user_id == uid).all()
    noms = set()
    for r in res:
        if r[0] and r[0] not in ["None", "[]"]:
            try:
                for item in ast.literal_eval(r[0]): noms.add(item['nom'].strip().title())
            except: pass
    return sorted([n for n in noms if n])

def allure_to_sec(allure_str):
    try:
        if not allure_str or ":" not in allure_str: return 0
        m, s = map(int, allure_str.split(':'))
        return m * 60 + s
    except: return 0

def sec_to_allure(seconds):
    if seconds <= 0: return "00:00"
    m, s = int(seconds // 60), int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def sec_to_time_str(seconds):
    if seconds <= 0: return "00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0: return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"

def estimate_riegel(dist_ref, sec_ref, dist_cible):
    return sec_ref * (dist_cible / dist_ref)**1.06 if dist_ref > 0 else 0

def calc_body_fat(p, t, c, v):
    try: return 495 / (1.0324 - 0.19077 * (math.log10(v - c)) + 0.15456 * (math.log10(t))) - 450
    except: return 0

# --- INTERFACE ---
# --- DÉFINITION DES ONGLETS DYNAMIQUES ---
# Remplace "Lilian" par ton identifiant exact de connexion !
PSEUDO_COACH = "Lilian135lapuenta" 
is_coach = (st.session_state.username.lower() == PSEUDO_COACH.lower())

liste_onglets = ["Planification", "Saisie", "Santé", "Journal", "Analyses", "Records", "Bilan IA"]
if is_coach:
    liste_onglets.append("👑 Espace Coach")

tabs = st.tabs(liste_onglets)
today = datetime.now().date()
today = datetime.now().date()

# ==========================================
# ONGLET 0 : PLANIFICATION & IA COACH
# ==========================================
with tabs[0]: 
    col_p1, col_p2 = st.columns([2, 1])
    
    with col_p1:
        # --- 1. LE PLAN DU JOUR ---
        st.header("🎯 Plan du jour")
        plan_today = db.query(Planification).filter(Planification.date == today, Planification.user_id == uid).all()
        if plan_today:
            for p in plan_today:
                st.info(f"**{p.titre}**\n\n{p.description}")
                if st.button(f"✅ Marquer comme fait", key=f"done_{p.id}"):
                    db.query(Planification).filter(Planification.id == p.id).delete()
                    db.commit(); st.rerun()
        else: 
            st.success("Aucune séance programmée aujourd'hui. Repos ou improvisation !")

        st.divider()
        
        # --- 2. PROGRAMMER UNE SÉANCE ---
        st.subheader("➕ Programmer")
        with st.form("add_plan"):
            # J'ai mis 'today + 1 jour' par défaut, c'est plus logique pour planifier le futur
            p_date = st.date_input("Date", today + timedelta(days=1))
            p_titre = st.text_input("Titre de la séance")
            p_desc = st.text_area("Description / Objectifs")
            if st.form_submit_button("Ajouter au calendrier"):
                db.add(Planification(user_id=uid, date=p_date, titre=p_titre, description=p_desc, statut="Programmé"))
                db.commit(); st.success("Séance ajoutée !"); st.rerun()

        st.divider()
        
        # --- 3. TIMELINE DU CALENDRIER À VENIR ---
        st.subheader("📅 Prochaines Séances")
        # On récupère toutes les séances futures triées par date
        plan_futur = db.query(Planification).filter(Planification.date > today, Planification.user_id == uid).order_by(Planification.date.asc()).all()
        
        if plan_futur:
            jours_fr = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
            for p in plan_futur:
                # Formatage de la date (ex: "Mer 15/05")
                nom_jour = jours_fr[p.date.weekday()]
                date_str = f"{nom_jour} {p.date.strftime('%d/%m')}"
                
                # Utilisation d'un expander pour que ça reste compact sur téléphone
                with st.expander(f"**{date_str}** : {p.titre}", expanded=False):
                    st.write(p.description)
                    # Option pour annuler/supprimer une séance prévue
                    if st.button("🗑️ Annuler cette séance", key=f"del_plan_{p.id}"):
                        db.query(Planification).filter(Planification.id == p.id).delete()
                        db.commit(); st.rerun()
        else:
            st.info("Rien de prévu pour les prochains jours. C'est le moment de structurer ta semaine !")

with col_p2:
        st.subheader("🤖 Assistant IA")
        st.markdown("Générer une séance optimale basée sur tes 7 derniers jours.")
if st.button("Consulter l'IA", type="primary"):
            if "GEMINI_API_KEY" not in st.secrets:
                st.error("L'IA n'est pas activée. Ajoute ta GEMINI_API_KEY.")
            else:
                with st.spinner("Analyse de ta semaine en cours..."):
                    try:
                        # --- MODIFICATION ICI : On remonte 7 jours en arrière ---
                        sept_jours = today - timedelta(days=7)
                        recent_sessions = db.query(Seance).filter(Seance.user_id == uid, Seance.date >= sept_jours).order_by(Seance.date.asc()).all()
                        
                        if recent_sessions:
                            lignes_histo = []
                            for s in recent_sessions:
                                if s.type_seance == "Mesures":
                                    if s.sommeil_heures or s.vfc:
                                        lignes_histo.append(f"- {s.date.strftime('%d/%m')} : Nuit ({s.sommeil_heures}h sommeil, VFC {s.vfc}ms)")
                                else:
                                    lignes_histo.append(f"- {s.date.strftime('%d/%m')} : {s.type_seance} (Effort {s.rpe}/10, {s.duree} min)")
                            histo_txt = "\n".join(lignes_histo)
                        else:
                            histo_txt = "Aucune donnée sur les 7 derniers jours."
                        
                        auto_model_name = get_best_gemini_model()
                        model = genai.GenerativeModel(auto_model_name)
                        
                        prompt = f"Tu es un coach sportif d'élite. L'athlète te demande une séance aujourd'hui. Voici son historique de charge et de récupération des 7 derniers jours :\n{histo_txt}\n\nEn analysant cette semaine, propose-lui la meilleure séance possible aujourd'hui (course, force, cross-training ou repos total) en 3 ou 4 lignes maximum. Sois direct, précis et motivant."
                        response = model.generate_content(prompt)
                        st.success(f"(Modèle : {auto_model_name})\n\n{response.text}")
                        
                    except Exception as e:
                        st.error(f"Détail du blocage principal : {e}")
                        
                        # --- LE CAMELEON EST ICI (Bloc de Secours) ---
                        auto_model_name = get_best_gemini_model()
                        model = genai.GenerativeModel(auto_model_name)
                        
                        derniere_mesure = db.query(Seance).filter(Seance.user_id == uid, Seance.type_seance == "Mesures").order_by(Seance.date.desc()).first()
                        if derniere_mesure and derniere_mesure.vfc:
                            vfc_txt = f"VFC: {derniere_mesure.vfc} ms, Sommeil: {derniere_mesure.sommeil_heures}h"
                        else:
                            vfc_txt = "Pas de données VFC/Sommeil récentes."
                        
                        prompt_secours = f"Tu es un coach sportif d'élite. L'athlète te demande une séance aujourd'hui. Voici ses dernières constantes : {vfc_txt}. Propose-lui une seule séance courte et efficace (course ou force) adaptée à son état, en 3 lignes maximum. Sois direct et motivant."
                        
                        try:
                            response_secours = model.generate_content(prompt_secours)
                            st.success(f"(Modèle de secours : {auto_model_name})\n\n{response_secours.text}")
                        except Exception as e2:
                            st.error("L'IA est temporairement indisponible. Repose-toi ou fais un footing léger aujourd'hui ! 🏃‍♂️")
# ==========================================
# ONGLET 1 : SAISIE & GARMIN
# ==========================================
with tabs[1]: 
    tab_matin, tab_seance = st.tabs(["🌅 Matin", "🏋️ Entraînement"])
    
    with tab_matin:
        d_date_matin = st.date_input("Date", today, key="date_matin")
        exist_m = db.query(Seance).filter(Seance.date == d_date_matin, Seance.user_id == uid).first()
        def_slp = float(exist_m.sommeil_heures) if exist_m and exist_m.sommeil_heures else 7.5
        def_slp_q = int(exist_m.sommeil_qualite) if exist_m and exist_m.sommeil_qualite else 7
        def_vfc = int(exist_m.vfc) if exist_m and exist_m.vfc else 0
        def_fcn = int(exist_m.fc_nocturne) if exist_m and exist_m.fc_nocturne else 0
        
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            slp = st.number_input("Sommeil (h)", 0.0, 15.0, def_slp)
            slp_q = st.slider("Qualité (1-10)", 1, 10, def_slp_q)
        with c_m2:
            vfc = st.number_input("VFC (ms)", 0, 250, def_vfc)
            fcn = st.number_input("FC Repos", 0, 150, def_fcn)
            
        if st.button("Sauvegarder la nuit", type="primary"):
            if exist_m:
                db.query(Seance).filter(Seance.date == d_date_matin, Seance.user_id == uid).update({"sommeil_heures": slp, "sommeil_qualite": slp_q, "vfc": vfc, "fc_nocturne": fcn})
            else:
                db.add(Seance(user_id=uid, date=d_date_matin, type_seance="Mesures", rpe=0, duree=0, sommeil_heures=slp, sommeil_qualite=slp_q, vfc=vfc, fc_nocturne=fcn))
            db.commit(); st.success("Enregistré ✅")

    with tab_seance:
        mode = st.radio("Modalité", ["Force", "Hyrox", "Course", "Cross-Training", "Repos"], horizontal=True)
        d_date_ent = st.date_input("Date de séance", today, key="date_ent")
        current_exos, dist_tot, allure_m, shoe, fc_moy = [], 0.0, "00:00", None, 0
        
        if mode != "Repos":
            c_r1, c_r2 = st.columns(2)
            rpe = c_r1.slider("RPE (Effort 1-10)", 1, 10, 5)
            dur = c_r2.number_input("Durée (min)", 0, 480, 60, key="dur_input")
            
            if mode == "Course":
                with st.expander("⌚ Importer depuis Garmin (Photo)", expanded=False):
                    uploaded_file = st.file_uploader("Capture d'écran Garmin", type=["jpg", "jpeg", "png"])
                    if uploaded_file is not None:
                        if st.button("Analyser l'image avec l'IA"):
                            if "GEMINI_API_KEY" not in st.secrets:
                                st.error("Ajoute ta clé GEMINI_API_KEY.")
                            else:
                                with st.spinner("Lecture des données en cours..."):
                                    try:
                                        img = Image.open(uploaded_file)
                                        # --- LE CAMELEON EST ICI AUSSI ---
                                        auto_model_name = get_best_gemini_model()
                                        model = genai.GenerativeModel(auto_model_name)
                                        
                                        prompt = "Analyse cette image d'une application de course (Garmin/Strava). Renvoie uniquement un format JSON strict avec ces clés exactes : 'distance' (float, en km), 'duree' (int, en minutes totales), 'allure' (string, format MM:SS), 'fc_moyenne' (int, battements par minute). Ne mets aucun autre texte."
                                        response = model.generate_content([prompt, img])
                                        txt = response.text.replace("```json", "").replace("```", "").strip()
                                        data_ia = json.loads(txt)
                                        st.success(f"Données extraites avec succès ! (Modèle: {auto_model_name})")
                                        st.write(f"📏 Distance: {data_ia.get('distance')} km | ⏱️ Durée: {data_ia.get('duree')} min | 🏃 Allure: {data_ia.get('allure')} | ❤️ FC: {data_ia.get('fc_moyenne')} bpm")
                                        st.info("Copie ces valeurs dans les cases ci-dessous 👇")
                                    except Exception as e:
                                        st.error(f"Détail du blocage : {e}")

                c_c1, c_c2 = st.columns(2)
                dist_tot = c_c1.number_input("Distance (km)", 0.0)
                allure_m = c_c2.text_input("Allure (min:sec)", "05:00")
                fc_moy = c_c1.number_input("FC Moyenne", 0, 220, 0)
                
            elif mode == "Cross-Training":
                st.markdown("### Détails du WOD")
                c_ct1, c_ct2 = st.columns(2)
                wod_format = c_ct1.selectbox("Format", ["AMRAP", "EMOM", "FOR TIME", "TABATA", "CHIPPER", "AUTRE"])
                wod_score = c_ct2.text_input("Score (Temps, Tours, Reps...)", placeholder="ex: 4 tours + 10 reps")
                st.session_state.blks = [{'format': wod_format, 'score': wod_score}]
                
                st.markdown("Mouvements inclus (optionnel)")
                nb = st.number_input("Nombre d'exos", 0, 20, 1)
                for i in range(nb):
                    cols = st.columns([3, 2, 1, 1, 1])
                    nom = cols[0].selectbox(f"Mouvement {i+1}", [""] + get_options_exos() + ["+ Saisir nouveau"], key=f"ct_nom_{i}")
                    if nom == "+ Saisir nouveau": nom = cols[0].text_input(f"Nouveau", key=f"ct_new_{i}")
                    grp = cols[1].selectbox("Muscle", ["Full Body", "Jambes", "Dos", "Pecs", "Epaules", "Bras"], key=f"ct_grp_{i}")
                    p = cols[4].number_input("Charge", 0.0, key=f"ct_p_{i}")
                    if nom: current_exos.append({"nom": nom.strip().title(), "groupe": grp, "s": 1, "r": 0, "p": p})

            elif mode in ["Force", "Hyrox"]:
                nb = st.number_input("Nombre d'exercices", 1, 20, 1)
                for i in range(nb):
                    cols = st.columns([3, 2, 1, 1, 1])
                    nom = cols[0].selectbox(f"Mouvement {i+1}", [""] + get_options_exos() + ["+ Saisir nouveau"], key=f"force_nom_{i}")
                    if nom == "+ Saisir nouveau": nom = cols[0].text_input(f"Nouveau", key=f"force_new_{i}")
                    grp = cols[1].selectbox("Muscle", ["Jambes", "Dos", "Pecs", "Epaules", "Bras", "Full Body"], key=f"force_grp_{i}")
                    s = cols[2].number_input("Séries", 0, key=f"force_s_{i}")
                    r = cols[3].number_input("Reps", 0, key=f"force_r_{i}")
                    p = cols[4].number_input("Charge", 0.0, key=f"force_p_{i}")
                    if nom: current_exos.append({"nom": nom.strip().title(), "groupe": grp, "s": s, "r": r, "p": p})
        else:
            rpe, dur = 0, 0
            st.info("Jour de repos complet sélectionné.")

        if st.button("Enregistrer ma séance", type="primary"):
            base = db.query(Seance).filter(Seance.date == d_date_ent, Seance.user_id == uid).first()
            i_slp = base.sommeil_heures if base else 0.0
            i_slpq = base.sommeil_qualite if base else 0
            i_vfc = base.vfc if base else 0
            i_fcn = base.fc_nocturne if base else 0
            inter = str(st.session_state.get('blks', [])) if mode == "Cross-Training" else "[]"
            
            db.add(Seance(user_id=uid, date=d_date_ent, type_seance=mode, rpe=rpe, duree=dur, 
                          exercices=str(current_exos), intervalles=inter, dist_totale=dist_tot, allure_moy=allure_m, fc_moy=fc_moy,
                          sommeil_heures=i_slp, sommeil_qualite=i_slpq, vfc=i_vfc, fc_nocturne=i_fcn))
            db.commit(); st.session_state.blks = []; st.success("Séance sauvegardée ! ✅"); st.rerun()

# ==========================================
# ONGLET 2 : SANTÉ
# ==========================================
with tabs[2]: 
    st.subheader("Carnet de Santé")
    h_date = st.date_input("Date de la mesure", today, key="date_sante")
    exist_s = db.query(Sante).filter(Sante.date == h_date, Sante.user_id == uid).first()
    
    with st.expander("⚖️ Poids & Mensurations", expanded=True):
        with st.form("form_mensurations"):
            c1, c2 = st.columns(2)
            h_poids = c1.number_input("Poids (kg)", 0.0, 200.0, float(exist_s.poids) if exist_s and exist_s.poids else 0.0)
            h_taille = c2.number_input("Taille (cm)", 0.0, 250.0, float(exist_s.taille) if exist_s and exist_s.taille else 0.0)
            h_ventre = c1.number_input("Ventre (cm)", 0.0, 200.0, float(exist_s.ventre) if exist_s and exist_s.ventre else 0.0)
            h_cou = c2.number_input("Cou (cm)", 0.0, 100.0, float(exist_s.cou) if exist_s and exist_s.cou else 0.0)
            if st.form_submit_button("Valider Mensurations"):
                mg = calc_body_fat(h_poids, h_taille, h_cou, h_ventre) if h_poids>0 and h_taille>0 and h_ventre>0 and h_cou>0 else None
                if exist_s: db.query(Sante).filter(Sante.id == exist_s.id).update({"poids": h_poids or None, "taille": h_taille or None, "ventre": h_ventre or None, "cou": h_cou or None, "mg_estimee": mg})
                else: db.add(Sante(user_id=uid, date=h_date, poids=h_poids or None, taille=h_taille or None, ventre=h_ventre or None, cou=h_cou or None, mg_estimee=mg))
                db.commit(); st.rerun()

    with st.expander("🍎 Nutrition journalière"):
        with st.form("form_nutrition"):
            c3, c4 = st.columns(2)
            h_cal = c3.number_input("Calories (kcal)", 0, 10000, int(exist_s.calories) if exist_s and exist_s.calories else 0)
            h_prot = c4.number_input("Protéines (g)", 0, 500, int(exist_s.proteines) if exist_s and exist_s.proteines else 0)
            if st.form_submit_button("Valider Nutrition"):
                if exist_s: db.query(Sante).filter(Sante.id == exist_s.id).update({"calories": h_cal or None, "proteines": h_prot or None})
                else: db.add(Sante(user_id=uid, date=h_date, calories=h_cal or None, proteines=h_prot or None))
                db.commit(); st.rerun()

    with st.expander("🩹 Suivi des Douleurs"):
        with st.form("form_blessures"):
            bless_list = ["Aucune", "Genou", "Bas du dos", "Epaule", "Cheville", "Ischios", "Autre"]
            idx_b = bless_list.index(exist_s.blessure_nom) if exist_s and exist_s.blessure_nom in bless_list else 0
            h_bless = st.selectbox("Localisation", bless_list, index=idx_b)
            h_grav = st.slider("Douleur (0-10)", 0, 10, int(exist_s.blessure_gravite) if exist_s and exist_s.blessure_gravite else 0)
            if st.form_submit_button("Valider Douleur"):
                if exist_s: db.query(Sante).filter(Sante.id == exist_s.id).update({"blessure_nom": h_bless, "blessure_gravite": h_grav})
                else: db.add(Sante(user_id=uid, date=h_date, blessure_nom=h_bless, blessure_gravite=h_grav))
                db.commit(); st.rerun()

# ==========================================
# ONGLET 3 : JOURNAL (OPTIMISÉ MOBILE)
# ==========================================
with tabs[3]: 
    if 'sel_date' not in st.session_state: st.session_state.sel_date = today

    # --- 1. NAVIGATION COMPACTE ---
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    if col_nav1.button("◀", use_container_width=True):
        st.session_state.sel_date -= timedelta(days=1)
        st.rerun()
        
    with col_nav2:
        new_date = st.date_input("Date", st.session_state.sel_date, label_visibility="collapsed")
        if new_date != st.session_state.sel_date:
            st.session_state.sel_date = new_date
            st.rerun()
            
    if col_nav3.button("▶", use_container_width=True):
        st.session_state.sel_date += timedelta(days=1)
        st.rerun()

    jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    nom_jour = jours_fr[st.session_state.sel_date.weekday()]
    st.markdown(f"<h3 style='text-align: center; color: #4A90E2;'>{nom_jour} {st.session_state.sel_date.strftime('%d/%m/%Y')}</h3>", unsafe_allow_html=True)
    st.divider()

    # --- 2. DÉTAILS DU JOUR ---
    s_detail = db.query(Seance).filter(Seance.date == st.session_state.sel_date, Seance.user_id == uid).all()
    
    if s_detail:
        # Santé et Sommeil
        has_health = any(s.sommeil_heures > 0 or s.vfc > 0 for s in s_detail)
        if has_health:
            h = max(s_detail, key=lambda s: s.sommeil_heures)
            st.markdown("#### 🌙 État de Forme")
            # Un seul bloc compact au lieu de 3 colonnes pour éviter les bugs d'affichage mobile
            st.info(f"**Sommeil:** {h.sommeil_heures}h ({h.sommeil_qualite}/10) | **VFC:** {h.vfc} ms | **FC Repos:** {h.fc_nocturne} bpm")

        # Entraînements
        for row in s_detail:
            if row.type_seance == "Mesures": continue 
            
            with st.container():
                st.markdown(f"#### 🏃 {row.type_seance}")
                st.write(f"**Effort (RPE):** {row.rpe}/10 | **Durée:** {row.duree} min")
                
                if row.type_seance == "Course":
                    st.write(f"**Distance:** {row.dist_totale} km à {row.allure_moy} min/km")
                elif row.type_seance == "Cross-Training" and row.intervalles and row.intervalles != "[]":
                    try:
                        wod_data = ast.literal_eval(row.intervalles)[0]
                        st.write(f"**WOD {wod_data.get('format', '')}** : {wod_data.get('score', '')}")
                    except: pass
                
                if row.exercices and row.exercices not in ["[]", "None"]:
                    try:
                        for ex in ast.literal_eval(row.exercices):
                            if ex.get('s', 0) > 0: 
                                st.markdown(f"- **{ex.get('nom','')}** : {ex.get('s',0)}x{ex.get('r',0)} @ {ex.get('p',0)}kg")
                            else: 
                                st.markdown(f"- **{ex.get('nom','')}** @ {ex.get('p',0)}kg")
                    except: pass
                
                if st.button("🗑️ Supprimer", key=f"del_{row.id}", type="secondary"):
                    db.query(Seance).filter(Seance.id == row.id).delete()
                    db.commit(); st.rerun()
                
                # --- AFFICHAGE DU DEBRIEF COACH ---
                # On vérifie si un commentaire existe pour cette séance
                commentaire_coach = db.query(Commentaire).filter(Commentaire.seance_id == row.id).first()
                if commentaire_coach and commentaire_coach.texte:
                    st.info(f"👑 **Debrief de Coach Lilian :**\n\n{commentaire_coach.texte}")
                    
                st.markdown("---")
        
    # --- 3. FIL D'ACTUALITÉ (Historique récent) ---
    st.subheader("🔄 Dernières Activités")
    recent_days = today - timedelta(days=30)
    historique = db.query(Seance).filter(Seance.user_id == uid, Seance.date >= recent_days, Seance.type_seance != "Mesures").order_by(Seance.date.desc()).all()
    
    if historique:
        # On affiche uniquement les 5 dernières activités pour ne pas saturer l'écran
        for s in historique[:5]:
            jours_courts = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
            date_str = f"{jours_courts[s.date.weekday()]} {s.date.strftime('%d/%m')}"
            titre = f"**{date_str}** - {s.type_seance}"
            resume = f"{s.duree} min"
            if s.type_seance == "Course": resume += f" | {s.dist_totale} km"
            elif s.type_seance in ["Force", "Hyrox", "Cross-Training"]: resume += f" | RPE {s.rpe}"
            
            # Ce bouton sert de raccourci : on clique, on voyage dans le temps jusqu'à ce jour !
            if st.button(f"🔍 {titre} ({resume})", key=f"hist_{s.id}", use_container_width=True):
                st.session_state.sel_date = s.date
                st.rerun()
    else:
        st.caption("Aucune activité récente à afficher.")
# ==========================================
# ONGLET 4 : ANALYSES (OPTIMISÉ MOBILE)
# ==========================================
with tabs[4]: 
    df_c = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid}", engine)
    if not df_c.empty:
        df_c['date'] = pd.to_datetime(df_c['date'])
        
        st.subheader("Analyse du Sommeil")
        df_sleep = df_c[df_c['sommeil_heures'] > 0].groupby('date').max().reset_index().sort_values('date')
        if not df_sleep.empty:
            fig_sleep = make_subplots(specs=[[{"secondary_y": True}]])
            fig_sleep.add_trace(go.Bar(x=df_sleep['date'], y=df_sleep['sommeil_heures'], name="Heures", marker_color="#3A506B"), secondary_y=False)
            fig_sleep.add_trace(go.Scatter(x=df_sleep['date'], y=df_sleep['sommeil_qualite'], name="Qualité", mode='lines+markers', line=dict(color="#5BC0BE")), secondary_y=True)
            fig_sleep.add_hrect(y0=7, y1=9, fillcolor="green", opacity=0.15, layer="below", line_width=0, secondary_y=False)
            fig_sleep.update_layout(template="plotly_dark", margin=dict(t=30, b=0), legend=dict(orientation="h", y=-0.3, x=0))
            st.plotly_chart(fig_sleep, use_container_width=True)

        st.divider()
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.subheader("Ratio de Charge ACWR")
            df_efforts = df_c[df_c['type_seance'] != "Mesures"].copy()
            df_efforts['charge'] = df_efforts['rpe'] * df_efforts['duree']
            daily = df_efforts.groupby('date')['charge'].sum().reset_index()
            daily['aigu'] = daily['charge'].rolling(7, min_periods=1).mean()
            daily['chronique'] = daily['charge'].rolling(28, min_periods=1).mean()
            daily['acwr'] = daily['aigu'] / daily['chronique']
            fig_acwr = go.Figure()
            fig_acwr.add_trace(go.Scatter(x=daily['date'], y=daily['acwr'], name="ACWR", line=dict(color='#E53935'), mode='lines+markers'))
            fig_acwr.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.15, layer="below", line_width=0)
            fig_acwr.update_layout(template="plotly_dark", margin=dict(t=30, b=0), legend=dict(orientation="h", y=-0.3, x=0))
            st.plotly_chart(fig_acwr, use_container_width=True)
            
            st.subheader("Distribution (80/20)")
            low_int = df_efforts[df_efforts['rpe'] <= 4]['duree'].sum()
            high_int = df_efforts[df_efforts['rpe'] > 4]['duree'].sum()
            if low_int > 0 or high_int > 0:
                fig_pie = px.pie(values=[low_int, high_int], names=['Z1-Z2', 'Z3+'], color_discrete_sequence=['#4A90E2', '#E53935'])
                fig_pie.update_layout(template="plotly_dark", margin=dict(t=30, b=0), legend=dict(orientation="h", y=-0.3, x=0))
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_d2:
            st.subheader("Efficacité Aérobie")
            df_run = df_c[(df_c['type_seance'] == "Course") & (df_c['fc_moy'] > 0)].copy()
            if not df_run.empty:
                df_run['allure_sec'] = df_run['allure_moy'].apply(allure_to_sec)
                df_run['vitesse_kmh'] = df_run['allure_sec'].apply(lambda x: 3600/x if x > 0 else 0)
                df_run['efficiency'] = df_run.apply(lambda r: r['vitesse_kmh'] / r['fc_moy'] if r['fc_moy'] > 0 else 0, axis=1)
                fig_eff = px.line(df_run[df_run['efficiency'] > 0], x='date', y='efficiency', markers=True)
                fig_eff.update_layout(template="plotly_dark", margin=dict(t=30, b=0), legend=dict(orientation="h", y=-0.3, x=0))
                st.plotly_chart(fig_eff, use_container_width=True)
                
            st.subheader("Distribution du Tonnage")
            t_list = []
            for ex_str in df_c['exercices'].dropna():
                if ex_str != "[]" and ex_str != "None":
                    try:
                        for ex in ast.literal_eval(ex_str): t_list.append({"groupe": ex.get('groupe', 'Autre'), "volume": ex.get('s',0)*ex.get('r',0)*ex.get('p',0)})
                    except: pass
            if t_list:
                df_t = pd.DataFrame(t_list).groupby('groupe').sum().reset_index()
                fig_t = px.bar(df_t, x='groupe', y='volume', color='groupe', template="plotly_dark")
                fig_t.update_layout(legend=dict(orientation="h", y=-0.3, x=0))
                st.plotly_chart(fig_t, use_container_width=True)

# ==========================================
# ONGLET 5 : RECORDS
# ==========================================
with tabs[5]: 
    df_r = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid}", engine)
    
    # -------------------------------------------
    # SECTION 1 : RECORDS DE COURSE
    # -------------------------------------------
    st.subheader("🏃‍♂️ Records Course à Pied")
    col_rc1, col_rc2 = st.columns([2, 1])
    
    with col_rc2:
        with st.expander("⏱️ Ajouter un chrono officiel", expanded=False):
            with st.form("add_manual_run_pr"):
                r_dist = st.selectbox("Distance", ["1 km", "5 km", "10 km", "Semi-Marathon", "Marathon"])
                r_time = st.text_input("Temps", placeholder="ex: 45:30 ou 1:45:30")
                if st.form_submit_button("Valider"):
                    try:
                        parts = r_time.strip().split(':')
                        if len(parts) == 2: 
                            secs = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3: 
                            secs = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                        else: 
                            secs = 0
                        
                        if secs > 0:
                            nom_record = f"Course: {r_dist}"
                            db.query(RecordManuel).filter(RecordManuel.nom_exo == nom_record, RecordManuel.user_id == uid).delete()
                            db.add(RecordManuel(user_id=uid, nom_exo=nom_record, valeur_1rm=float(secs)))
                            db.commit()
                            st.rerun()
                        else: 
                            st.error("Format de temps invalide.")
                    except: 
                        st.error("Format requis : MM:SS ou HH:MM:SS")

    with col_rc1:
        manuels_course = pd.read_sql(f"SELECT * FROM records_manuels WHERE user_id = {uid} AND nom_exo LIKE 'Course: %%'", engine)
        dict_manuels_course = {row['nom_exo'].replace("Course: ", ""): row['valeur_1rm'] for _, row in manuels_course.iterrows()}
        
        df_run = df_r[(df_r['type_seance'] == "Course") & (df_r['dist_totale'] >= 1.0)].copy()
        best_perf = None
        if not df_run.empty:
            df_run['sec_km'] = df_run['allure_moy'].apply(allure_to_sec)
            df_run['sec_tot'] = df_run['sec_km'] * df_run['dist_totale']
            df_run_valide = df_run[df_run['sec_tot'] > 0].copy()
            
            if not df_run_valide.empty:
                df_run_valide['score_10k'] = df_run_valide.apply(lambda r: estimate_riegel(r['dist_totale'], r['sec_tot'], 10.0), axis=1)
                best_perf = df_run_valide.loc[df_run_valide['score_10k'].idxmin()]
                st.caption(f"💡 Base des estimations : {best_perf['dist_totale']} km à {best_perf['allure_moy']} min/km")
        
        targets_map = {"1 km": 1, "5 km": 5, "10 km": 10, "Semi-Marathon": 21.1, "Marathon": 42.2}
        cols_run = st.columns(5)
        
        for i, (nom_dist, dist_km) in enumerate(targets_map.items()):
            best_officiel = dict_manuels_course.get(nom_dist, float('inf'))
            date_record = None
            
            if not df_run.empty:
                runs_couvrant_distance = df_run[df_run['dist_totale'] >= dist_km]
                if not runs_couvrant_distance.empty:
                    # On cherche la course avec le meilleur passage
                    meilleur_run = runs_couvrant_distance.loc[(runs_couvrant_distance['sec_km'] * dist_km).idxmin()]
                    meilleur_passage = meilleur_run['sec_km'] * dist_km
                    if meilleur_passage < best_officiel:
                        best_officiel = meilleur_passage
                        date_record = meilleur_run['date'] # On sauvegarde la date !
            
            if best_officiel != float('inf'):
                val_sec = best_officiel
                source = "Officiel 🏅"
            elif best_perf is not None:
                val_sec = estimate_riegel(best_perf['dist_totale'], best_perf['sec_tot'], dist_km)
                source = "Estimé 🤖"
                date_record = best_perf['date'] # Date de la course qui sert de base
            else:
                val_sec = 0
                source = "-"
                
            temps_str = sec_to_time_str(val_sec) if val_sec > 0 else "N/A"
            
            with cols_run[i]:
                st.metric(nom_dist, temps_str, source, delta_color="off")
                if date_record is not None:
                    # Nettoyage de la date et rechargement forcé
                    if st.button(f"🔍 {pd.to_datetime(date_record).strftime('%d/%m/%Y')}", key=f"btn_run_{nom_dist}"):
                        st.session_state.sel_date = pd.to_datetime(date_record).date()
                        st.rerun()

    # -------------------------------------------
    # SECTION 2 : RECORDS DE FORCE
    # -------------------------------------------
    st.subheader("🏋️‍♂️ Performances Maximales (Force)")
    col_rf1, col_rf2 = st.columns([2, 1])
    
    with col_rf2:
        with st.expander("⚖️ Calibrage manuel 1RM", expanded=False):
            with st.form("add_manual_pr"):
                m_exo = st.selectbox("Mouvement", [""] + get_options_exos())
                m_val = st.number_input("Valeur (kg)", 0.0)
                if st.form_submit_button("Sauvegarder"):
                    if m_exo and m_val > 0:
                        db.query(RecordManuel).filter(RecordManuel.nom_exo == m_exo, RecordManuel.user_id == uid).delete()
                        db.add(RecordManuel(user_id=uid, nom_exo=m_exo, valeur_1rm=m_val))
                        db.commit()
                        st.rerun()
                        
    with col_rf1:
        manuels_force = pd.read_sql(f"SELECT * FROM records_manuels WHERE user_id = {uid} AND nom_exo NOT LIKE 'Course: %%'", engine)
        dict_manuels_force = {row['nom_exo']: row['valeur_1rm'] for _, row in manuels_force.iterrows()}
        
        all_exos = []
        if not df_r.empty:
            for _, row in df_r.iterrows():
                ex_str = row['exercices']
                if pd.notna(ex_str) and ex_str not in ["None", "[]"]:
                    try: 
                        for ex in ast.literal_eval(ex_str):
                            if ex.get('p', 0) > 0 and ex.get('r', 0) > 0:
                                ex['nom'] = ex.get('nom', '').strip().title()
                                ex['date'] = row['date'] # On conserve la date de la séance
                                all_exos.append(ex)
                    except: pass
                    
        best_pr_dict = {}
        for exo, val in dict_manuels_force.items():
            best_pr_dict[exo] = {'1RM': val, 'source': 'Officiel 🏅', 'date': None}
            
        for ex in all_exos:
            nom = ex['nom']
            p = float(ex['p'])
            r = int(ex['r'])
            date_perf = ex['date']
            
            calc_1rm = p * (36 / (37 - r)) if r < 37 else p
            source = "Officiel 🏅" if r == 1 else "Estimé 🤖"
            
            if nom not in best_pr_dict or calc_1rm > best_pr_dict[nom]['1RM']:
                best_pr_dict[nom] = {'1RM': calc_1rm, 'source': source, 'date': date_perf}
            elif calc_1rm == best_pr_dict[nom]['1RM'] and source == "Officiel 🏅":
                best_pr_dict[nom]['source'] = "Officiel 🏅"
                best_pr_dict[nom]['date'] = date_perf

        if best_pr_dict:
            sorted_prs = sorted(best_pr_dict.items(), key=lambda x: x[1]['1RM'], reverse=True)
            
            c_pr = st.columns(3)
            for idx, (exo, data) in enumerate(sorted_prs):
                with c_pr[idx % 3]:
                    st.metric(f"{exo}", f"{int(data['1RM'])} kg", data['source'], delta_color="off")
                    if data.get('date'):
                        if st.button(f"🔍 {pd.to_datetime(data['date']).strftime('%d/%m/%Y')}", key=f"btn_force_{exo}"):
                            st.session_state.sel_date = pd.to_datetime(data['date']).date()
                            st.rerun()
        else:
            st.info("Aucune donnée de musculation enregistrée.")

# ==========================================
# ONGLET 6 : BILAN IA & EXPORT PDF
# ==========================================
with tabs[6]:
    st.subheader("📊 Générateur de Rapport & Bilan IA")
    
    # 1. Sélection de la période
    periode = st.selectbox("Choisir la période d'analyse :", ["7 derniers jours", "30 derniers jours", "Cette année"])
    
    if st.button("Générer le Bilan", type="primary"):
        # Calcul des dates
        if periode == "7 derniers jours":
            date_debut = today - timedelta(days=7)
        elif periode == "30 derniers jours":
            date_debut = today - timedelta(days=30)
        else:
            date_debut = today.replace(month=1, day=1)
            
        # Récupération des données
        df_b = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid} AND date >= '{date_debut}'", engine)
        
        if df_b.empty:
            st.warning("Aucune donnée sur cette période pour générer un bilan.")
        else:
            df_b['date'] = pd.to_datetime(df_b['date'])
            
            # --- ZONE IMPRIMABLE ---
            st.markdown("---")
            st.markdown(f"<h2 style='text-align: center;'>Bilan de Performance : {periode}</h2>", unsafe_allow_html=True)
            # --- AJOUT DES NOMS ICI ---
            st.markdown(f"<h4 style='text-align: center; color: #4A90E2;'>Athlète : {st.session_state.username.upper()} | Coach : LILIAN</h4>", unsafe_allow_html=True)
            st.write("") # Petit espace
            
            # 2. Les Chiffres Clés (Améliorés)
            st.markdown("### 📈 Indicateurs de Performance")
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            c_k5, c_k6, c_k7, c_k8 = st.columns(4)
            
            # -- Calculs de base --
            tot_dist = df_b['dist_totale'].sum()
            tot_dur = df_b['duree'].sum() / 60 # en heures
            moy_slp = df_b[df_b['sommeil_heures'] > 0]['sommeil_heures'].mean()
            moy_slp = moy_slp if pd.notna(moy_slp) else 0
            moy_vfc = df_b[df_b['vfc'] > 0]['vfc'].mean()
            moy_vfc = moy_vfc if pd.notna(moy_vfc) else 0
            
            # -- NOUVEAUX CALCULS DE PERFORMANCE --
            # Charge Totale et Intensité
            df_efforts = df_b[df_b['type_seance'] != "Mesures"].copy()
            if not df_efforts.empty:
                df_efforts['charge'] = df_efforts['rpe'] * df_efforts['duree']
                charge_totale = df_efforts['charge'].sum()
                rpe_moyen = df_efforts['rpe'].mean()
            else:
                charge_totale, rpe_moyen = 0, 0

            # Tonnage Total (Volume de force)
            tonnage_total = 0
            for ex_str in df_b['exercices'].dropna():
                if ex_str not in ["[]", "None"]:
                    try:
                        for ex in ast.literal_eval(ex_str):
                            tonnage_total += ex.get('s', 0) * ex.get('r', 0) * ex.get('p', 0)
                    except: pass
                    
            # Allure Moyenne Course (Pondérée)
            df_run = df_b[(df_b['type_seance'] == "Course") & (df_b['dist_totale'] > 0)].copy()
            allure_moy_globale = "00:00"
            if not df_run.empty:
                df_run['sec_tot'] = df_run['allure_moy'].apply(allure_to_sec) * df_run['dist_totale']
                sec_moy_km = df_run['sec_tot'].sum() / df_run['dist_totale'].sum()
                allure_moy_globale = sec_to_allure(sec_moy_km)

            # -- Affichage dans les colonnes --
            c_k1.metric("Volume Global", f"{tot_dur:.1f} h")
            c_k2.metric("Distance Course", f"{tot_dist:.1f} km")
            c_k3.metric("Tonnage Soulevé", f"{tonnage_total/1000:.1f} t" if tonnage_total > 0 else "0 t")
            c_k4.metric("Charge Cumulée", f"{int(charge_totale)} pts")
            
            c_k5.metric("Sommeil Moyen", f"{moy_slp:.1f} h")
            c_k6.metric("VFC Moyenne", f"{moy_vfc:.0f} ms")
            c_k7.metric("Allure Moy. Course", f"{allure_moy_globale} /km")
            c_k8.metric("Intensité Moy. (RPE)", f"{rpe_moyen:.1f} /10")
            
            # 3. Graphique de Charge
            st.markdown("---")
            st.markdown("### Évolution de la Charge (RPE x Durée)")
            if not df_efforts.empty:
                fig_charge = px.bar(df_efforts, x='date', y='charge', color='type_seance', template="plotly_dark")
                fig_charge.update_layout(margin=dict(t=10, b=0), legend=dict(orientation="h", y=-0.3, x=0))
                st.plotly_chart(fig_charge, use_container_width=True)
            else:
                st.info("Pas d'entraînements enregistrés sur cette période.")

            # 4. Analyse IA PERSONNALISÉE avec les nouvelles metrics
            st.markdown("### 🤖 Analyse du Coach Lilian")
            if "GEMINI_API_KEY" not in st.secrets:
                st.error("Ajoute ta clé GEMINI_API_KEY pour générer l'analyse.")
            else:
                with st.spinner("Rédaction du rapport par l'IA en cours..."):
                    try:
                        # LE NOUVEAU RÉSUMÉ ULTRA COMPLET POUR L'IA
                        resume_txt = f"Volume global: {tot_dur:.1f}h. Distance: {tot_dist:.1f}km (Allure moy: {allure_moy_globale}/km). Tonnage force: {tonnage_total}kg. Charge cumulée: {int(charge_totale)} pts (RPE moy: {rpe_moyen:.1f}/10). Sommeil moy: {moy_slp:.1f}h. VFC moy: {moy_vfc:.0f}ms."
                        
                        auto_model_name = get_best_gemini_model()
                        model = genai.GenerativeModel(auto_model_name)
                        
                        prompt = f"Tu es Lilian, un coach sportif expert de haut niveau. Tu t'adresses directement à ton athlète qui s'appelle '{st.session_state.username}'. Analyse son bilan pour la période '{periode}'. Voici ses données brutes : {resume_txt}. Rédige un rapport professionnel en 3 parties courtes et impactantes : 1) Analyse de la charge de travail et du volume (note bien ses allures et son tonnage s'il y en a), 2) État de récupération, 3) Recommandations pour le prochain cycle. Tu dois l'appeler par son prénom, utiliser un ton pro mais motivant, et signer par 'Coach Lilian'. Utilise du gras pour les points clés."
                        
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"Détail du blocage IA : {e}")
            # 5. Bouton Impression Web
            st.markdown("---")
            import streamlit.components.v1 as components
            components.html(
                """
                <div style="text-align: center;">
                    <button onclick="window.print()" style="background-color: #4A90E2; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; font-family: sans-serif; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        🖨️ Sauvegarder le Rapport en PDF
                    </button>
                    <p style="color: gray; font-size: 12px; margin-top: 10px; font-family: sans-serif;">Astuce : Dans la fenêtre d'impression, choisissez la destination "Enregistrer au format PDF" et désactivez "En-têtes et pieds de page" pour un rendu parfait.</p>
                </div>
                """,
                height=100
            )

# ==========================================
# ONGLET 8 : ESPACE COACH (ACCÈS RESTREINT)
# ==========================================
if is_coach:
    with tabs[7]:
        st.header("Supervision des Athlètes")
        
        # 1. Récupération des données
        tous_utilisateurs = db.query(Utilisateur).filter(Utilisateur.id != uid).all()
        mes_favoris = [f.athlete_id for f in db.query(FavorisCoach).filter(FavorisCoach.coach_id == uid).all()]
        
        # 2. Interface de Recherche et Filtre
        col_rech, col_filt = st.columns([3, 1])
        recherche = col_rech.text_input("🔍 Rechercher un athlète par pseudo...")
        filtre_fav = col_filt.checkbox("⭐ Favoris uniquement")
        
        # Filtrage de la liste
        utilisateurs_affiches = []
        for u in tous_utilisateurs:
            match_nom = recherche.lower() in u.username.lower()
            match_fav = (u.id in mes_favoris) if filtre_fav else True
            if match_nom and match_fav:
                utilisateurs_affiches.append(u)
                
        # 3. Affichage de la liste et sélection
        st.markdown("---")
        if not utilisateurs_affiches:
            st.info("Aucun athlète trouvé.")
        else:
            # On utilise les colonnes pour faire une belle liste de sélection
            c_liste, c_data = st.columns([1, 2])
            
            with c_liste:
                st.subheader("👥 Liste")
                # On utilise le session_state pour mémoriser l'athlète cliqué
                if 'selected_athlete_id' not in st.session_state:
                    st.session_state.selected_athlete_id = None
                    
                for u in utilisateurs_affiches:
                    is_fav = u.id in mes_favoris
                    icon_fav = "⭐" if is_fav else "☆"
                    
                    c_btn1, c_btn2 = st.columns([4, 1])
                    # Bouton pour voir l'athlète
                    if c_btn1.button(f"👤 {u.username}", key=f"voir_{u.id}", use_container_width=True):
                        st.session_state.selected_athlete_id = u.id
                    
                    # Bouton pour ajouter/retirer des favoris
                    if c_btn2.button(icon_fav, key=f"fav_{u.id}"):
                        if is_fav:
                            db.query(FavorisCoach).filter(FavorisCoach.coach_id == uid, FavorisCoach.athlete_id == u.id).delete()
                        else:
                            db.add(FavorisCoach(coach_id=uid, athlete_id=u.id))
                        db.commit()
                        st.rerun()

# 4. Affichage des données de l'athlète sélectionné et ACTIONS DU COACH
            with c_data:
                if st.session_state.selected_athlete_id:
                    ath_id = st.session_state.selected_athlete_id
                    ath_name = next((u.username for u in tous_utilisateurs if u.id == ath_id), "Inconnu")
                    
                    st.subheader(f"📊 Dossier de {ath_name.upper()}")
                    
                    # --- ACTION 1 : PLANIFICATION À DISTANCE ---
                    with st.expander(f"📅 Programmer une séance pour {ath_name}", expanded=False):
                        with st.form(f"form_plan_{ath_id}"):
                            pc_date = st.date_input("Date prévue", today + timedelta(days=1))
                            pc_titre = st.text_input("Titre de la séance")
                            pc_desc = st.text_area("Description / Objectifs")
                            if st.form_submit_button("Envoyer au calendrier de l'athlète"):
                                db.add(Planification(user_id=ath_id, date=pc_date, titre=pc_titre, description=pc_desc, statut="Programmé par Coach Lilian"))
                                db.commit()
                                st.success(f"Séance envoyée directement dans l'agenda de {ath_name} !")
                                st.rerun()

                    # --- ACTION 2 : FEEDBACK SUR LES DERNIÈRES SÉANCES ---
                    st.markdown("**Dernières activités & Feedback :**")
                    trente_jours = today - timedelta(days=30)
                    seances_ath = db.query(Seance).filter(Seance.user_id == ath_id, Seance.date >= trente_jours, Seance.type_seance != "Mesures").order_by(Seance.date.desc()).limit(5).all()
                    
                    if seances_ath:
                        for s in seances_ath:
                            date_str = s.date.strftime('%d/%m')
                            resume = f"{s.duree} min | RPE {s.rpe}"
                            
                            with st.expander(f"🏃 {date_str} : {s.type_seance} ({resume})"):
                                if s.type_seance == "Course": st.write(f"**Distance:** {s.dist_totale} km | **Allure:** {s.allure_moy}")
                                if s.exercices and s.exercices not in ["[]", "None"]: st.write(f"**Détails:** {s.exercices}")
                                
                                # Récupération d'un commentaire existant
                                existing_comment = db.query(Commentaire).filter(Commentaire.seance_id == s.id).first()
                                def_text = existing_comment.texte if existing_comment else ""
                                
                                # Formulaire de Debrief
                                c_txt = st.text_area("📝 Ton debrief de Coach :", value=def_text, key=f"txt_{s.id}")
                                if st.button("Enregistrer le debrief", key=f"btn_comment_{s.id}"):
                                    if existing_comment:
                                        existing_comment.texte = c_txt
                                    else:
                                        db.add(Commentaire(seance_id=s.id, texte=c_txt))
                                    db.commit()
                                    st.success("Debrief sauvegardé !")
                                    st.rerun()
                    else:
                        st.info("Aucune activité récente pour cet athlète.")
                else:
                    st.caption("👈 Sélectionne un athlète dans la liste pour voir ses données et interagir.")
