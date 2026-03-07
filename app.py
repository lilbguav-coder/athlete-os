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

# --- CONFIG & STYLE ---
st.set_page_config(page_title="Athlète OS", page_icon="logo.png", layout="wide")
if not os.path.exists("uploads"): os.makedirs("uploads")

st.markdown("""
    <style>
    body { font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #1A1A1D; padding: 15px; border-radius: 8px; border-left: 4px solid #4A90E2; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #E0E0E0; font-weight: 500; }
    hr { border-color: #333; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION CLOUD ---
db_url = st.secrets["DATABASE_URL"]
engine = create_engine(db_url)
Base = declarative_base()

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
                if db.query(Utilisateur).filter(Utilisateur.username == new_user).first():
                    st.error("Cet identifiant est déjà pris.")
                elif len(new_pwd) < 4: st.warning("Mot de passe trop court.")
                else:
                    h_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db.add(Utilisateur(username=new_user, password_hash=h_pwd))
                    db.commit()
                    st.success("Compte créé avec succès ! Connecte-toi à gauche.")
    st.stop()

# --- Connecté ---
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

def calc_body_fat(poids, taille, cou, ventre):
    try: return 495 / (1.0324 - 0.19077 * (math.log10(ventre - cou)) + 0.15456 * (math.log10(taille))) - 450
    except: return 0

# --- INTERFACE ---
tabs = st.tabs(["Planification", "Saisie", "Santé", "Journal", "Analyses", "Records"])
today = datetime.now().date()

# ==========================================
# ONGLET 0 : PLANIFICATION
# ==========================================
with tabs[0]: 
    st.header("Plan du jour")
    plan_today = db.query(Planification).filter(Planification.date == today, Planification.user_id == uid).all()
    if plan_today:
        for p in plan_today:
            st.info(f"**{p.titre}**\n\n{p.description}")
            if st.button(f"Marquer comme fait", key=f"done_{p.id}"):
                db.query(Planification).filter(Planification.id == p.id).delete()
                db.commit(); st.rerun()
    else: st.success("Aucune séance programmée aujourd'hui.")

    st.divider()
    st.subheader("Programmer une séance")
    with st.form("add_plan"):
        p_date = st.date_input("Date", today)
        p_titre = st.text_input("Titre")
        p_desc = st.text_area("Description")
        if st.form_submit_button("Ajouter"):
            db.add(Planification(user_id=uid, date=p_date, titre=p_titre, description=p_desc, statut="Programmé"))
            db.commit(); st.success("Ajouté !"); st.rerun()

# ==========================================
# ONGLET 1 : SAISIE
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
        current_exos, dist_tot, allure_m, shoe, fc_moy, img_path = [], 0.0, "00:00", None, 0, None
        
        if mode != "Repos":
            c_r1, c_r2 = st.columns(2)
            rpe = c_r1.slider("RPE (Effort 1-10)", 1, 10, 5)
            dur = c_r2.number_input("Durée (min)", 0, 480, 60)
            
            if mode == "Course":
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
            db.commit()
            st.session_state.blks = []
            st.success("Séance sauvegardée ! ✅"); st.rerun()

# ==========================================
# ONGLET 2 : SANTÉ
# ==========================================
with tabs[2]: 
    st.subheader("Carnet de Santé")
    h_date = st.date_input("Date de la mesure", today, key="date_sante")
    
    # On va chercher s'il y a déjà des données existantes pour cette date
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
                if exist_s:
                    db.query(Sante).filter(Sante.id == exist_s.id).update({"poids": h_poids or None, "taille": h_taille or None, "ventre": h_ventre or None, "cou": h_cou or None, "mg_estimee": mg})
                else:
                    db.add(Sante(user_id=uid, date=h_date, poids=h_poids or None, taille=h_taille or None, ventre=h_ventre or None, cou=h_cou or None, mg_estimee=mg))
                db.commit(); st.rerun()

    with st.expander("🍎 Nutrition journalière"):
        with st.form("form_nutrition"):
            c3, c4 = st.columns(2)
            h_cal = c3.number_input("Calories (kcal)", 0, 10000, int(exist_s.calories) if exist_s and exist_s.calories else 0)
            h_prot = c4.number_input("Protéines (g)", 0, 500, int(exist_s.proteines) if exist_s and exist_s.proteines else 0)
            
            if st.form_submit_button("Valider Nutrition"):
                if exist_s:
                    db.query(Sante).filter(Sante.id == exist_s.id).update({"calories": h_cal or None, "proteines": h_prot or None})
                else:
                    db.add(Sante(user_id=uid, date=h_date, calories=h_cal or None, proteines=h_prot or None))
                db.commit(); st.rerun()

    with st.expander("🩹 Suivi des Douleurs"):
        with st.form("form_blessures"):
            bless_list = ["Aucune", "Genou", "Bas du dos", "Epaule", "Cheville", "Ischios", "Autre"]
            idx_b = bless_list.index(exist_s.blessure_nom) if exist_s and exist_s.blessure_nom in bless_list else 0
            h_bless = st.selectbox("Localisation", bless_list, index=idx_b)
            h_grav = st.slider("Douleur (0-10)", 0, 10, int(exist_s.blessure_gravite) if exist_s and exist_s.blessure_gravite else 0)
            
            if st.form_submit_button("Valider Douleur"):
                if exist_s:
                    db.query(Sante).filter(Sante.id == exist_s.id).update({"blessure_nom": h_bless, "blessure_gravite": h_grav})
                else:
                    db.add(Sante(user_id=uid, date=h_date, blessure_nom=h_bless, blessure_gravite=h_grav))
                db.commit(); st.rerun()

# ==========================================
# ONGLET 3 : JOURNAL
# ==========================================
with tabs[3]: 
    if 'cal_month' not in st.session_state: st.session_state.cal_month = today.month
    if 'cal_year' not in st.session_state: st.session_state.cal_year = today.year
    if 'sel_date' not in st.session_state: st.session_state.sel_date = today

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    if col_nav1.button("◀"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month == 0: st.session_state.cal_month, st.session_state.cal_year = 12, st.session_state.cal_year - 1
    if col_nav3.button("▶"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month == 13: st.session_state.cal_month, st.session_state.cal_year = 1, st.session_state.cal_year + 1
            
    col_nav2.markdown(f"<h3 style='text-align: center;'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)

    df_all = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid}", engine)
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_mois = df_all[(df_all['date'].dt.month == st.session_state.cal_month) & (df_all['date'].dt.year == st.session_state.cal_year)].copy()
        df_mois['date_str'] = df_mois['date'].dt.strftime('%Y-%m-%d')
    else: df_mois = pd.DataFrame(columns=['date_str'])
    
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(st.session_state.cal_year, st.session_state.cal_month)
    
    jours = ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"]
    cols_jours = st.columns(7)
    for i, j in enumerate(jours): cols_jours[i].write(f"**{j}**")
    
    for week in month_days:
        cols_grille = st.columns(7)
        for i, d in enumerate(week):
            if d.month == st.session_state.cal_month:
                seances_jour = df_mois[df_mois['date_str'] == d.strftime('%Y-%m-%d')]
                indicator = "• " * len(seances_jour[seances_jour['type_seance'] != "Mesures"])
                if cols_grille[i].button(f"{d.day} {indicator}", key=f"d_{d}", use_container_width=True):
                    st.session_state.sel_date = d

    st.divider()
    st.subheader(f"Données du {st.session_state.sel_date.strftime('%d/%m/%Y')}")
    s_detail = db.query(Seance).filter(Seance.date == st.session_state.sel_date, Seance.user_id == uid).all()
    if s_detail:
        for row in s_detail:
            if row.type_seance == "Mesures": continue 
            with st.container():
                st.markdown(f"#### {row.type_seance}")
                st.write(f"**RPE:** {row.rpe}/10 | **Vol:** {row.duree} min")
                
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
                            if ex.get('s',0) > 0: st.write(f"- {ex.get('nom','')} : {ex.get('s',0)}x{ex.get('r',0)} @ {ex.get('p',0)}kg")
                            else: st.write(f"- {ex.get('nom','')} @ {ex.get('p',0)}kg")
                    except: pass
                
                if st.button("🗑️ Supprimer", key=f"del_{row.id}"):
                    db.query(Seance).filter(Seance.id == row.id).delete()
                    db.commit(); st.rerun()
                st.markdown("---")
    else: st.info("Aucune séance ce jour.")

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
    st.subheader("Modélisation Course")
    if not df_r.empty:
        df_run = df_r[(df_r['type_seance'] == "Course") & (df_r['dist_totale'] >= 1.0)].copy()
        if not df_run.empty:
            df_run['sec_tot'] = df_run['allure_moy'].apply(allure_to_sec) * df_run['dist_totale']
            df_run_valide = df_run[df_run['sec_tot'] > 0].copy()
            if not df_run_valide.empty:
                df_run_valide['score_10k'] = df_run_valide.apply(lambda r: estimate_riegel(r['dist_totale'], r['sec_tot'], 10.0), axis=1)
                best_perf = df_run_valide.loc[df_run_valide['score_10k'].idxmin()]
                st.success(f"Référence détectée : {best_perf['dist_totale']} km à {best_perf['allure_moy']} min/km")
                targets = [1, 5, 10, 21.1, 42.2]
                cols_run = st.columns(5)
                for i, t in enumerate(targets):
                    t_sec = estimate_riegel(best_perf['dist_totale'], best_perf['sec_tot'], t)
                    cols_run[i].metric(f"{t} km", f"{sec_to_time_str(t_sec)}", delta_color="off")
        else: st.info("Volume aérobie insuffisant.")

    st.divider()
    col_rec1, col_rec2 = st.columns([2, 1])
    with col_rec2:
        st.subheader("Calibrage 1RM")
        with st.form("add_manual_pr"):
            m_exo = st.selectbox("Mouvement", [""] + get_options_exos())
            m_val = st.number_input("Valeur (kg)", 0.0)
            if st.form_submit_button("Sauvegarder"):
                if m_exo and m_val > 0:
                    db.query(RecordManuel).filter(RecordManuel.nom_exo == m_exo, RecordManuel.user_id == uid).delete()
                    db.add(RecordManuel(user_id=uid, nom_exo=m_exo, valeur_1rm=m_val))
                    db.commit(); st.rerun()
                    
    with col_rec1:
        st.subheader("Performances Maximales (Force)")
        manuels = pd.read_sql(f"SELECT * FROM records_manuels WHERE user_id = {uid}", engine)
        dict_manuels = dict(zip(manuels.nom_exo, manuels.valeur_1rm)) if not manuels.empty else {}
        all_exos = []
        if not df_r.empty:
            for row in df_r['exercices'].dropna():
                if row not in ["None", "[]"]:
                    try: 
                        for ex in ast.literal_eval(row):
                            if ex.get('p', 0) > 0 and ex.get('r', 0) > 0:
                                ex['nom'] = ex.get('nom', '').strip().title()
                                all_exos.append(ex)
                    except: pass
        if all_exos or dict_manuels:
            df_ex = pd.DataFrame(all_exos) if all_exos else pd.DataFrame(columns=['nom', '1RM', 'p', 'r'])
            if not df_ex.empty:
                df_ex['1RM'] = df_ex.apply(lambda r: r['p'] * (36/(37-r['r'])) if r['r']<37 else r['p'], axis=1)
                best_pr = df_ex.sort_values('1RM', ascending=False).drop_duplicates('nom')
            else: best_pr = pd.DataFrame(columns=['nom', '1RM', 'p', 'r'])
            
            c_pr = st.columns(3)
            idx = 0
            exos_affiches = set()
            for exo, val in dict_manuels.items():
                c_pr[idx%3].metric(f"{exo}", f"{int(val)} kg", "Manuel", delta_color="off")
                exos_affiches.add(exo); idx += 1
            for _, row in best_pr.iterrows():
                if row['nom'] not in exos_affiches:
                    c_pr[idx%3].metric(f"{row['nom']}", f"{int(row['1RM'])} kg", "Calculé", delta_color="off")
                    idx += 1
