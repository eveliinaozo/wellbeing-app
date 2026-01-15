import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt
import io



DB_PATH = "wellbeing.db"

# ---------- Session state initialization ----------
if 'role' not in st.session_state:
    st.session_state.role = None

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
st.set_page_config(
    page_title="Wellbeing Monitor",
    layout="wide",
    initial_sidebar_state="collapsed"
)


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

# ---------- MAIN NAVIGATION LOGIC ----------
if st.session_state.role is None:
    # Centrēts logo ar columns
    left_col, center_col, right_col = st.columns([2.4, 2, 1])
    with center_col:
        st.image("images/msc_logo.png", width=75)

    st.markdown("<h1 style='text-align: center;'>WELL-BEING APP</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])  # centrs

    with col2:
        if st.button("Start Survey", use_container_width=True):
            st.session_state.role = "employee"
            st.rerun()
    
    st.stop()

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
    st.image("images/msc_logo.png", width=75)

# Navigation
view = st.sidebar.selectbox("Select page", ["Fill in survey", "HR Dashboard"])
HR_PASSWORD = "HR123"

# ---------- FORM PAGE ----------
if view == "Fill in survey":
    
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="msc-form">', unsafe_allow_html=True)
    
    st.markdown('<div class="form-header">Enter your wellbeing indicators</div>', unsafe_allow_html=True)
    # st.markdown('<div class="form-subheader">Department</div>', unsafe_allow_html=True)
    
    departments = [
        "Administration",
        "Customer Invoicing",
        "Finance & Accounting",
        "Commercial Reporting & BI",
        "Information Technology",
        "OVA",
        "Documentation, Pricing & Legal"
    ]

    department = st.selectbox(
        "Department",
        ["Select department"] + departments,
        index=0,
        key="employee_department"
    )

    # ---------- STRESS SECTION ----------
    st.markdown('<div class="section-title">1.) How intense do you find your daily workload? (0-10, 0 = very light, 10 = too heavy)</div>', unsafe_allow_html=True)
    stress_q1 = st.slider("", 0, 10, 5, key="stress_q1")

    st.markdown('<div class="section-title">2.) To what extent do work-related issues cause you anxiety? (0-10, 0 = not at all, 10 = to a very great extent)</div>', unsafe_allow_html=True)
    stress_q2 = st.slider("", 0, 10, 5, key="stress_q2")

    st.markdown('<div class="section-title">3.) How exhausted do you feel due to your work? (0-10, 0 = not exhausted at all, 10 = extremely exhausted)</div>', unsafe_allow_html=True)
    stress_q3 = st.slider("", 0, 10, 5, key="stress_q3")
    
    # Aprēķina stress vidējo (tikai attēlošanai)
    stress_avg = round((stress_q1 + stress_q2 + stress_q3) / 3, 2)
    
    # ---------- MOTIVATION SECTION ----------
    st.markdown('<div class="section-title">4.) Rate your motivation to perform daily work tasks. (0-10, 0 = not motivated at all, 10 = extremely motivated)</div>', unsafe_allow_html=True)
    motivation_q1 = st.slider("", 0, 10, 5, key="motivation_q1")

    st.markdown('<div class="section-title">5.) How inspired do you feel at work?(0-10, 0 = not inspired at all, 10 = extremely inspired)</div>', unsafe_allow_html=True)
    motivation_q2 = st.slider("", 0, 10, 5, key="motivation_q2")

    st.markdown('<div class="section-title">6.) Rate how valued you feel for the work you do. (0-10, 0 = not valued at all, 10 = extremely valued)</div>', unsafe_allow_html=True)
    motivation_q3 = st.slider("", 0, 10, 5, key="motivation_q3")
    
    # Aprēķina motivation vidējo (tikai attēlošanai)
    motivation_avg = round((motivation_q1 + motivation_q2 + motivation_q3) / 3, 2)
    
    # Parāda aprēķinātās vidējās vērtības
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Your average stress ", f"{stress_avg}/10")
    with col2:
        st.metric("Your average motivation ", f"{motivation_avg}/10")
    
    if st.button("Submit"):
        if department == "Select department":
            st.warning("Please select a department before submitting.")
        else:
            add_response(
                department,
                stress_q1, stress_q2, stress_q3,
                motivation_q1, motivation_q2, motivation_q3
            )
            st.success("Thank you — your response has been saved.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------- HR DASHBOARD ----------
elif view == "HR Dashboard":
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    st.markdown('<div class="msc-form">', unsafe_allow_html=True)
    
    st.markdown('<div class="form-header">HR Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-subheader">Overview by department</div>', unsafe_allow_html=True)
    
    hr_pw = st.text_input("Enter HR password", type="password", key="hr_password")
    
    if hr_pw == HR_PASSWORD:
        df = load_responses_df()
        
        if df.empty:
            st.info("No data available yet.")
        else:
            # HR izvēles: nodaļa un periods
            all_departments = sorted(df['department'].unique())
            selected_dept = st.selectbox(
                "Select department or view:",
                ["All departments"] + all_departments,
                key="hr_select_dept"
            )
           
            # Ja izvēlas "Select department", filtrēšanu neveic
            if selected_dept == "Select department":
                filtered_df = df.copy()
            else:
                filtered_df = df[df['department'] == selected_dept]

            st.markdown("""
            <div style="font-size:14px; margin-bottom:10px; color:#555;">
            Choose the time period you would like to analyze.  
            The dashboard will automatically update to show responses submitted during this period.
            </div>
            """, unsafe_allow_html=True)

            start_date = st.date_input("Start date", value=df['timestamp'].min().date(), key="hr_start_date")
            end_date = st.date_input("End date", value=df['timestamp'].max().date(), key="hr_end_date")
            
            # Filtrējam datus pēc datumiem
            filtered_df = df[(df['timestamp'].dt.date >= start_date) & 
                             (df['timestamp'].dt.date <= end_date)]
            
            if selected_dept != "All departments":
                filtered_df = filtered_df[filtered_df['department'] == selected_dept]
            
            # ---------------- Excel lejupielāde ----------------
            if not filtered_df.empty:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if selected_dept == "All departments":
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
                    label=f"⬇ Download Excel ({selected_dept})",
                    data=output,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_{selected_dept}"
                )
            else:
                st.info("No data available for the selected period or department.")
            
            # ---------------- Heatmap un kritiskās nodaļas ----------------
            filtered_df = filtered_df.copy()

            filtered_df['stress'] = filtered_df[['stress_q1','stress_q2','stress_q3']].mean(axis=1)
            filtered_df['motivation'] = filtered_df[['motivation_q1','motivation_q2','motivation_q3']].mean(axis=1)

            if selected_dept == "All departments":
                grouped = filtered_df.groupby('department')[['motivation','stress']].mean().round(2)
                
                # Pievieno atbilžu skaitu
                grouped['total_responses'] = filtered_df.groupby('department').size()
                
                st.markdown('<div class="section-title" style="font-size: 20px; margin-top: 30px;">Average indicators by department</div>', unsafe_allow_html=True)
                st.dataframe(grouped)

                # Kopējais atbilžu skaits visām nodaļām
                total_responses_all = filtered_df.shape[0]
                st.metric("Total number of responses (all departments)", total_responses_all)
                
                # Heatmap
                fig, axs = plt.subplots(1, 2, figsize=(18, max(4, len(grouped)*0.)))
                # Motivation: zils = labs (10), sarkans = slikts (0)
                motivation_cmap = sns.blend_palette(["#A6192E", "#8E99BC"], as_cmap=True, n_colors=256)

                # Stress: sarkans = slikts (10), zils = labs (0)
                stress_cmap = sns.blend_palette(["#8E99BC", "#A6192E"], as_cmap=True, n_colors=256)

                
                sns.heatmap(grouped[['motivation']].T, annot=True, fmt=".2f", cmap=motivation_cmap, ax=axs[0], vmin=0, vmax=10,
                            annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 12})
                axs[0].set_title('Motivation (higher = better)')
                axs[0].set_ylabel('')
                
                sns.heatmap(grouped[['stress']].T, annot=True, fmt=".2f", cmap=stress_cmap, ax=axs[1], vmin=0, vmax=10,
                            annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 12})
                axs[1].set_title('Stress (higher = worse)')
                axs[1].set_ylabel('')
                axs[1].invert_yaxis()  # stress heatmap ass atgriež pareizajā orientācijā

                
                fig.patch.set_facecolor('white')
                axs[0].set_facecolor('white')
                axs[1].set_facecolor('white')
                plt.tight_layout()
                st.pyplot(fig)
                
                critical = grouped[(grouped['stress'] >= 7) | (grouped['motivation'] <= 4)]
                if critical.empty:
                    st.success("👍 No critical departments identified.")
                else:
                    st.warning("⚠ Critical departments identified:")
                    st.dataframe(critical)
            
            else:
                dept_data = filtered_df[filtered_df['department'] == selected_dept]
                if len(dept_data) > 0:
                    avg_motivation = dept_data['motivation'].mean().round(2)
                    avg_stress = dept_data['stress'].mean().round(2)
                    total_responses = len(dept_data)
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Average motivation", f"{avg_motivation}/10")
                    col2.metric("Average stress", f"{avg_stress}/10")
                    col3.metric("Number of responses", total_responses)
                    
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
                               cbar_kws={'label': 'Rating (0-10)'},
                               annot_kws={'color': 'black', 'fontweight': 'bold', 'fontsize': 14})
                    
                    ax_single.set_title(f'{selected_dept} - Comparison of indicators')
                    ax_single.set_ylabel('')
                    ax_single.set_facecolor('white')
                    fig_single.patch.set_facecolor('white')
                    
                    plt.tight_layout()
                    st.pyplot(fig_single)
                    
                    # ============= COMBINED MONTHLY VIEW STABIŅU DIAGRAMMA =============
                    st.markdown('<div class="section-title" style="font-size: 20px; margin-top: 40px;">Monthly trends for ' + selected_dept + '</div>', unsafe_allow_html=True)
                    st.markdown("""
                    <div style="font-size:13px; margin-top:15px; color:#666;">
                    <b>Interpretation note:</b>  
                    Stress scores represent negative wellbeing (higher values = more stress),  
                    while motivation scores represent positive engagement (higher values = more motivation).
                    </div>
                    """, unsafe_allow_html=True)
                    # Izveido mēneša kolonnu
                    dept_data['month'] = dept_data['timestamp'].dt.strftime('%Y-%m')
                    
                    # Grupē pēc mēneša
                    monthly_dept = dept_data.groupby('month').agg({
                        'stress': 'mean',
                        'motivation': 'mean',
                        'id': 'count'  # skaits
                    }).reset_index().round(2)
                    
                    # Sakārto mēnešus alfabētiski (chronoloģiski)
                    monthly_dept = monthly_dept.sort_values('month')
                    
                    if not monthly_dept.empty:
                        # Bar colors
                        bar_color_motivation = '#8E99BC'  # zils/grišs motivācijai
                        bar_color_stress = '#A6192E'      # sarkans stresam
                        
                        fig3, ax3 = plt.subplots(figsize=(12, 6))
                        
                        x = range(len(monthly_dept['month']))
                        width = 0.35
                        
                        bars_motivation = ax3.bar([i - width/2 for i in x], monthly_dept['motivation'], 
                                                 width, label='Motivation', color=bar_color_motivation, 
                                                 edgecolor='black', linewidth=1)
                        bars_stress = ax3.bar([i + width/2 for i in x], monthly_dept['stress'], 
                                             width, label='Stress', color=bar_color_stress, 
                                             edgecolor='black', linewidth=1)
                        
                        ax3.set_title(f'{selected_dept} - Monthly averages comparison', fontweight='bold', fontsize=16, pad=20)
                        ax3.set_ylabel('Rating (0-10)', fontweight='bold')
                        ax3.set_xlabel('Month', fontweight='bold')
                        ax3.set_xticks(x)
                        ax3.set_xticklabels(monthly_dept['month'], rotation=45, ha='right')
                        ax3.grid(True, axis='y', linestyle='--', alpha=0.3)
                        ax3.set_ylim(0, 10)
                        ax3.legend(fontsize=12)
                        
                        # Pievieno vērtības virs stabiņiem
                        for bars in [bars_motivation, bars_stress]:
                            for bar in bars:
                                height = bar.get_height()
                                ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                        f'{height:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=9)
                        
                        fig3.patch.set_facecolor('white')
                        ax3.set_facecolor('white')
                        plt.tight_layout()
                        st.pyplot(fig3)
                        
                        # Rādīt atbilžu skaitu pa mēnešiem
                        st.markdown('<div class="section-title" style="font-size: 16px; margin-top: 20px;">Responses per month</div>', unsafe_allow_html=True)
                        responses_by_month = monthly_dept[['month', 'id']].rename(columns={'id': 'responses'})
                        st.dataframe(responses_by_month.set_index('month'))

        # ---------------- Dzēšanas sadaļa apakšā ----------------
        st.markdown('<hr>', unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size: 18px;">⚠ Delete data</div>', unsafe_allow_html=True)
        st.markdown("Select a date range to permanently delete records.")

        # Pārvēršam timestamp uz datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Aizstājam NaN ar šodienas datumu, ja nepieciešams
        if df['timestamp'].isna().all():
            min_date = max_date = pd.to_datetime("today").date()
        else:
            min_date = df['timestamp'].min().date()
            max_date = df['timestamp'].max().date()

        del_start = st.date_input("Delete from date", value=min_date, key="del_start")
        del_end = st.date_input("Delete to date", value=max_date, key="del_end")

        confirm_delete = st.checkbox("I understand that this action is irreversible", key="confirm_delete")

        if confirm_delete and st.button("Delete selected data", key="delete_button"):
            dept_param = None if selected_dept == "All departments" else selected_dept
            delete_responses(department=dept_param, start_date=del_start, end_date=del_end)
            st.success("✅ Data successfully deleted.")
    
    elif hr_pw:
        st.error("Incorrect password.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)