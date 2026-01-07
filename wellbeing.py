import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import io

DB_PATH = "wellbeing.db"

# ---------- Database helpers ----------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def check_table_exists():
    """Pārbauda, vai tabula pastāv"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'")
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def check_old_structure():
    """Pārbauda, vai tabulā ir vecās kolonnas"""
    if not check_table_exists():
        return False
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(responses)")
    columns = [col[1] for col in cur.fetchall()]
    conn.close()
    
    # Vecā struktūra: motivation, stress
    # Jaunā struktūra: stress_q1, stress_q2, stress_q3, motivation_q1, motivation_q2, motivation_q3
    return 'motivation' in columns and 'stress' in columns

def migrate_database():
    """Migrē datus no vecās struktūras uz jauno"""
    if not check_old_structure():
        return
    
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # 1. Izveidojam jaunu tabulu ar pareizo struktūru
        cur.execute('''
            CREATE TABLE IF NOT EXISTS responses_new (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                department TEXT,
                stress_q1 INTEGER,
                stress_q2 INTEGER,
                stress_q3 INTEGER,
                motivation_q1 INTEGER,
                motivation_q2 INTEGER,
                motivation_q3 INTEGER
            )
        ''')
        
        # 2. Migrējam datus no vecās tabulas uz jauno
        # Katram jautājumam piešķiram tādu pašu vērtību kā vidējam
        cur.execute('''
            INSERT INTO responses_new (id, timestamp, department, 
                                       stress_q1, stress_q2, stress_q3,
                                       motivation_q1, motivation_q2, motivation_q3)
            SELECT id, timestamp, department,
                   stress, stress, stress,
                   motivation, motivation, motivation
            FROM responses
        ''')
        
        # 3. Dzēšam veco tabulu
        cur.execute("DROP TABLE responses")
        
        # 4. Pārsaucam jauno tabulu par veco nosaukumu
        cur.execute("ALTER TABLE responses_new RENAME TO responses")
        
        conn.commit()
        print("✅ Datubāze atjaunināta uz jauno versiju")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Kļūda migrējot datubāzi: {e}")
    finally:
        conn.close()

def init_db():
    """Inicializē datubāzi ar pareizo struktūru"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            department TEXT,
            stress_q1 INTEGER,
            stress_q2 INTEGER,
            stress_q3 INTEGER,
            motivation_q1 INTEGER,
            motivation_q2 INTEGER,
            motivation_q3 INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    
    # Ja atklājam veco struktūru, migrējam datus
    if check_old_structure():
        migrate_database()

def add_response(department, stress_q1, stress_q2, stress_q3, motivation_q1, motivation_q2, motivation_q3):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO responses (timestamp, department, stress_q1, stress_q2, stress_q3, motivation_q1, motivation_q2, motivation_q3) VALUES (?,?,?,?,?,?,?,?)",
        (datetime.utcnow().isoformat(), department, stress_q1, stress_q2, stress_q3, motivation_q1, motivation_q2, motivation_q3)
    )
    conn.commit()
    conn.close()

def load_responses_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM responses", conn, parse_dates=["timestamp"])
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=[
            "id", "timestamp", "department",
            "stress_q1", "stress_q2", "stress_q3",
            "motivation_q1", "motivation_q2", "motivation_q3"
        ])
    return df
def delete_responses(department=None, start_date=None, end_date=None):
    """
    Dzēš datus pēc nodaļas un/vai datuma diapazona.
    Ja abi parametri None, dzēš visu tabulu.
    """
    conn = get_conn()
    cur = conn.cursor()
    
    query = "DELETE FROM responses WHERE 1=1"
    params = []

    if department:
        query += " AND department = ?"
        params.append(department)
    if start_date:
        query += " AND DATE(timestamp) >= ?"
        params.append(start_date.strftime("%Y-%m-%d"))
    if end_date:
        query += " AND DATE(timestamp) <= ?"
        params.append(end_date.strftime("%Y-%m-%d"))

    cur.execute(query, params)
    conn.commit()
    conn.close()

# ---------------------------------------------------------------
# ----------------------  UI STYLE ADDITIONS  --------------------
# ---------------------------------------------------------------
st.set_page_config(page_title="Wellbeing Monitor", layout="wide")

