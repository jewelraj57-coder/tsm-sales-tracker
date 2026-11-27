import json
from datetime import date
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="SR & TSM Sales Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

KHATA_RATE_PER_TON = 200000.0  # ১ টন = ২,০০,০০০ টাকা
DEFAULT_DAYS = 26

SPREADSHEET_NAME = "TSM_Sales_Database"
SALES_SHEET = "Sales_Entries"
TARGET_SHEET = "SR_Monthly_Targets"

# --- Modern & Mobile Responsive CSS ---
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Hind Siliguri', 'Plus Jakarta Sans', sans-serif;
        }

        .stApp {
            background: radial-gradient(circle at top left, #dbeafe 0%, #eff6ff 32%, #f8fafc 70%, #f1f5f9 100%);
            color: #0f172a;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        [data-testid="stSidebar"] * {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] .stRadio > label,
        [data-testid="stSidebar"] .stDateInput > label {
            font-weight: 600 !important;
            color: #cbd5e1 !important;
        }
        [data-testid="stSidebar"] input[type="date"] {
            background-color: #1e293b !important;
            color: #ffffff !important;
            border: 1px solid #475569 !important;
            border-radius: 8px !important;
        }

        /* Hero Banner */
        .hero-box {
            background: linear-gradient(125deg, #0f172a 0%, #1d4ed8 52%, #0284c7 100%);
            color: #ffffff;
            padding: 22px 26px;
            border-radius: 18px;
            margin-bottom: 20px;
            box-shadow: 0 12px 28px rgba(29, 78, 216, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.16);
            position: relative;
            overflow: hidden;
        }
        .hero-box h1 {
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.75rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.01em;
            line-height: 1.25 !important;
        }
        .hero-box p {
            color: #e0f2fe !important;
            margin: 8px 0 0 0 !important;
            font-size: 0.96rem !important;
            line-height: 1.5 !important;
            opacity: 0.96;
        }

        /* Section Headings */
        .section-heading {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.18rem;
            font-weight: 700;
            color: #0f172a;
            margin: 18px 0 10px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #e2e8f0;
        }

        /* Bordered Container Card Enhancement */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.92);
            backdrop-filter: blur(8px);
            border: 1px solid #e2e8f0 !important;
            border-radius: 16px !important;
            padding: 6px 8px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
            margin-bottom: 14px;
        }

        /* KPI Metric Cards */
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-top: 4px solid #2563eb;
            border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.1);
        }
        [data-testid="stMetricLabel"] > div {
            font-size: 0.86rem !important;
            font-weight: 700 !important;
            color: #475569 !important;
        }
        [data-testid="stMetricValue"] > div {
            font-size: 1.32rem !important;
            font-weight: 800 !important;
            color: #0f172a !important;
        }
        [data-testid="stMetricDelta"] > div {
            font-size: 0.8rem !important;
            font-weight: 600 !important;
        }

        /* SKU Cards */
        .sku-card {
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 12px;
            color: #0f172a;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
            transition: transform 0.18s ease;
            height: 100%;
        }
        .sku-card:hover {
            transform: translateY(-2px);
        }
        .sku-pen {
            background: linear-gradient(145deg, #ffffff 0%, #eff6ff 100%);
            border: 1px solid #bfdbfe;
            border-left: 6px solid #2563eb;
        }
        .sku-stat {
            background: linear-gradient(145deg, #ffffff 0%, #f5f3ff 100%);
            border: 1px solid #ddd6fe;
            border-left: 6px solid #7c3aed;
        }
        .sku-khata {
            background: linear-gradient(145deg, #ffffff 0%, #ecfdf5 100%);
            border: 1px solid #a7f3d0;
            border-left: 6px solid #059669;
        }
        .sku-title {
            font-weight: 800;
            font-size: 1.1rem;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .sku-line {
            font-size: 0.94rem;
            line-height: 1.6;
            color: #1e293b;
            margin: 3px 0;
        }

        /* Form Inputs & Buttons */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div, .stDateInput input {
            border-radius: 10px !important;
            border-color: #cbd5e1 !important;
            font-size: 0.95rem !important;
        }
        .stButton > button, .stFormSubmitButton > button {
            border-radius: 11px !important;
            font-weight: 700 !important;
            font-size: 0.96rem !important;
            width: 100%;
            min-height: 44px;
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
            transition: all 0.18s ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
            box-shadow: 0 6px 16px rgba(29, 78, 216, 0.3);
        }

        /* Dataframe Table */
        [data-testid="stDataFrame"] {
            border-radius: 14px !important;
            overflow: hidden !important;
            border: 1px solid #cbd5e1 !important;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        }

        /* --- Mobile Responsiveness (<= 768px) --- */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.85rem;
                padding-bottom: 2.2rem;
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }

            .hero-box {
                padding: 16px 16px;
                border-radius: 14px;
                margin-bottom: 14px;
            }
            .hero-box h1 {
                font-size: 1.32rem !important;
            }
            .hero-box p {
                font-size: 0.84rem !important;
            }

            .section-heading {
                font-size: 1.04rem;
                margin: 14px 0 8px 0;
            }

            [data-testid="stMetric"] {
                padding: 11px 12px;
                border-radius: 12px;
                margin-bottom: 8px;
            }
            [data-testid="stMetricLabel"] > div {
                font-size: 0.78rem !important;
            }
            [data-testid="stMetricValue"] > div {
                font-size: 1.08rem !important;
            }
            [data-testid="stMetricDelta"] > div {
                font-size: 0.74rem !important;
            }

            .sku-card {
                padding: 14px 14px;
                border-radius: 13px;
                margin-bottom: 10px;
            }
            .sku-title {
                font-size: 1rem;
                margin-bottom: 6px;
            }
            .sku-line {
                font-size: 0.86rem;
                line-height: 1.5;
            }

            .stButton > button, .stFormSubmitButton > button {
                min-height: 46px;
                font-size: 0.92rem !important;
            }

            [data-testid="stDataFrame"] {
                font-size: 0.8rem !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

SALES_COLS = [
    "Date",
    "SR_Slot",
    "SR_Name",
    "Summary_Type",     # "Half Summary" বা "Full Summary"
    "Pen_Order_Pcs",
    "Stat_Order_Pcs",
    "Khata_Order_BDT",
    "Khata_Order_Ton",
    "Memo_Count",
    "Note",
]

TARGET_COLS = [
    "SR_Slot",
    "SR_Name",
    "Working_Days",
    "Pen_Monthly_Target_Pcs",
    "Stat_Monthly_Target_Pcs",
    "Khata_Monthly_Target_Ton",
]

INITIAL_TARGETS = [
    ["SR-1", "SR 1", 26, 5000.0, 3000.0, 2.5],
    ["SR-2", "SR 2", 26, 5000.0, 3000.0, 2.5],
    ["SR-3", "SR 3", 26, 5000.0, 3000.0, 2.5],
    ["SR-4", "SR 4", 26, 5000.0, 3000.0, 2.5],
    ["SR-5", "SR 5", 26, 5000.0, 3000.0, 2.5],
    ["SR-6", "SR 6", 26, 5000.0, 3000.0, 2.5],
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def safe_int(val, default=0, min_val=0):
    try:
        n = int(float(str(val).strip()))
        return n if n >= min_val else default
    except Exception:
        return default


def safe_float(val, default=0.0, min_val=0.0):
    try:
        n = float(str(val).strip())
        return n if n >= min_val else default
    except Exception:
        return default


@st.cache_resource
def connect_sheets():
    if "gcp_service_account" not in st.secrets:
        st.error("Streamlit Secrets-এ `gcp_service_account` পাওয়া যায়নি।")
        st.stop()

    raw = st.secrets["gcp_service_account"]
    creds_info = json.loads(raw) if isinstance(raw, str) else dict(raw)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    book = client.open(SPREADSHEET_NAME)

    try:
        sales_ws = book.worksheet(SALES_SHEET)
    except gspread.WorksheetNotFound:
        sales_ws = book.add_worksheet(title=SALES_SHEET, rows=1000, cols=12)
        sales_ws.append_row(SALES_COLS)

    if not sales_ws.get_all_values():
        sales_ws.append_row(SALES_COLS)

    try:
        target_ws = book.worksheet(TARGET_SHEET)
    except gspread.WorksheetNotFound:
        target_ws = book.add_worksheet(title=TARGET_SHEET, rows=20, cols=10)
        target_ws.append_row(TARGET_COLS)
        for r in INITIAL_TARGETS:
            target_ws.append_row(r)

    if not target_ws.get_all_values():
        target_ws.append_row(TARGET_COLS)
        for r in INITIAL_TARGETS:
            target_ws.append_row(r)

    return sales_ws, target_ws


def read_targets(target_ws):
    vals = target_ws.get_all_values()
    if len(vals) <= 1:
        df = pd.DataFrame(INITIAL_TARGETS, columns=TARGET_COLS)
    else:
        rows = [(r + [""] * len(TARGET_COLS))[: len(TARGET_COLS)] for r in vals[1:]]
        df = pd.DataFrame(rows, columns=TARGET_COLS)

    df = df.head(6).copy()
    while len(df) < 6:
        idx = len(df)
        df = pd.concat([df, pd.DataFrame([INITIAL_TARGETS[idx]], columns=TARGET_COLS)], ignore_index=True)

    df["SR_Slot"] = [f"SR-{i+1}" for i in range(6)]
    df["SR_Name"] = [
        str(x).strip() if str(x).strip() else f"SR {i+1}"
        for i, x in enumerate(df["SR_Name"])
    ]
    df["Working_Days"] = df["Working_Days"].apply(lambda v: safe_int(v, DEFAULT_DAYS, 1))
    for col in ["Pen_Monthly_Target_Pcs", "Stat_Monthly_Target_Pcs", "Khata_Monthly_Target_Ton"]:
        df[col] = df[col].apply(lambda v: safe_float(v, 0.0, 0.0))

    df["Khata_Monthly_Target_BDT"] = df["Khata_Monthly_Target_Ton"] * KHATA_RATE_PER_TON
    return df


def save_targets(target_ws, df):
    target_ws.clear()
    target_ws.append_row(TARGET_COLS)
    for i in range(6):
        r = df.iloc[i]
        target_ws.append_row([
            f"SR-{i+1}",
            str(r["SR_Name"]).strip() or f"SR {i+1}",
            safe_int(r["Working_Days"], DEFAULT_DAYS, 1),
            round(float(r["Pen_Monthly_Target_Pcs"]), 2),
            round(float(r["Stat_Monthly_Target_Pcs"]), 2),
            round(float(r["Khata_Monthly_Target_Ton"]), 4),
        ])


def read_sales(sales_ws):
    vals = sales_ws.get_all_values()
    if len(vals) <= 1:
        return pd.DataFrame(columns=SALES_COLS + ["Dt"])

    rows = [(r + [""] * len(SALES_COLS))[: len(SALES_COLS)] for r in vals[1:]]
    df = pd.DataFrame(rows, columns=SALES_COLS)

    for col in ["Date", "SR_Slot", "SR_Name", "Summary_Type", "Note"]:
        df[col] = df[col].astype(str).str.strip()

    df["Summary_Type"] = df["Summary_Type"].replace("", "Full Summary")
    for col in ["Pen_Order_Pcs", "Stat_Order_Pcs", "Khata_Order_BDT", "Khata_Order_Ton"]:
        df[col] = df[col].apply(lambda v: safe_float(v, 0.0, 0.0))

    missing_ton_mask = (df["Khata_Order_BDT"] > 0) & (df["Khata_Order_Ton"] <= 0)
    df.loc[missing_ton_mask, "Khata_Order_Ton"] = df.loc[missing_ton_mask, "Khata_Order_BDT"] / KHATA_RATE_PER_TON

    df["Memo_Count"] = df["Memo_Count"].apply(lambda v: safe_int(v, 0, 0))
    df["Dt"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    return df


def effective_day_rows(df_sr_day):
    """একই দিনে Full Summary থাকলে সেটি নেয়, না থাকলে Half Summary নেয়।"""
    if df_sr_day.empty:
        return df_sr_day
    full_rows = df_sr_day[df_sr_day["Summary_Type"] == "Full Summary"]
    return full_rows if not full_rows.empty else df_sr_day


def effective_month_rows(df_month, sr_slot):
    """মাসের প্রতিদিনের কার্যকর এন্ট্রি বের করে।"""
    if df_month.empty:
        return pd.DataFrame(columns=SALES_COLS)
    sub = df_month[df_month["SR_Slot"] == sr_slot]
    if sub.empty:
        return pd.DataFrame(columns=SALES_COLS)
    chunks = [effective_day_rows(grp) for _, grp in sub.groupby("Date", sort=False)]
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=SALES_COLS)


try:
    sales_ws, target_ws = connect_sheets()
    targets_df = read_targets(target_ws)
    sales_df = read_sales(sales_ws)
except Exception as e:
    st.error(f"Google Sheets সংযোগে সমস্যা: {e}")
    st.stop()

st.sidebar.title("📊 মেনু / Navigation")
mode = st.sidebar.radio(
    "ভিউ নির্বাচন করুন",
    ["SR এন্ট্রি ও আমার রিপোর্ট", "TSM ড্যাশবোর্ড (সব SR ও টোটাল)"],
)
selected_date = st.sidebar.date_input("রিপোর্টের তারিখ", value=date.today())
sel_date_str = str(selected_date)
month_prefix = sel_date_str[:7]

if sales_df.empty:
    day_df = pd.DataFrame(columns=SALES_COLS)
    month_df = pd.DataFrame(columns=SALES_COLS)
else:
    day_df = sales_df[sales_df["Date"] == sel_date_str]
    month_df = sales_df[sales_df["Date"].str.startswith(month_prefix)]


def build_summary(t_df, d_df, m_df):
    records = []
    for _, row in t_df.iterrows():
        slot = row["SR_Slot"]
        name = row["SR_Name"]
        days = safe_int(row["Working_Days"], DEFAULT_DAYS, 1)

        pen_m_tgt = float(row["Pen_Monthly_Target_Pcs"])
        stat_m_tgt = float(row["Stat_Monthly_Target_Pcs"])
        khata_m_tgt_ton = float(row["Khata_Monthly_Target_Ton"])
        khata_m_tgt_bdt = khata_m_tgt_ton * KHATA_RATE_PER_TON

        pen_d_tgt = pen_m_tgt / days
        stat_d_tgt = stat_m_tgt / days
        khata_d_tgt_bdt = khata_m_tgt_bdt / days

        raw_sd = d_df[d_df["SR_Slot"] == slot] if not d_df.empty else pd.DataFrame(columns=SALES_COLS)
        sd = effective_day_rows(raw_sd)
        sm = effective_month_rows(m_df, slot)

        pen_d_ord = sd["Pen_Order_Pcs"].sum() if not sd.empty else 0.0
        stat_d_ord = sd["Stat_Order_Pcs"].sum() if not sd.empty else 0.0
        khata_d_ord_bdt = sd["Khata_Order_BDT"].sum() if not sd.empty else 0.0
        d_memo = int(sd["Memo_Count"].sum()) if not sd.empty else 0

        pen_d_short = max(0.0, pen_d_tgt - pen_d_ord)
        stat_d_short = max(0.0, stat_d_tgt - stat_d_ord)
        khata_d_short_bdt = max(0.0, khata_d_tgt_bdt - khata_d_ord_bdt)

        pen_m_sales = sm["Pen_Order_Pcs"].sum() if not sm.empty else 0.0
        stat_m_sales = sm["Stat_Order_Pcs"].sum() if not sm.empty else 0.0
        khata_m_sales_bdt = sm["Khata_Order_BDT"].sum() if not sm.empty else 0.0
        khata_m_sales_ton = khata_m_sales_bdt / KHATA_RATE_PER_TON
        m_memo = int(sm["Memo_Count"].sum()) if not sm.empty else 0

        records.append({
            "SR_Slot": slot,
            "SR_Name": name,
            "Working_Days": days,
            "Pen_M_Target": pen_m_tgt,
            "Stat_M_Target": stat_m_tgt,
            "Khata_M_Target_Ton": khata_m_tgt_ton,
            "Khata_M_Target_BDT": khata_m_tgt_bdt,
            "Pen_M_Sales": pen_m_sales,
            "Stat_M_Sales": stat_m_sales,
            "Khata_M_Sales_BDT": khata_m_sales_bdt,
            "Khata_M_Sales_Ton": khata_m_sales_ton,
            "Month_Memo": m_memo,
            "Pen_D_Target": pen_d_tgt,
            "Stat_D_Target": stat_d_tgt,
            "Khata_D_Target_BDT": khata_d_tgt_bdt,
            "Pen_D_Order": pen_d_ord,
            "Stat_D_Order": stat_d_ord,
            "Khata_D_Order_BDT": khata_d_ord_bdt,
            "Pen_D_Shortfall": pen_d_short,
            "Stat_D_Shortfall": stat_d_short,
            "Khata_D_Shortfall_BDT": khata_d_short_bdt,
            "Day_Memo": d_memo,
        })
    return pd.DataFrame(records)


summary_df = build_summary(targets_df, day_df, month_df)

# ==============================================================================
# VIEW 1: SR SELF-ENTRY & INDIVIDUAL REPORT
# ==============================================================================
if mode == "SR এন্ট্রি ও আমার রিপোর্ট":
    st.markdown(
        """
        <div class="hero-box">
            <h1>SR সেলস এন্ট্রি ও ব্যক্তিগত রিপোর্ট</h1>
            <p>১ম বক্সে মাসিক টার্গেট (খাতা: টন ও টাকা) ও মাসিক সেলস দেখুন; ২য় বক্সে ডেইলি টার্গেট, খাতার টাকা সেলস, শর্টফল, মেমো ও সামারি দিন</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sr_options = [f"{r['SR_Slot']} — {r['SR_Name']}" for _, r in targets_df.iterrows()]
    chosen = st.selectbox("আপনার SR আইডি নির্বাচন করুন", sr_options)
    sr_idx = sr_options.index(chosen)
    t_row = targets_df.iloc[sr_idx]
    s_row = summary_df.iloc[sr_idx]
    sr_slot = t_row["SR_Slot"]
    sr_name = t_row["SR_Name"]

    # --- BOX 1: MONTHLY TARGET & MONTHLY SALES BOX ---
    st.markdown('<div class="section-heading">📦 ১. মাসিক টার্গেট ও মাসিক সেলস বক্স</div>', unsafe_allow_html=True)
    with st.container(border=True):
        with st.form(f"monthly_target_form_{sr_idx}"):
            st.caption("মাসিক টার্গেট সেট করুন (১ টন খাতা = ২,০০,০০০ টাকা হিসেবে টাকা অটো দেখাবে)")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                new_name = st.text_input("SR নাম", value=sr_name)
            with c2:
                new_days = st.number_input("কার্যদিবস (Working Days)", min_value=1, max_value=31, value=safe_int(t_row["Working_Days"], DEFAULT_DAYS, 1), step=1)
            with c3:
                new_pen_t = st.number_input("কলম মাসিক টার্গেট (Pcs)", min_value=0.0, value=float(t_row["Pen_Monthly_Target_Pcs"]), step=100.0, format="%.0f")
            with c4:
                new_stat_t = st.number_input("স্টেশনারি মাসিক টার্গেট (Pcs)", min_value=0.0, value=float(t_row["Stat_Monthly_Target_Pcs"]), step=100.0, format="%.0f")

            c5, c6, c7 = st.columns([1.2, 1.3, 1.5])
            with c5:
                new_khata_t_ton = st.number_input("খাতা মাসিক টার্গেট (Ton)", min_value=0.0, value=float(t_row["Khata_Monthly_Target_Ton"]), step=0.25, format="%.2f")
            with c6:
                auto_khata_tgt_bdt = new_khata_t_ton * KHATA_RATE_PER_TON
                st.metric("খাতা মাসিক টার্গেট (অটো টাকা)", f"৳{auto_khata_tgt_bdt:,.0f}")
            with c7:
                st.write("")
                save_t_btn = st.form_submit_button("মাসিক টার্গেট সংরক্ষণ করুন")

            if save_t_btn:
                updated = targets_df.copy()
                updated.loc[sr_idx, "SR_Name"] = new_name.strip() or f"SR {sr_idx + 1}"
                updated.loc[sr_idx, "Working_Days"] = int(new_days)
                updated.loc[sr_idx, "Pen_Monthly_Target_Pcs"] = float(new_pen_t)
                updated.loc[sr_idx, "Stat_Monthly_Target_Pcs"] = float(new_stat_t)
                updated.loc[sr_idx, "Khata_Monthly_Target_Ton"] = float(new_khata_t_ton)
                save_targets(target_ws, updated)
                st.success("মাসিক টার্গেট সেভ হয়েছে!")
                st.rerun()

        st.markdown(f"**মাসিক সেলস বক্স ({month_prefix} — দৈনিক এন্ট্রি থেকে অটো যোগ ও টন রূপান্তর):**")
        m1, m2, m3 = st.columns(3)
        m1.metric("কলম মাসিক সেলস / টার্গেট", f"{s_row['Pen_M_Sales']:,.0f} / {s_row['Pen_M_Target']:,.0f} Pcs")
        m2.metric("স্টেশনারি মাসিক সেলস / টার্গেট", f"{s_row['Stat_M_Sales']:,.0f} / {s_row['Stat_M_Target']:,.0f} Pcs")
        m3.metric(
            "খাতা মাসিক সেলস (টাকা ও টন)",
            f"৳{s_row['Khata_M_Sales_BDT']:,.0f} ({s_row['Khata_M_Sales_Ton']:,.2f} Ton)",
            f"টার্গেট: ৳{s_row['Khata_M_Target_BDT']:,.0f} ({s_row['Khata_M_Target_Ton']:,.2f} Ton)",
        )

    # --- BOX 2: DAILY TARGET, ORDER (KHATA IN BDT), SHORTFALL, MEMO & SUMMARY ---
    st.markdown(f'<div class="section-heading">📝 ২. ডেইলি বক্স — টার্গেট, সেলস, শর্টফল, মেমো ও সামারি ({sel_date_str})</div>', unsafe_allow_html=True)
    with st.container(border=True):
        d1, d2, d3 = st.columns(3)
        d1.metric("কলম ডেইলি টার্গেট", f"{s_row['Pen_D_Target']:,.0f} Pcs", f"সেলস: {s_row['Pen_D_Order']:,.0f} | শর্টফল: {s_row['Pen_D_Shortfall']:,.0f}")
        d2.metric("স্টেশনারি ডেইলি টার্গেট", f"{s_row['Stat_D_Target']:,.0f} Pcs", f"সেলস: {s_row['Stat_D_Order']:,.0f} | শর্টফল: {s_row['Stat_D_Shortfall']:,.0f}")
        d3.metric("খাতা ডেইলি টার্গেট (BDT)", f"৳{s_row['Khata_D_Target_BDT']:,.0f}", f"সেলস: ৳{s_row['Khata_D_Order_BDT']:,.0f} | শর্টফল: ৳{s_row['Khata_D_Shortfall_BDT']:,.0f}")

        st.divider()
        with st.form(f"daily_entry_form_{sr_idx}", clear_on_submit=True):
            st.caption("দৈনিক খাতা কত টাকার সেল হয়েছে তা টাকায় (BDT) লিখুন — মাসিক সেলসে টাকা ও অটো টন যুক্ত হবে")
            f1, f2, f3 = st.columns(3)
            with f1:
                entry_date = st.date_input("তারিখ", value=selected_date)
            with f2:
                summary_type = st.selectbox("সামারি ধরন", ["Half Summary", "Full Summary"])
            with f3:
                memo_cnt = st.number_input("ডেইলি মেমো সংখ্যা", min_value=0, value=0, step=1, format="%d")

            f4, f5, f6 = st.columns(3)
            with f4:
                pen_ord = st.number_input("কলম ডেইলি সেলস (Pcs)", min_value=0.0, value=0.0, step=10.0, format="%.0f")
            with f5:
                stat_ord = st.number_input("স্টেশনারি ডেইলি সেলস (Pcs)", min_value=0.0, value=0.0, step=10.0, format="%.0f")
            with f6:
                khata_ord_bdt = st.number_input("খাতা ডেইলি সেলস (BDT)", min_value=0.0, value=0.0, step=5000.0, format="%.0f")

            note_txt = st.text_input("এলাকা / নোট (ঐচ্ছিক)")
            submit_daily = st.form_submit_button("ডেইলি এন্ট্রি জমা দিন")

            if submit_daily:
                if pen_ord <= 0 and stat_ord <= 0 and khata_ord_bdt <= 0 and memo_cnt <= 0:
                    st.warning("অন্তত একটি সেলসের পরিমাণ বা মেমো সংখ্যা দিন।")
                else:
                    khata_ord_ton = float(khata_ord_bdt) / KHATA_RATE_PER_TON
                    sales_ws.append_row([
                        str(entry_date),
                        sr_slot,
                        sr_name,
                        summary_type,
                        round(float(pen_ord), 2),
                        round(float(stat_ord), 2),
                        round(float(khata_ord_bdt), 2),
                        round(khata_ord_ton, 4),
                        int(memo_cnt),
                        note_txt.strip(),
                    ])
                    st.success("ডেইলি এন্ট্রি সেভ হয়েছে এবং মাসিক সেলসে (টাকা ও টন) যোগ হয়েছে!")
                    st.rerun()

    st.markdown('<div class="section-heading">📋 আমার পূর্বের এন্ট্রিসমূহ</div>', unsafe_allow_html=True)
    my_logs = sales_df[sales_df["SR_Slot"] == sr_slot] if not sales_df.empty else pd.DataFrame(columns=SALES_COLS)
    if my_logs.empty:
        st.info("এখনও কোনো এন্ট্রি পাওয়া যায়নি।")
    else:
        st.dataframe(my_logs.drop(columns=["Dt"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)


# ==============================================================================
# VIEW 2: TSM DASHBOARD — ALL 6 SRs + SKU-WISE & GRAND TOTALS
# ==============================================================================
else:
    st.markdown(
        """
        <div class="hero-box">
            <h1>TSM ড্যাশবোর্ড — ৬ জন SR ও ৩টি SKU টোটাল</h1>
            <p>SKU-ভিত্তিক ডেইলি টার্গেট, ডেইলি সেলস, মাসিক সেলস (খাতা: টাকা ও টন) এবং ৬ জন SR-এর ব্যক্তিগত রিপোর্ট দেখুন</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    pen_d_tgt_tot = summary_df["Pen_D_Target"].sum()
    pen_d_ord_tot = summary_df["Pen_D_Order"].sum()
    pen_m_sales_tot = summary_df["Pen_M_Sales"].sum()
    pen_m_tgt_tot = summary_df["Pen_M_Target"].sum()

    stat_d_tgt_tot = summary_df["Stat_D_Target"].sum()
    stat_d_ord_tot = summary_df["Stat_D_Order"].sum()
    stat_m_sales_tot = summary_df["Stat_M_Sales"].sum()
    stat_m_tgt_tot = summary_df["Stat_M_Target"].sum()

    khata_d_tgt_bdt_tot = summary_df["Khata_D_Target_BDT"].sum()
    khata_d_ord_bdt_tot = summary_df["Khata_D_Order_BDT"].sum()
    khata_m_sales_bdt_tot = summary_df["Khata_M_Sales_BDT"].sum()
    khata_m_sales_ton_tot = khata_m_sales_bdt_tot / KHATA_RATE_PER_TON
    khata_m_tgt_bdt_tot = summary_df["Khata_M_Target_BDT"].sum()
    khata_m_tgt_ton_tot = summary_df["Khata_M_Target_Ton"].sum()

    st.markdown(f'<div class="section-heading">🎯 ৩টি SKU-ওয়াইজ টোটাল ({sel_date_str} ও মাস {month_prefix})</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            f"""
            <div class="sku-card sku-pen">
                <div class="sku-title">১. কলম (Pen — Pcs)</div>
                <div class="sku-line">• ডেইলি টোটাল টার্গেট: <b>{pen_d_tgt_tot:,.0f} Pcs</b></div>
                <div class="sku-line">• ডেইলি টোটাল সেলস: <b>{pen_d_ord_tot:,.0f} Pcs</b></div>
                <div class="sku-line">• মাসিক টোটাল সেলস: <b>{pen_m_sales_tot:,.0f} / {pen_m_tgt_tot:,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="sku-card sku-stat">
                <div class="sku-title">২. স্টেশনারি (Stationery — Pcs)</div>
                <div class="sku-line">• ডেইলি টোটাল টার্গেট: <b>{stat_d_tgt_tot:,.0f} Pcs</b></div>
                <div class="sku-line">• ডেইলি টোটাল সেলস: <b>{stat_d_ord_tot:,.0f} Pcs</b></div>
                <div class="sku-line">• মাসিক টোটাল সেলস: <b>{stat_m_sales_tot:,.0f} / {stat_m_tgt_tot:,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="sku-card sku-khata">
                <div class="sku-title">৩. খাতা / বুক (Khata — BDT &amp; Ton)</div>
                <div class="sku-line">• ডেইলি টোটাল টার্গেট: <b>৳{khata_d_tgt_bdt_tot:,.0f}</b></div>
                <div class="sku-line">• ডেইলি টোটাল সেলস: <b>৳{khata_d_ord_bdt_tot:,.0f}</b></div>
                <div class="sku-line">• মাসিক সেলস: <b>৳{khata_m_sales_bdt_tot:,.0f} ({khata_m_sales_ton_tot:,.2f} Ton)</b></div>
                <div class="sku-line">• মাসিক টার্গেট: <b>৳{khata_m_tgt_bdt_tot:,.0f} ({khata_m_tgt_ton_tot:,.2f} Ton)</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-heading">👥 ৬ জন SR-এর ব্যক্তিগত সামারি টেবিল</div>', unsafe_allow_html=True)
    display_cols = [
        "SR_Slot",
        "SR_Name",
        "Pen_D_Target",
        "Pen_D_Order",
        "Pen_D_Shortfall",
        "Pen_M_Sales",
        "Stat_D_Target",
        "Stat_D_Order",
        "Stat_D_Shortfall",
        "Stat_M_Sales",
        "Khata_D_Target_BDT",
        "Khata_D_Order_BDT",
        "Khata_D_Shortfall_BDT",
        "Khata_M_Sales_BDT",
        "Khata_M_Sales_Ton",
        "Khata_M_Target_Ton",
        "Day_Memo",
    ]
    total_row = pd.DataFrame([{
        "SR_Slot": "TOTAL",
        "SR_Name": "সব SR মোট",
        "Pen_D_Target": pen_d_tgt_tot,
        "Pen_D_Order": pen_d_ord_tot,
        "Pen_D_Shortfall": summary_df["Pen_D_Shortfall"].sum(),
        "Pen_M_Sales": pen_m_sales_tot,
        "Stat_D_Target": stat_d_tgt_tot,
        "Stat_D_Order": stat_d_ord_tot,
        "Stat_D_Shortfall": summary_df["Stat_D_Shortfall"].sum(),
        "Stat_M_Sales": stat_m_sales_tot,
        "Khata_D_Target_BDT": khata_d_tgt_bdt_tot,
        "Khata_D_Order_BDT": khata_d_ord_bdt_tot,
        "Khata_D_Shortfall_BDT": summary_df["Khata_D_Shortfall_BDT"].sum(),
        "Khata_M_Sales_BDT": khata_m_sales_bdt_tot,
        "Khata_M_Sales_Ton": khata_m_sales_ton_tot,
        "Khata_M_Target_Ton": khata_m_tgt_ton_tot,
        "Day_Memo": int(summary_df["Day_Memo"].sum()),
    }])
    st.dataframe(
        pd.concat([summary_df[display_cols], total_row[display_cols]], ignore_index=True),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-heading">🗂️ সব এন্ট্রি লগ</div>', unsafe_allow_html=True)
    if sales_df.empty:
        st.info("এখনও কোনো এন্ট্রি জমা পড়েনি।")
    else:
        st.dataframe(sales_df.drop(columns=["Dt"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)
