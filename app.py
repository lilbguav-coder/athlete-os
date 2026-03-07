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
st.set_page_config(page_title="Performance OS", layout="wide")
if not os.path.exists("uploads"): os.makedirs("uploads")

st.markdown("""
    <style>
    body { font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #1A1A1D; padding: 20px; border-radius: 8px; border-left: 4px solid #4A90E2; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    h1, h2, h3 { color: #E0E0E0; font-weight: 500; }
    hr { border-color: #333; }
    .stTextArea textarea { width: 100% !important; }
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
# SYSTEME D'AUTHENTIFICATION
# ==========================================
if 'user_id' not in st.session_state:
    st.title("Athlète OS - Portail d'Accès")
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
                else:
                    st.error("Identifiants incorrects.")
                    
    with col2:
        st.subheader("Créer un compte")
        with st.form("register_form"):
            new_user = st.text_input("Nouvel Identifiant")
            new_pwd = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("S'inscrire"):
                if db.query(Utilisateur).filter(Utilisateur.username == new_user).first():
                    st.error("Cet identifiant est déjà pris.")
                elif len(new_pwd) < 4:
                    st.warning("Mot de passe trop court.")
                else:
                    h_pwd = bcrypt.hashpw(new_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    db.add(Utilisateur(username=new_user, password_hash=h_pwd))
                    db.commit()
                    st.success("Compte créé avec succès ! Tu peux te connecter à gauche. (Le premier compte créé récupère ton historique)")

    st.stop() # Bloque l'application tant qu'on n'est pas connecté

# L'utilisateur est connecté !
uid = st.session_state.user_id
st.sidebar.success(f"Connecté : **{st.session_state.username}**")
if st.sidebar.button("Se déconnecter"):
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
st.title("Système de Performance Intégrée")
tabs = st.tabs(["Planification", "Saisie", "Santé", "Journal", "Analyses", "Records"])
today = datetime.now().date()

# ==========================================
# ONGLET 0 : PLANIFICATION
# ==========================================
with tabs[0]: 
    st.header("Plan d'entraînement journalier")
    plan_today = db.query(Planification).filter(Planification.date == today, Planification.user_id == uid).all()
    if plan_today:
        for p in plan_today:
            st.info(f"**Séance du jour : {p.titre}**\n\n{p.description}")
            if st.button(f"Valider la séance", key=f"done_{p.id}"):
                db.query(Planification).filter(Planification.id == p.id).delete()
                db.commit(); st.rerun()
    else:
        st.success("Journée de récupération ou séance libre programmée.")

    st.divider()
    col_p1, col_p2 = st.columns([1, 1])
    
    with col_p1:
        st.subheader("Consultation et Édition")
        date_vue = st.date_input("Sélectionner la date", today, key="plan_view")
        plan_jour = db.query(Planification).filter(Planification.date == date_vue, Planification.user_id == uid).all()
        if plan_jour:
            for p in plan_jour:
                with st.expander(f"Détails : {p.titre}", expanded=True):
                    with st.form(f"edit_plan_{p.id}"):
                        e_titre = st.text_input("Intitulé", p.titre)
                        e_desc = st.text_area("Objectifs", p.description)
                        c_b1, c_b2 = st.columns(2)
                        if c_b1.form_submit_button("Mettre à jour"):
                            db.query(Planification).filter(Planification.id == p.id).update({"titre": e_titre, "description": e_desc})
                            db.commit(); st.rerun()
                        if c_b2.form_submit_button("Supprimer"):
                            db.query(Planification).filter(Planification.id == p.id).delete()
                            db.commit(); st.rerun()
        else:
            st.info("Aucune planification trouvée.")

    with col_p2:
        st.subheader("Programmer une nouvelle séance")
        with st.form("add_plan"):
            p_date = st.date_input("Date prévue", today)
            p_titre = st.text_input("Intitulé de la séance")
            p_desc = st.text_area("Descriptif technique")
            if st.form_submit_button("Ajouter au calendrier"):
                db.add(Planification(user_id=uid, date=p_date, titre=p_titre, description=p_desc, statut="Programmé"))
                db.commit(); st.success("Séance programmée."); st.rerun()

# ==========================================
# ONGLET 1 : SAISIE
# ==========================================
with tabs[1]: 
    tab_matin, tab_seance = st.tabs(["🌅 Matin : Constantes & Sommeil", "🏋️ Séance : Entraînement"])
    
    with tab_matin:
        st.subheader("Récupération de la nuit")
        d_date_matin = st.date_input("Date", today, key="date_matin")
        
        exist_m = db.query(Seance).filter(Seance.date == d_date_matin, Seance.user_id == uid).first()
        def_slp = float(exist_m.sommeil_heures) if exist_m and exist_m.sommeil_heures else 7.5
        def_slp_q = int(exist_m.sommeil_qualite) if exist_m and exist_m.sommeil_qualite else 7
        def_vfc = int(exist_m.vfc) if exist_m and exist_m.vfc else 0
        def_fcn = int(exist_m.fc_nocturne) if exist_m and exist_m.fc_nocturne else 0
        
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            slp = st.number_input("Sommeil total (heures)", 0.0, 15.0, def_slp)
            slp_q = st.slider("Index qualité (1-10)", 1, 10, def_slp_q)
        with c_m2:
            vfc = st.number_input("Variabilité FC (VFC/HRV)", 0, 250, def_vfc)
            fcn = st.number_input("FC Repos (Nocturne)", 0, 150, def_fcn)
            
        st.markdown("---")
        st.subheader("État psychologique")
        stress = st.select_slider("Niveau de stress", [1,2,3,4,5], value=2, key="stress_m")
        motiv = st.select_slider("Motivation pour aujourd'hui", [1,2,3,4,5], value=4, key="motiv_m")
        
        if st.button("Sauvegarder mes constantes", type="primary"):
            records = db.query(Seance).filter(Seance.date == d_date_matin, Seance.user_id == uid).all()
            if records:
                db.query(Seance).filter(Seance.date == d_date_matin, Seance.user_id == uid).update({
                    "sommeil_heures": slp, "sommeil_qualite": slp_q, "vfc": vfc, "fc_nocturne": fcn, "pre_check": str({"stress": stress, "motiv": motiv})
                })
            else:
                db.add(Seance(user_id=uid, date=d_date_matin, type_seance="Mesures", rpe=0, duree=0,
                              sommeil_heures=slp, sommeil_qualite=slp_q, vfc=vfc, fc_nocturne=fcn,
                              pre_check=str({"stress": stress, "motiv": motiv})))
            db.commit()
            st.success("Constantes enregistrées pour la journée ! ✅")

    with tab_seance:
        mode = st.radio("Modalité", ["Force", "Hyrox", "Course"], horizontal=True)
        d_date_ent = st.date_input("Date d'exécution", today, key="date_ent")
        current_exos, dist_tot, allure_m, shoe, fc_moy, img_path = [], 0.0, "00:00", None, 0, None
        
        rpe = st.slider("RPE (Rating of Perceived Exertion)", 1, 10, 5)
        dur = st.number_input("Volume horaire (min)", 0, 480, 60)
        
        if mode == "Course":
            colc1, colc2 = st.columns(2)
            dist_tot = colc1.number_input("Distance courue (km)", 0.0)
            allure_m = colc2.text_input("Allure globale (min:sec)", "05:00")
            fc_moy = colc1.number_input("FC Moyenne d'effort", 0, 220, 0)
            shoe = colc2.text_input("Modèle de chaussures", "Standard")
            
            st.markdown("**Construction des blocs d'allure**")
            if 'blks' not in st.session_state: st.session_state.blks = []
            st.button("Ajouter une séquence", on_click=lambda: st.session_state.blks.append({"nom": f"Bloc {len(st.session_state.blks)+1}", "reps": 1, "dist": 5.0, "allure": "05:00", "rec_dist": 0.0, "rec_allure": "00:00"}))
            for i, b in enumerate(st.session_state.blks):
                cs = st.columns([2,1,1,1,1,1])
                b['nom'] = cs[0].text_input("Nom", b['nom'], key=f"seq_nom_{i}")
                b['reps'] = cs[1].number_input("Reps", 1, key=f"seq_rep_{i}")
                b['dist'] = cs[2].number_input("Dist", 0.0, key=f"seq_dist_{i}")
                b['allure'] = cs[3].text_input("Allure", b['allure'], key=f"seq_all_{i}")
                b['rec_dist'] = cs[4].number_input("Rec", 0.0, key=f"seq_recd_{i}")
                b['rec_allure'] = cs[5].text_input("All. R", b['rec_allure'], key=f"seq_reca_{i}")
        
        elif mode in ["Force", "Hyrox"]:
            nb = st.number_input("Nombre de mouvements exécutés", 1, 20, 1)
            for i in range(nb):
                cols = st.columns([3, 2, 1, 1, 1])
                nom = cols[0].selectbox(f"Mouvement {i+1}", [""] + get_options_exos() + ["+ Saisir nouveau"], key=f"force_nom_{i}")
                if nom == "+ Saisir nouveau": nom = cols[0].text_input(f"Nouveau mouvement", key=f"force_new_{i}")
                grp = cols[1].selectbox("Muscle", ["Jambes", "Dos", "Pecs", "Epaules", "Bras", "Full Body"], key=f"force_grp_{i}")
                s = cols[2].number_input("Séries", 0, key=f"force_s_{i}")
                r = cols[3].number_input("Reps", 0, key=f"force_r_{i}")
                p = cols[4].number_input("Charge", 0.0, key=f"force_p_{i}")
                if nom: current_exos.append({"nom": nom.strip().title(), "groupe": grp, "s": s, "r": r, "p": p})

        if st.button("Enregistrer ma séance", type="primary"):
            base = db.query(Seance).filter(Seance.date == d_date_ent, Seance.user_id == uid).first()
            i_slp = base.sommeil_heures if base else 0.0
            i_slpq = base.sommeil_qualite if base else 0
            i_vfc = base.vfc if base else 0
            i_fcn = base.fc_nocturne if base else 0
            i_pre = base.pre_check if base else "{}"
            
            db.add(Seance(user_id=uid, date=d_date_ent, type_seance=mode, rpe=rpe, duree=dur, 
                          exercices=str(current_exos), intervalles=str(st.session_state.get('blks', [])), dist_totale=dist_tot, allure_moy=allure_m, fc_moy=fc_moy,
                          sommeil_heures=i_slp, sommeil_qualite=i_slpq, vfc=i_vfc, fc_nocturne=i_fcn, chaussures=shoe, 
                          pre_check=i_pre, image_fc=img_path))
            db.commit()
            st.session_state.blks = []
            st.success("Séance sauvegardée ! ✅"); st.rerun()

# ==========================================
# ONGLET 2 : SANTÉ
# ==========================================
with tabs[2]: 
    st.subheader("Suivi de composition corporelle et lésions")
    with st.form("sante_pro"):
        c1, c2 = st.columns(2)
        h_date = c1.date_input("Date de la mesure", today)
        h_poids = c2.number_input("Masse corporelle (kg)", 0.0)
        h_taille = c1.number_input("Stature (cm)", 175.0)
        h_ventre = c2.number_input("Circonférence abdominale (cm)", 80.0)
        h_cou = c1.number_input("Circonférence nuque (cm)", 38.0)
        st.markdown("---")
        c3, c4 = st.columns(2)
        h_cal = c3.number_input("Apport calorique (kcal)", 0)
        h_prot = c4.number_input("Apport protéique (g)", 0)
        st.markdown("---")
        h_bless = st.selectbox("Localisation de lésion", ["Aucune", "Genou", "Bas du dos", "Epaule", "Cheville", "Ischios"])
        h_grav = st.slider("Index de douleur (0-10)", 0, 10, 0)
        if st.form_submit_button("Valider la mesure"):
            mg = calc_body_fat(h_poids, h_taille, h_cou, h_ventre)
            db.add(Sante(user_id=uid, date=h_date, poids=h_poids if h_poids > 0 else None, taille=h_taille, cou=h_cou, ventre=h_ventre, mg_estimee=mg if mg > 0 else None, calories=h_cal if h_cal > 0 else None, proteines=h_prot, blessure_nom=h_bless, blessure_gravite=h_grav))
            db.commit(); st.success("Mesures ajoutées au registre.")

# ==========================================
# ONGLET 3 : JOURNAL
# ==========================================
with tabs[3]: 
    st.subheader("Vue d'ensemble du registre")
    if 'cal_year' not in st.session_state: st.session_state.cal_year = today.year
    if 'cal_month' not in st.session_state: st.session_state.cal_month = today.month
    if 'sel_date' not in st.session_state: st.session_state.sel_date = today

    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    if col_nav1.button("Mois Précédent"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month == 0:
            st.session_state.cal_month = 12
            st.session_state.cal_year -= 1
    if col_nav3.button("Mois Suivant"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month == 13:
            st.session_state.cal_month = 1
            st.session_state.cal_year += 1
            
    col_nav2.markdown(f"<h3 style='text-align: center;'>{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)

    df_all = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid}", engine)
    if not df_all.empty:
        df_all['date'] = pd.to_datetime(df_all['date'])
        df_mois = df_all[(df_all['date'].dt.month == st.session_state.cal_month) & (df_all['date'].dt.year == st.session_state.cal_year)].copy()
        df_mois['date_str'] = df_mois['date'].dt.strftime('%Y-%m-%d')
    else:
        df_mois = pd.DataFrame(columns=['date_str'])
    
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
                indicator, tooltip = "", "Aucune donnée"
                if not seances_jour.empty:
                    for _, s in seances_jour.iterrows():
                        if s['type_seance'] != "Mesures":
                            indicator += "• "
                            tooltip = f"Type: {s['type_seance']} | Vol: {s['duree']} min | RPE: {s['rpe']}"
                if cols_grille[i].button(f"{d.day} {indicator}", key=f"d_{d}", help=tooltip, use_container_width=True):
                    st.session_state.sel_date = d

    st.divider()
    st.subheader(f"Données du {st.session_state.sel_date.strftime('%d/%m/%Y')}")
    
    s_detail = db.query(Seance).filter(Seance.date == st.session_state.sel_date, Seance.user_id == uid).all()
    if s_detail:
        for row in s_detail:
            if row.type_seance == "Mesures": continue 
            col_info, col_edit = st.columns([4, 1])
            with col_info:
                st.markdown(f"#### Module : {row.type_seance}")
                st.write(f"**RPE:** {row.rpe}/10 | **Volume:** {row.duree} min | **Sommeil:** {row.sommeil_heures}h | **VFC:** {row.vfc} ms")
                if row.type_seance == "Course":
                    st.write(f"**Distance nette : {row.dist_totale} km** à {row.allure_moy} min/km")
                if row.exercices and row.exercices not in ["[]", "None"]:
                    try:
                        for ex in ast.literal_eval(row.exercices):
                            st.write(f"- {ex.get('nom','').strip().title()} : {ex.get('s',0)}x{ex.get('r',0)} @ {ex.get('p',0)}kg")
                    except: pass
            
            with col_edit:
                with st.popover("Éditer"):
                    with st.form(f"edit_{row.id}"):
                        new_rpe = st.number_input("Correction RPE", 0, 10, int(row.rpe))
                        new_dur = st.number_input("Correction Vol", 0, 500, int(row.duree))
                        new_slp = st.number_input("Correction Sommeil", 0.0, 15.0, float(row.sommeil_heures or 0))
                        new_vfc = st.number_input("Correction VFC", 0, 250, int(row.vfc or 0))
                        if st.form_submit_button("Appliquer"):
                            db.query(Seance).filter(Seance.date == row.date, Seance.user_id == uid).update({"sommeil_heures": new_slp, "vfc": new_vfc})
                            db.query(Seance).filter(Seance.id == row.id, Seance.user_id == uid).update({"rpe": new_rpe, "duree": new_dur})
                            db.commit(); st.rerun()
                if st.button("Supprimer", key=f"del_{row.id}"):
                    db.query(Seance).filter(Seance.id == row.id, Seance.user_id == uid).delete()
                    db.commit(); st.rerun()
    else: st.info("Aucune donnée pour cette date.")

# ==========================================
# ONGLET 4 : ANALYSES
# ==========================================
with tabs[4]: 
    df_c = pd.read_sql(f"SELECT * FROM seances WHERE user_id = {uid}", engine)
    if not df_c.empty:
        df_c['date'] = pd.to_datetime(df_c['date'])
        
        c_filt1, c_filt2 = st.columns([1, 2])
        filtre_mode = c_filt1.radio("Fenêtre d'analyse", ["Base globale", "Période spécifiée"], horizontal=True)
        if filtre_mode == "Période spécifiée":
            dates = c_filt2.date_input("Bornes temporelles", [today - timedelta(days=30), today])
            if len(dates) == 2: df_c = df_c[(df_c['date'] >= pd.to_datetime(dates[0])) & (df_c['date'] <= pd.to_datetime(dates[1]))]
        
        if df_c.empty: st.warning("Données insuffisantes.")
        else:
            st.subheader("Analyse du Sommeil")
            df_sleep = df_c[df_c['sommeil_heures'] > 0].groupby('date').max().reset_index().sort_values('date')
            if not df_sleep.empty:
                fig_sleep = make_subplots(specs=[[{"secondary_y": True}]])
                fig_sleep.add_trace(go.Bar(x=df_sleep['date'], y=df_sleep['sommeil_heures'], name="Volume Sommeil (h)", marker_color="#3A506B"), secondary_y=False)
                fig_sleep.add_trace(go.Scatter(x=df_sleep['date'], y=df_sleep['sommeil_qualite'], name="Index Qualité (1-10)", mode='lines+markers', line=dict(color="#5BC0BE")), secondary_y=True)
                fig_sleep.update_layout(template="plotly_dark", barmode='group', margin=dict(t=30, b=0))
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
                fig_acwr = go.Figure()
                fig_acwr.add_trace(go.Scatter(x=daily['date'], y=daily['aigu'], name="Fatigue Aiguë (7j)", line=dict(color='#E53935')))
                fig_acwr.add_trace(go.Scatter(x=daily['date'], y=daily['chronique'], name="Forme Chronique (28j)", line=dict(color='#4A90E2')))
                fig_acwr.update_layout(template="plotly_dark", margin=dict(t=30, b=0))
                st.plotly_chart(fig_acwr, use_container_width=True)
                
            with col_d2:
                st.subheader("Distribution du Tonnage")
                t_list = []
                for ex_str in df_c['exercices'].dropna():
                    if ex_str != "[]" and ex_str != "None":
                        try:
                            for ex in ast.literal_eval(ex_str): t_list.append({"groupe": ex.get('groupe', 'Autre'), "volume": ex.get('s',0)*ex.get('r',0)*ex.get('p',0)})
                        except: pass
                if t_list:
                    df_t = pd.DataFrame(t_list).groupby('groupe').sum().reset_index()
                    st.plotly_chart(px.bar(df_t, x='groupe', y='volume', color='groupe', template="plotly_dark"), use_container_width=True)

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
                    db.commit(); st.success("Enregistré."); st.rerun()
                    
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
            else:
                best_pr = pd.DataFrame(columns=['nom', '1RM', 'p', 'r'])
            
            c_pr = st.columns(3)
            idx = 0
            exos_affiches = set()
            
            for exo, val in dict_manuels.items():
                c_pr[idx%3].metric(f"{exo}", f"{int(val)} kg", "Manuel", delta_color="off")
                exos_affiches.add(exo)
                idx += 1
                
            for _, row in best_pr.iterrows():
                if row['nom'] not in exos_affiches:
                    c_pr[idx%3].metric(f"{row['nom']}", f"{int(row['1RM'])} kg", f"Calculé", delta_color="off")
                    idx += 1
        else:
            st.info("Aucun mouvement enregistré.")