# ---- CUSTOM CSS TO MATCH YOUR VISUAL EXAMPLE ----
# --------- PIEVIENO MATERIAL ICONS FONTU ---------
st.markdown("""
<link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
""", unsafe_allow_html=True)

# --------- ATJAUNINĀTS CUSTOM CSS ---------
st.markdown("""
<style>
 

    /* Pārkrāso stToolbar fonu par baltu */
    div.stAppToolbar.st-emotion-cache-14vh5up {
        background-color: #ffffff !important;
    }
            
    /* Import Archivo font */
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800;900&display=swap');

    /* Apply font globally */
    * {
        font-family: 'Archivo', sans-serif !important;
    }

    /* MAIN BACKGROUND - WHITE */
    .stApp, body, .main, .block-container {
        background: white !important;
        color: rgb(34, 34, 33) !important;
    }

    /* Remove default Streamlit padding */
    .main .block-container {
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }

    /* LEFT SIDEBAR - YELLOW BACKGROUND */
    section[data-testid="stSidebar"] {
        background-color: rgb(238, 212, 132) !important;
        padding-top: 40px;
        min-height: 100vh;
        transition: none; /* atvieglo toggle animāciju */
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] * {
        color: rgb(34, 34, 33) !important;
    }


    /* Main content area - FULL PAGE WHITE */
    .main-content {
        background: white !important;
        display: flex;
        justify-content: center;
        align-items: flex-start;
    }

    /* WHITE FORM INSIDE GRAY CARD */
    .msc-form {
        background: white !important;
        border-radius: 8px !important;
        width: 100% !important;
    }

    /* Header styling */
    h1, h2, h3, h4, h5, h6 {
        color: rgb(34, 34, 33) !important;
        font-weight: 700 !important;
        margin-bottom: 20px !important;
    }

    /* Form header styling */
    .form-header {
        font-size: 24px;
        font-weight: 800;
        color: rgb(34, 34, 33);
        margin-bottom: 10px;
    }

    .form-subheader {
        color: rgb(189, 189, 189);
        font-size: 16px;
        font-weight: 500;
    }

    /* Select box styling */
    .stSelectbox, .stSlider {
        margin-bottom: 30px !important;
    }

    /* Slider styling - WHITE BACKGROUND FOR SLIDERS */
    .stSlider > div > div {
        background: white !important;
    }

    /* Slider track background */
    .stSlider > div > div > div {
        background: rgb(242, 242, 242) !important;
    }

    /* Active slider track (filled part) */
    .stSlider > div > div > div > div {
        background: rgb(238, 212, 132) !important;
    }

    /* Button styling */
    .stButton > button {
        background-color: rgb(238, 212, 132) !important;
        color: rgb(34, 34, 33) !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        width: 100% !important;
        margin-top: 20px !important;
        cursor: pointer !important; /* saglabā klikšķa funkcionalitāti */
    }

    .stButton > button:hover {
        background-color: rgb(225, 200, 120) !important;
    }

    /* Section titles inside form */
    .section-title {
        font-size: 18px !important;
        font-weight: 700 !important;
        margin-bottom: 15px !important;
        color: rgb(34, 34, 33) !important;
    }

    /* Sidebar selectbox styling */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: white !important;
        color: black !important;
        border: 1px solid rgb(120,120,120) !important;
        border-radius: 6px !important;
    }

    section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
        color: black !important;
    }

    section[data-testid="stSidebar"] .stSelectbox svg {
        fill: black !important;
    }

    /* Material icons font for sidebar toggle */
    [data-testid="stIconMaterial"] {
        font-family: 'Material Icons' !important;
        font-size: 24px !important;
        color: rgb(34, 34, 33) !important;
        cursor: pointer;
    }

    /* No global cursor override */
    /* cursor auto removed to not block sidebar toggle */

    /* Mainīt download button fonu un tekstu */
    div.stDownloadButton > button {
        background-color: rgb(238, 212, 132) !important;
        color: black !important;
        border-radius: 30px !important;
        padding: 10px 25px !important;
        font-weight: 600 !important;
    }

    /* Hover efekts */
    div.stDownloadButton > button:hover {
        background-color: rgb(225, 200, 120) !important;
    }
        
    
            

    /* MAIN ALERT CONTAINER — remove yellow frame completely */
    div[role="alert"][data-testid="stAlertContainer"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* INNER WRAPPER (this is the real visible alert box) */
    div[role="alert"][data-testid="stAlertContainer"] > .st-am.st-en {
        background-color: #FFF4D6 !important;   /* tavs jaunais fons */
        color: #3A2E0D !important;              /* tumšs teksts */
        border: 2px solid #E6C785 !important;   /* iekšējais rāmis */
        border-radius: 8px !important;
        padding: 15px !important;
    }

    /* Markdown text */
    div[data-testid="stMarkdownContainer"] p {
        color: #3A2E0D !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        margin: 0 !important;
    }

    /* Icon recolor */
    div[role="alert"] svg {
        fill: #A07500 !important;
    }
            
    /* MAIN LABEL ABOVE VALUE */
    div[data-testid="stMetric"] label {
        color: black !important;
        font-weight: 600 !important;
    }

    /* VALUE (5.0/10) */
    div[data-testid="stMetric"] div {
        color: black !important;
    }

    div[data-baseweb="select"] {
        cursor: pointer !important;
    }
    div[data-baseweb="select"] * {
    cursor: pointer !important;
    }





        
</style>
""", unsafe_allow_html=True)

# Initialize database with migration support
init_db()

# ---------- HEADER WITH LOGO ----------
# Samazina top padding, bet ne līdz nullei
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 0.7rem;  /* neliels padding, columns joprojām darbojas */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Centrēts logo ar columns
left_col, center_col, right_col = st.columns([2.4, 2, 1])
with center_col:
    st.image("projekts/images/msc_logo.png", width=75)


# Navigation
view = st.sidebar.selectbox("Izvēlieties lapu", ["Aizpildīt anketu", "HR Dashboard"])
HR_PASSWORD = "HR123"

# ---------- FORM PAGE ----------
if view == "Aizpildīt anketu":
    
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="msc-form">', unsafe_allow_html=True)
    
    st.markdown('<div class="form-header">Ievadi savus rādītājus</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subheader">Nodaļa</div>', unsafe_allow_html=True)
    
    department = st.selectbox("", ["Administration", "Customer Invoicing", "Finance & Accounting", "Commercial Reporting & BI", "Information Technology", "OVA", "Documentation, Pricing & Legal"])
    
    st.markdown('<div class="form-divider"></div>', unsafe_allow_html=True)
    
    # ---------- STRESS SECTION ----------
    st.markdown('<div class="section-title">1.) Darba noslogojums, ko izjūtat ikdienā (0-10)</div>', unsafe_allow_html=True)
    stress_q1 = st.slider("", 0, 10, 5, key="stress_q1")

    st.markdown('<div class="section-title">2.) Trauksmes vai satraukuma līmenis saistībā ar darba jautājumiem (0-10)</div>', unsafe_allow_html=True)
    stress_q2 = st.slider("", 0, 10, 5, key="stress_q2")

    st.markdown('<div class="section-title">3.) Izsīkuma un noguruma pakāpe darba dēļ (0-10)</div>', unsafe_allow_html=True)
    stress_q3 = st.slider("", 0, 10, 5, key="stress_q3")
    
    # Aprēķina stress vidējo (tikai attēlošanai)
    stress_avg = round((stress_q1 + stress_q2 + stress_q3) / 3, 2)
    
    # ---------- MOTIVATION SECTION ----------
    st.markdown('<div class="section-title">4.) Motivācija doties uz darbu un iesaistīties ikdienas pienākumos (0-10)</div>', unsafe_allow_html=True)
    motivation_q1 = st.slider("", 0, 10, 5, key="motivation_q1")

    st.markdown('<div class="section-title">5.) Iedvesma, ko sniedz jūsu komanda un vadītājs(0-10)</div>', unsafe_allow_html=True)
    motivation_q2 = st.slider("", 0, 10, 5, key="motivation_q2")

    st.markdown('<div class="section-title">6.) Novērtējuma sajūta par darbu, ko veicat(0-10)</div>', unsafe_allow_html=True)
    motivation_q3 = st.slider("", 0, 10, 5, key="motivation_q3")
    
    # Aprēķina motivation vidējo (tikai attēlošanai)
    motivation_avg = round((motivation_q1 + motivation_q2 + motivation_q3) / 3, 2)
    
    # Parāda aprēķinātās vidējās vērtības
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Jūsu vidējais stress ", f"{stress_avg}/10")
    with col2:
        st.metric("Jūsu vidējā motivācija ", f"{motivation_avg}/10")
    
    st.markdown('<div class="form-divider"></div>', unsafe_allow_html=True)
    
    if st.button("Iesniegt"):
        add_response(department, stress_q1, stress_q2, stress_q3, motivation_q1, motivation_q2, motivation_q3)
        st.success("Paldies — jūsu atbilde ir saglabāta.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- HR DASHBOARD ----------
elif view == "HR Dashboard":
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="msc-form">', unsafe_allow_html=True)
    
    st.markdown('<div class="form-header">HR Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subheader">Pārskats pa nodaļām</div>', unsafe_allow_html=True)
    
    hr_pw = st.text_input("Ievadiet HR paroli", type="password", key="hr_password")
    
    if hr_pw == HR_PASSWORD:
        df = load_responses_df()
        
        if df.empty:
            st.info("Datu vēl nav.")
        else:
            # HR izvēles: nodaļa un periods
            all_departments = sorted(df['department'].unique())
            selected_dept = st.selectbox(
                "Izvēlieties nodaļu vai skatu:",
                ["Visas nodaļas"] + all_departments,
                key="hr_select_dept"
            )
            
            start_date = st.date_input("Sākuma datums", value=df['timestamp'].min().date(), key="hr_start_date")
            end_date = st.date_input("Beigu datums", value=df['timestamp'].max().date(), key="hr_end_date")
            
            # Filtrējam datus pēc datumiem
            filtered_df = df[(df['timestamp'].dt.date >= start_date) & 
                             (df['timestamp'].dt.date <= end_date)]
            
            if selected_dept != "Visas nodaļas":
                filtered_df = filtered_df[filtered_df['department'] == selected_dept]
            
            # ---------------- Excel lejupielāde ----------------
            if not filtered_df.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if selected_dept == "Visas nodaļas":
                        df_to_export = filtered_df.groupby('department')[[
                            'stress_q1','stress_q2','stress_q3','motivation_q1','motivation_q2','motivation_q3'
                        ]].mean().round(2).reset_index()
                        sheet_name = "Avg_by_department"
                        file_name = "wellbeing_avg_by_department.xlsx"
                    else:
                        df_to_export = pd.DataFrame([filtered_df[[
                            'stress_q1','stress_q2','stress_q3','motivation_q1','motivation_q2','motivation_q3'
                        ]].mean().round(2)])
                        sheet_name = f"{selected_dept}_report"
                        file_name = f"wellbeing_{selected_dept}_report.xlsx"
                    
                    df_to_export.to_excel(writer, index=False, sheet_name=sheet_name)
                output.seek(0)
                
                st.download_button(
                    label=f"⬇ Lejupielādēt Excel ({selected_dept})",
                    data=output,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_{selected_dept}"
                )
            else:
                st.info("Nav datu izvēlētajā periodā/nodaļā.")
            
            # ---------------- Heatmap un kritiskās nodaļas ----------------
            filtered_df = filtered_df.copy()

            filtered_df['stress'] = filtered_df[['stress_q1','stress_q2','stress_q3']].mean(axis=1)
            filtered_df['motivation'] = filtered_df[['motivation_q1','motivation_q2','motivation_q3']].mean(axis=1)

            if selected_dept == "Visas nodaļas":
                grouped = filtered_df.groupby('department')[['motivation','stress']].mean().round(2)
                
                # Pievieno atbilžu skaitu
                grouped['total_responses'] = filtered_df.groupby('department').size()
                
                st.markdown('<div class="section-title" style="font-size: 20px; margin-top: 30px;">Vidējie rādītāji pa nodaļām</div>', unsafe_allow_html=True)
                st.dataframe(grouped)

                # Kopējais atbilžu skaits visām nodaļām
                total_responses_all = filtered_df.shape[0]
                st.metric("Kopējais atbilžu skaits visās nodaļās", total_responses_all)
                
                # Heatmap
                fig, axs = plt.subplots(1, 2, figsize=(12, max(3, len(grouped)*0.6)))
                colors = ["#8E99BC", "#A6192E"]
                custom_cmap = sns.blend_palette(colors, as_cmap=True, n_colors=256)
                
                sns.heatmap(grouped[['motivation']].T, annot=True, fmt=".2f", cmap=custom_cmap, ax=axs[0], vmin=0, vmax=10,
                            annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 12})
                axs[0].set_title('Motivation (augstāks = labāk)')
                axs[0].set_ylabel('')
                
                sns.heatmap(grouped[['stress']].T, annot=True, fmt=".2f", cmap=custom_cmap, ax=axs[1], vmin=0, vmax=10,
                            annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 12})
                axs[1].set_title('Stress (augstāks = sliktāk)')
                axs[1].set_ylabel('')
                
                fig.patch.set_facecolor('white')
                axs[0].set_facecolor('white')
                axs[1].set_facecolor('white')
                plt.tight_layout()
                st.pyplot(fig)
                
                critical = grouped[(grouped['stress'] >= 7) | (grouped['motivation'] <= 4)]
                if critical.empty:
                    st.success("👍 Nav kritisku nodaļu.")
                else:
                    st.warning("⚠ Atrastas kritiskas nodaļas:")
                    st.dataframe(critical)
                
                

            
            else:
                dept_data = filtered_df[filtered_df['department'] == selected_dept]
                if len(dept_data) > 0:
                    avg_motivation = dept_data['motivation'].mean().round(2)
                    avg_stress = dept_data['stress'].mean().round(2)
                    total_responses = len(dept_data)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Vidējā motivācija", f"{avg_motivation}/10")
                    col2.metric("Vidējais stress", f"{avg_stress}/10")
                    col3.metric("Atbilžu skaits", total_responses)
                    
                    # Heatmap vienai nodaļai
                    single_dept_data = pd.DataFrame({
                        'metric': ['Motivation', 'Stress'],
                        'value': [avg_motivation, avg_stress]
                    }).set_index('metric')
                    
                    fig_single, ax_single = plt.subplots(figsize=(8, 2))
                    
                    # Izveido custom divkrāsu gradientu
                    colors = ["#8E99BC", "#A6192E"]
                    custom_cmap = sns.blend_palette(colors, as_cmap=True, n_colors=256)
                    
                    # Heatmap ar vienu rindu (Motivation un Stress)
                    sns.heatmap(single_dept_data.T, 
                               annot=single_dept_data.T.round(2), 
                               fmt='', 
                               cmap=custom_cmap, 
                               cbar=True, 
                               ax=ax_single, 
                               vmin=0, 
                               vmax=10,
                               cbar_kws={'label': 'Vērtējums (0-10)'},
                               annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 14})
                    
                    ax_single.set_title(f'{selected_dept} - rādītāju salīdzinājums')
                    ax_single.set_ylabel('')
                    ax_single.set_facecolor('white')
                    fig_single.patch.set_facecolor('white')
                    
                    plt.tight_layout()
                    st.pyplot(fig_single)
        
        # ---------------- Dzēšanas sadaļa apakšā ----------------
        # ---------------- Dzēšanas sadaļa apakšā ----------------
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 18px;">⚠ Dzēst datus</div>', unsafe_allow_html=True)
        st.markdown("Izvēlies datumu diapazonu, lai dzēstu atbilstošos ierakstus.")

        # Pārvēršam timestamp uz datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Aizstājam NaN ar šodienas datumu, ja nepieciešams
        if df['timestamp'].isna().all():
            min_date = max_date = pd.to_datetime("today").date()
        else:
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()

        del_start = st.date_input("Sākuma datums dzēšanai", value=min_date, key="del_start")
        del_end = st.date_input("Beigu datums dzēšanai", value=max_date, key="del_end")

        confirm_delete = st.checkbox("Es apzinos, ka dzēšanas darbība ir neatgriezeniska", key="confirm_delete")

        if confirm_delete and st.button("Dzēst izvēlētos datus", key="delete_button"):
            dept_param = None if selected_dept == "Visas nodaļas" else selected_dept
            delete_responses(department=dept_param, start_date=del_start, end_date=del_end)
            st.success("✅ Dati veiksmīgi dzēsti.")

    
    elif hr_pw:
        st.error("Nepareiza parole.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)