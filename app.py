import json
from datetime import date, timedelta
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="TSM Sales Tracker", layout="wide")

# --- Colorful & Mobile Responsive Styling ---
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 40%, #f1f5f9 100%);
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2.5rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
        }

        .hero-box {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #0ea5e9 100%);
            color: #ffffff;
            padding: 18px 22px;
            border-radius: 16px;
            margin-bottom: 16px;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.16);
        }

        .hero-box h1 {
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.8rem !important;
            font-weight: 800 !important;
        }

        .hero-box p {
            color: #e0f2fe !important;
            margin: 6px 0 0 0 !important;
            font-size: 0.9rem !important;
        }

        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-top: 4px solid #2563eb;
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
        }

        [data-testid="stMetricLabel"] > div {
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            color: #334155 !important;
        }

        [data-testid="stMetricValue"] > div {
            font-size: 1.3rem !important;
            font-weight: 800 !important;
            color: #0f172a !important;
        }

        .sku-card {
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
            color: #0f172a;
        }

        .sku-pen {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 5px solid #2563eb;
        }

        .sku-stat {
            background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
            border-left: 5px solid #7c3aed;
        }

        .sku-khata {
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
            border-left: 5px solid #059669;
        }

        .session-half {
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
            border-left: 5px solid #d97706;
        }

        .session-full {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-left: 5px solid #0284c7;
        }

        .sku-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 8px;
        }

        .sku-line {
            font-size: 0.9rem;
            margin: 4px 0;
            line-height: 1.45;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            flex-wrap: wrap;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 8px 16px;
            font-weight: 700;
            background-color: #ffffff;
            border: 1px solid #cbd5e1;
            color: #334155;
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            border-color: #1d4ed8 !important;
        }

        .stButton > button, .stFormSubmitButton > button {
            border-radius: 10px;
            font-weight: 700;
            width: 100%;
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: #ffffff;
            border: none;
            padding: 0.55rem 1rem;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #cbd5e1;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.85rem;
                padding-bottom: 2rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }

            .hero-box {
                padding: 14px 16px;
                border-radius: 12px;
            }

            .hero-box h1 {
                font-size: 1.35rem !important;
            }

            .hero-box p {
                font-size: 0.8rem !important;
            }

            [data-testid="stMetric"] {
                padding: 10px 10px;
                border-radius: 10px;
                margin-bottom: 6px;
            }

            [data-testid="stMetricLabel"] > div {
                font-size: 0.74rem !important;
            }

            [data-testid="stMetricValue"] > div {
                font-size: 1.05rem !important;
            }

            .stTabs [data-baseweb="tab"] {
                padding: 6px 10px;
                font-size: 0.8rem !important;
                flex: 1 1 46%;
                text-align: center;
            }

            .sku-card {
                padding: 12px 14px;
            }

            [data-testid="stDataFrame"] {
                font-size: 0.78rem !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

SPREADSHEET_NAME = "TSM_Sales_Database"
SALES_SHEET = "Sales_Data"
CONFIG_SHEET = "SR_Config"
KHATA_RATE_PER_TON = 200000.0
DEFAULT_DAYS = 26

SALES_COLS = [
    "Date",
    "Session",
    "SR_Name",
    "SKU",
    "Qty",
    "Unit",
    "Rate",
    "Total_BDT",
    "Khata_Ton",
    "Memo",
    "Note",
]

CONFIG_COLS = [
    "SR_Slot",
    "SR_Name",
    "Working_Days",
    "Pen_Monthly_Pcs",
    "Pen_Rate",
    "Stationery_Monthly_Pcs",
    "Stationery_Rate",
    "Khata_Monthly_Ton",
]

INITIAL_SRS = [
    ["SR-1", "SR 1", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
    ["SR-2", "SR 2", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
    ["SR-3", "SR 3", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
    ["SR-4", "SR 4", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
    ["SR-5", "SR 5", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
    ["SR-6", "SR 6", 26, 5000.0, 10.0, 3000.0, 25.0, 5.0],
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def safe_int(val, default=26, min_val=1):
    try:
        n = int(float(str(val).strip()))
        return n if n >= min_val else default
    except Exception:
        return default


def safe_num(val, default=0.0, min_val=0.0):
    try:
        n = float(str(val).strip())
        return n if n >= min_val else default
    except Exception:
        return default


@st.cache_resource
def connect_sheets():
    if "gcp_service_account" not in st.secrets:
        st.error("`gcp_service_account` not found in Streamlit Secrets.")
        st.stop()

    raw = st.secrets["gcp_service_account"]
    creds_info = json.loads(raw) if isinstance(raw, str) else dict(raw)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    book = client.open(SPREADSHEET_NAME)

    try:
        sales_ws = book.worksheet(SALES_SHEET)
    except gspread.WorksheetNotFound:
        sales_ws = book.add_worksheet(title=SALES_SHEET, rows=500, cols=15)
        sales_ws.append_row(SALES_COLS)

    if not sales_ws.get_all_values():
        sales_ws.append_row(SALES_COLS)

    try:
        cfg_ws = book.worksheet(CONFIG_SHEET)
    except gspread.WorksheetNotFound:
        cfg_ws = book.add_worksheet(title=CONFIG_SHEET, rows=20, cols=10)
        cfg_ws.append_row(CONFIG_COLS)
        for r in INITIAL_SRS:
            cfg_ws.append_row(r)

    if not cfg_ws.get_all_values():
        cfg_ws.append_row(CONFIG_COLS)
        for r in INITIAL_SRS:
            cfg_ws.append_row(r)

    return sales_ws, cfg_ws


def read_config(cfg_ws):
    vals = cfg_ws.get_all_values()
    if len(vals) <= 1:
        df_c = pd.DataFrame(INITIAL_SRS, columns=CONFIG_COLS)
    else:
        rows = [(r + [""] * len(CONFIG_COLS))[: len(CONFIG_COLS)] for r in vals[1:]]
        df_c = pd.DataFrame(rows, columns=CONFIG_COLS)

    df_c = df_c.head(6).copy()
    while len(df_c) < 6:
        idx = len(df_c)
        df_c = pd.concat([df_c, pd.DataFrame([INITIAL_SRS[idx]], columns=CONFIG_COLS)], ignore_index=True)

    df_c["SR_Slot"] = [f"SR-{i+1}" for i in range(6)]
    df_c["SR_Name"] = [
        str(x).strip() if str(x).strip() else f"SR {i+1}"
        for i, x in enumerate(df_c["SR_Name"])
    ]
    df_c["Working_Days"] = df_c["Working_Days"].apply(lambda v: safe_int(v, DEFAULT_DAYS, 1))
    for col in ["Pen_Monthly_Pcs", "Pen_Rate", "Stationery_Monthly_Pcs", "Stationery_Rate", "Khata_Monthly_Ton"]:
        df_c[col] = df_c[col].apply(safe_num)
    return df_c


def read_sales(sales_ws):
    vals = sales_ws.get_all_values()
    if len(vals) <= 1:
        return pd.DataFrame(columns=SALES_COLS)

    rows = [(r + [""] * len(SALES_COLS))[: len(SALES_COLS)] for r in vals[1:]]
    df_s = pd.DataFrame(rows, columns=SALES_COLS)

    for col in ["Date", "Session", "SR_Name", "SKU", "Unit", "Note"]:
        df_s[col] = df_s[col].astype(str).str.strip()

    df_s["Session"] = df_s["Session"].replace("", "Full Summary")
    for col in ["Qty", "Rate", "Total_BDT", "Khata_Ton"]:
        df_s[col] = df_s[col].apply(safe_num)
    df_s["Memo"] = df_s["Memo"].apply(lambda v: safe_int(v, 0, 0))
    df_s["Dt"] = pd.to_datetime(df_s["Date"], errors="coerce").dt.date
    return df_s


st.markdown(
    """
    <div class="hero-box">
        <h1>TSM Sales Tracker</h1>
        <p>6 SRs • Pen (Pcs + Rate), Stationery (Pcs + Rate) &amp; Khata (Ton @ 200,000 BDT) • Daily, Weekly &amp; Monthly Reports • Half &amp; Full Summary</p>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    sales_ws, cfg_ws = connect_sheets()
    cfg_df = read_config(cfg_ws)
    sales_df = read_sales(sales_ws)
except Exception as err:
    st.error(f"Google Sheets connection error: {err}")
    st.stop()

# Clean any stale session keys that could conflict with input types
for stale_key in list(st.session_state.keys()):
    if stale_key.startswith(("dy_", "nm_", "pm_", "pr_", "sm_", "sr_", "km_", "c_dy_")):
        del st.session_state[stale_key]

sr_names = cfg_df["SR_Name"].tolist()

# --- Sidebar: New Entry Form ---
st.sidebar.header("New Sales / Order Entry")
sku = st.sidebar.selectbox("Select SKU", ["Pen", "Stationery", "Khata"])

with st.sidebar.form("new_entry_form", clear_on_submit=True):
    e_date = st.date_input("Date", value=date.today())
    e_session = st.selectbox("Session", ["Half Summary", "Full Summary"])
    e_sr = st.selectbox("SR Name", sr_names)

    sr_info = cfg_df[cfg_df["SR_Name"] == e_sr].iloc[0]

    if sku == "Pen":
        q_val = st.number_input("Pen Quantity (Pcs)", min_value=0.0, step=10.0, format="%.0f")
        r_val = st.number_input("Pen Unit Rate (BDT)", min_value=0.0, value=float(sr_info["Pen_Rate"]), step=1.0, format="%.2f")
        tot_bdt = float(q_val) * float(r_val)
        k_ton = 0.0
        unit_str = "Pcs"
        st.caption(f"Pen Total Amount: **BDT {tot_bdt:,.0f}**")
    elif sku == "Stationery":
        q_val = st.number_input("Stationery Quantity (Pcs)", min_value=0.0, step=10.0, format="%.0f")
        r_val = st.number_input("Stationery Unit Rate (BDT)", min_value=0.0, value=float(sr_info["Stationery_Rate"]), step=1.0, format="%.2f")
        tot_bdt = float(q_val) * float(r_val)
        k_ton = 0.0
        unit_str = "Pcs"
        st.caption(f"Stationery Total Amount: **BDT {tot_bdt:,.0f}**")
    else:
        k_ton = st.number_input("Khata Quantity (Ton)", min_value=0.0, step=0.25, format="%.2f")
        r_val = KHATA_RATE_PER_TON
        tot_bdt = float(k_ton) * KHATA_RATE_PER_TON
        q_val = float(k_ton)
        unit_str = "Ton"
        st.caption(f"Khata Total Amount (1 Ton = 200,000 BDT): **BDT {tot_bdt:,.0f}**")

    m_val = st.number_input("Memos", min_value=0, step=1, format="%d")
    n_val = st.text_input("Area / Note (Optional)")
    save_btn = st.form_submit_button("Save to Google Sheet")

    if save_btn:
        if q_val <= 0 and tot_bdt <= 0:
            st.sidebar.warning("Quantity or amount must be greater than 0.")
        else:
            sales_ws.append_row([
                str(e_date),
                e_session,
                e_sr,
                sku,
                round(float(q_val), 4),
                unit_str,
                round(float(r_val), 2),
                round(float(tot_bdt), 2),
                round(float(k_ton), 4),
                int(m_val),
                n_val.strip(),
            ])
            st.sidebar.success("Saved to Google Sheet!")
            st.rerun()

# --- Report Date & Period Filters ---
rep_date = st.date_input("Report Date", value=date.today())
rep_date_str = str(rep_date)
wk_start = rep_date - timedelta(days=6)
mo_prefix = rep_date_str[:7]

if sales_df.empty:
    d_sub = pd.DataFrame(columns=SALES_COLS)
    w_sub = pd.DataFrame(columns=SALES_COLS)
    m_sub = pd.DataFrame(columns=SALES_COLS)
else:
    d_sub = sales_df[sales_df["Date"] == rep_date_str]
    w_sub = sales_df[(sales_df["Dt"] >= wk_start) & (sales_df["Dt"] <= rep_date)]
    m_sub = sales_df[sales_df["Date"].str.startswith(mo_prefix)]


def build_report(c_df, d_df, w_df, m_df):
    out = []
    for _, row in c_df.iterrows():
        sr = row["SR_Name"]
        days = safe_int(row["Working_Days"], DEFAULT_DAYS, 1)

        pen_mt = float(row["Pen_Monthly_Pcs"])
        pen_rt = float(row["Pen_Rate"])
        stat_mt = float(row["Stationery_Monthly_Pcs"])
        stat_rt = float(row["Stationery_Rate"])
        khata_mt_ton = float(row["Khata_Monthly_Ton"])
        khata_mt_bdt = khata_mt_ton * KHATA_RATE_PER_TON

        tot_mt_bdt = (pen_mt * pen_rt) + (stat_mt * stat_rt) + khata_mt_bdt
        tot_dt_bdt = tot_mt_bdt / days

        pen_dt = pen_mt / days
        stat_dt = stat_mt / days
        khata_dt_ton = khata_mt_ton / days

        sd = d_df[d_df["SR_Name"] == sr] if not d_df.empty else pd.DataFrame(columns=SALES_COLS)
        sh = sd[sd["Session"] == "Half Summary"]
        sf = sd[sd["Session"] == "Full Summary"]

        d_pen_pcs = sd[sd["SKU"] == "Pen"]["Qty"].sum()
        d_pen_bdt = sd[sd["SKU"] == "Pen"]["Total_BDT"].sum()
        d_stat_pcs = sd[sd["SKU"] == "Stationery"]["Qty"].sum()
        d_stat_bdt = sd[sd["SKU"] == "Stationery"]["Total_BDT"].sum()
        d_kh_ton = sd[sd["SKU"] == "Khata"]["Khata_Ton"].sum()
        d_kh_bdt = sd[sd["SKU"] == "Khata"]["Total_BDT"].sum()
        d_tot_bdt = sd["Total_BDT"].sum()
        d_memo = int(sd["Memo"].sum())

        d_short_bdt = max(0.0, tot_dt_bdt - d_tot_bdt)
        d_short_pen = max(0.0, pen_dt - d_pen_pcs)
        d_short_stat = max(0.0, stat_dt - d_stat_pcs)
        d_short_kh_ton = max(0.0, khata_dt_ton - d_kh_ton)

        sw = w_df[w_df["SR_Name"] == sr] if not w_df.empty else pd.DataFrame(columns=SALES_COLS)
        w_pen_pcs = sw[sw["SKU"] == "Pen"]["Qty"].sum()
        w_stat_pcs = sw[sw["SKU"] == "Stationery"]["Qty"].sum()
        w_kh_ton = sw[sw["SKU"] == "Khata"]["Khata_Ton"].sum()
        w_tot_bdt = sw["Total_BDT"].sum()
        w_memo = int(sw["Memo"].sum())
        w_short_bdt = max(0.0, (tot_dt_bdt * 7) - w_tot_bdt)

        sm = m_df[m_df["SR_Name"] == sr] if not m_df.empty else pd.DataFrame(columns=SALES_COLS)
        m_pen_pcs = sm[sm["SKU"] == "Pen"]["Qty"].sum()
        m_pen_bdt = sm[sm["SKU"] == "Pen"]["Total_BDT"].sum()
        m_stat_pcs = sm[sm["SKU"] == "Stationery"]["Qty"].sum()
        m_stat_bdt = sm[sm["SKU"] == "Stationery"]["Total_BDT"].sum()
        m_kh_ton = sm[sm["SKU"] == "Khata"]["Khata_Ton"].sum()
        m_kh_bdt = sm[sm["SKU"] == "Khata"]["Total_BDT"].sum()
        m_tot_bdt = sm["Total_BDT"].sum()
        m_memo = int(sm["Memo"].sum())

        m_short_bdt = max(0.0, tot_mt_bdt - m_tot_bdt)
        m_short_pen = max(0.0, pen_mt - m_pen_pcs)
        m_short_stat = max(0.0, stat_mt - m_stat_pcs)
        m_short_kh_ton = max(0.0, khata_mt_ton - m_kh_ton)

        ach_pct = (m_tot_bdt / tot_mt_bdt * 100.0) if tot_mt_bdt > 0 else 0.0
        short_pct = max(0.0, 100.0 - ach_pct) if tot_mt_bdt > 0 else 0.0

        out.append({
            "SR_Name": sr,
            "Days": days,
            "Half_BDT": sh["Total_BDT"].sum(),
            "Half_Memo": int(sh["Memo"].sum()),
            "Half_Pen_Pcs": sh[sh["SKU"] == "Pen"]["Qty"].sum(),
            "Half_Stat_Pcs": sh[sh["SKU"] == "Stationery"]["Qty"].sum(),
            "Half_Khata_BDT": sh[sh["SKU"] == "Khata"]["Total_BDT"].sum(),
            "Full_BDT": sf["Total_BDT"].sum(),
            "Full_Memo": int(sf["Memo"].sum()),
            "Full_Pen_Pcs": sf[sf["SKU"] == "Pen"]["Qty"].sum(),
            "Full_Stat_Pcs": sf[sf["SKU"] == "Stationery"]["Qty"].sum(),
            "Full_Khata_BDT": sf[sf["SKU"] == "Khata"]["Total_BDT"].sum(),
            "Day_Target_BDT": tot_dt_bdt,
            "Day_Sales_BDT": d_tot_bdt,
            "Day_Short_BDT": d_short_bdt,
            "Day_Memo": d_memo,
            "Day_Pen_Pcs": d_pen_pcs,
            "Day_Pen_BDT": d_pen_bdt,
            "Day_Short_Pen": d_short_pen,
            "Day_Stat_Pcs": d_stat_pcs,
            "Day_Stat_BDT": d_stat_bdt,
            "Day_Short_Stat": d_short_stat,
            "Day_Khata_Ton": d_kh_ton,
            "Day_Khata_BDT": d_kh_bdt,
            "Day_Short_Khata_Ton": d_short_kh_ton,
            "Week_Sales_BDT": w_tot_bdt,
            "Week_Short_BDT": w_short_bdt,
            "Week_Pen_Pcs": w_pen_pcs,
            "Week_Stat_Pcs": w_stat_pcs,
            "Week_Khata_Ton": w_kh_ton,
            "Week_Memo": w_memo,
            "Month_Target_BDT": tot_mt_bdt,
            "Month_Sales_BDT": m_tot_bdt,
            "Month_Short_BDT": m_short_bdt,
            "Ach_%": ach_pct,
            "Short_%": short_pct,
            "Month_Pen_Target": pen_mt,
            "Month_Pen_Pcs": m_pen_pcs,
            "Month_Pen_BDT": m_pen_bdt,
            "Month_Short_Pen": m_short_pen,
            "Month_Stat_Target": stat_mt,
            "Month_Stat_Pcs": m_stat_pcs,
            "Month_Stat_BDT": m_stat_bdt,
            "Month_Short_Stat": m_short_stat,
            "Month_Khata_Target_Ton": khata_mt_ton,
            "Month_Khata_Ton": m_kh_ton,
            "Month_Khata_BDT": m_kh_bdt,
            "Month_Short_Khata_Ton": m_short_kh_ton,
            "Month_Memo": m_memo,
        })
    return pd.DataFrame(out)


rep_df = build_report(cfg_df, d_sub, w_sub, m_sub)

t1, t2, t3, t4 = st.tabs([
    "Daily, Weekly & Monthly Report",
    "Half & Full Summary",
    "6 SR Setup",
    "Sales Log",
])

with t1:
    tot_dt = rep_df["Day_Target_BDT"].sum()
    tot_ds = rep_df["Day_Sales_BDT"].sum()
    tot_dsh = max(0.0, tot_dt - tot_ds)
    tot_ws = rep_df["Week_Sales_BDT"].sum()
    tot_wsh = rep_df["Week_Short_BDT"].sum()
    tot_mt = rep_df["Month_Target_BDT"].sum()
    tot_ms = rep_df["Month_Sales_BDT"].sum()
    tot_msh = max(0.0, tot_mt - tot_ms)
    tot_ach = (tot_ms / tot_mt * 100.0) if tot_mt > 0 else 0.0
    tot_shp = max(0.0, 100.0 - tot_ach) if tot_mt > 0 else 0.0

    st.subheader(f"Grand Total Summary ({rep_date_str})")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Daily Target", f"BDT {tot_dt:,.0f}")
    c2.metric("Daily Sales", f"BDT {tot_ds:,.0f}", f"Memo: {int(rep_df['Day_Memo'].sum())}")
    c3.metric("Daily Shortfall", f"BDT {tot_dsh:,.0f}")
    c4.metric("7-Day Sales", f"BDT {tot_ws:,.0f}", f"Shortfall: BDT {tot_wsh:,.0f}")
    c5.metric("Monthly Target", f"BDT {tot_mt:,.0f}")

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Monthly Sales", f"BDT {tot_ms:,.0f}", f"Memo: {int(rep_df['Month_Memo'].sum())}")
    c7.metric("Monthly Shortfall", f"BDT {tot_msh:,.0f}")
    c8.metric("Achievement %", f"{tot_ach:.1f}%")
    c9.metric("Shortfall %", f"{tot_shp:.1f}%")
    c10.metric("Total Khata", f"{rep_df['Month_Khata_Ton'].sum():,.2f} Ton")

    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(
            f"""
            <div class="sku-card sku-pen">
                <div class="sku-title">Pen (Pcs &amp; BDT)</div>
                <div class="sku-line">• Today: <b>{rep_df['Day_Pen_Pcs'].sum():,.0f} Pcs</b> (BDT {rep_df['Day_Pen_BDT'].sum():,.0f}) | Shortfall: <b>{rep_df['Day_Short_Pen'].sum():,.0f}</b></div>
                <div class="sku-line">• 7 Days: <b>{rep_df['Week_Pen_Pcs'].sum():,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{rep_df['Month_Pen_Pcs'].sum():,.0f} / {rep_df['Month_Pen_Target'].sum():,.0f} Pcs</b> (BDT {rep_df['Month_Pen_BDT'].sum():,.0f}) | Shortfall: <b>{rep_df['Month_Short_Pen'].sum():,.0f}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            f"""
            <div class="sku-card sku-stat">
                <div class="sku-title">Stationery (Pcs &amp; BDT)</div>
                <div class="sku-line">• Today: <b>{rep_df['Day_Stat_Pcs'].sum():,.0f} Pcs</b> (BDT {rep_df['Day_Stat_BDT'].sum():,.0f}) | Shortfall: <b>{rep_df['Day_Short_Stat'].sum():,.0f}</b></div>
                <div class="sku-line">• 7 Days: <b>{rep_df['Week_Stat_Pcs'].sum():,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{rep_df['Month_Stat_Pcs'].sum():,.0f} / {rep_df['Month_Stat_Target'].sum():,.0f} Pcs</b> (BDT {rep_df['Month_Stat_BDT'].sum():,.0f}) | Shortfall: <b>{rep_df['Month_Short_Stat'].sum():,.0f}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f"""
            <div class="sku-card sku-khata">
                <div class="sku-title">Khata (Ton @ 200,000 BDT)</div>
                <div class="sku-line">• Today: <b>{rep_df['Day_Khata_Ton'].sum():,.2f} Ton</b> (<b>BDT {rep_df['Day_Khata_BDT'].sum():,.0f}</b>) | Shortfall: <b>{rep_df['Day_Short_Khata_Ton'].sum():,.2f} Ton</b></div>
                <div class="sku-line">• 7 Days: <b>{rep_df['Week_Khata_Ton'].sum():,.2f} Ton</b></div>
                <div class="sku-line">• Monthly: <b>{rep_df['Month_Khata_Ton'].sum():,.2f} / {rep_df['Month_Khata_Target_Ton'].sum():,.2f} Ton</b> (<b>BDT {rep_df['Month_Khata_BDT'].sum():,.0f}</b>) | Shortfall: <b>{rep_df['Month_Short_Khata_Ton'].sum():,.2f} Ton</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    grand_row = pd.DataFrame([{
        "SR_Name": "GRAND TOTAL (6 SRs)",
        "Day_Target_BDT": tot_dt,
        "Day_Sales_BDT": tot_ds,
        "Day_Short_BDT": tot_dsh,
        "Day_Memo": int(rep_df["Day_Memo"].sum()),
        "Day_Pen_Pcs": rep_df["Day_Pen_Pcs"].sum(),
        "Day_Pen_BDT": rep_df["Day_Pen_BDT"].sum(),
        "Day_Stat_Pcs": rep_df["Day_Stat_Pcs"].sum(),
        "Day_Stat_BDT": rep_df["Day_Stat_BDT"].sum(),
        "Day_Khata_Ton": rep_df["Day_Khata_Ton"].sum(),
        "Day_Khata_BDT": rep_df["Day_Khata_BDT"].sum(),
        "Week_Sales_BDT": tot_ws,
        "Week_Short_BDT": tot_wsh,
        "Week_Pen_Pcs": rep_df["Week_Pen_Pcs"].sum(),
        "Week_Stat_Pcs": rep_df["Week_Stat_Pcs"].sum(),
        "Week_Khata_Ton": rep_df["Week_Khata_Ton"].sum(),
        "Week_Memo": int(rep_df["Week_Memo"].sum()),
        "Month_Target_BDT": tot_mt,
        "Month_Sales_BDT": tot_ms,
        "Month_Short_BDT": tot_msh,
        "Ach_%": tot_ach,
        "Short_%": tot_shp,
        "Month_Pen_Target": rep_df["Month_Pen_Target"].sum(),
        "Month_Pen_Pcs": rep_df["Month_Pen_Pcs"].sum(),
        "Month_Pen_BDT": rep_df["Month_Pen_BDT"].sum(),
        "Month_Short_Pen": rep_df["Month_Short_Pen"].sum(),
        "Month_Stat_Target": rep_df["Month_Stat_Target"].sum(),
        "Month_Stat_Pcs": rep_df["Month_Stat_Pcs"].sum(),
        "Month_Stat_BDT": rep_df["Month_Stat_BDT"].sum(),
        "Month_Short_Stat": rep_df["Month_Short_Stat"].sum(),
        "Month_Khata_Target_Ton": rep_df["Month_Khata_Target_Ton"].sum(),
        "Month_Khata_Ton": rep_df["Month_Khata_Ton"].sum(),
        "Month_Khata_BDT": rep_df["Month_Khata_BDT"].sum(),
        "Month_Short_Khata_Ton": rep_df["Month_Short_Khata_Ton"].sum(),
        "Month_Memo": int(rep_df["Month_Memo"].sum()),
    }])

    table_cols = [
        "SR_Name", "Day_Target_BDT", "Day_Sales_BDT", "Day_Short_BDT", "Day_Memo",
        "Day_Pen_Pcs", "Day_Pen_BDT", "Day_Stat_Pcs", "Day_Stat_BDT", "Day_Khata_Ton", "Day_Khata_BDT",
        "Week_Sales_BDT", "Week_Short_BDT", "Week_Pen_Pcs", "Week_Stat_Pcs", "Week_Khata_Ton", "Week_Memo",
        "Month_Target_BDT", "Month_Sales_BDT", "Month_Short_BDT", "Ach_%", "Short_%",
        "Month_Pen_Target", "Month_Pen_Pcs", "Month_Pen_BDT", "Month_Short_Pen",
        "Month_Stat_Target", "Month_Stat_Pcs", "Month_Stat_BDT", "Month_Short_Stat",
        "Month_Khata_Target_Ton", "Month_Khata_Ton", "Month_Khata_BDT", "Month_Short_Khata_Ton",
        "Month_Memo",
    ]
    st.dataframe(pd.concat([rep_df[table_cols], grand_row[table_cols]], ignore_index=True), width="stretch", hide_index=True)

with t2:
    st.subheader("Half Summary & Full Summary")
    pick_sr = st.selectbox("Select SR", sr_names)
    one = rep_df[rep_df["SR_Name"] == pick_sr].iloc[0]

    h_col, f_col = st.columns(2)
    with h_col:
        st.markdown(
            f"""
            <div class="sku-card session-half">
                <div class="sku-title">Half Summary — {pick_sr} ({rep_date_str})</div>
                <div class="sku-line">• Total Amount: <b>BDT {one['Half_BDT']:,.0f}</b> | Memos: <b>{int(one['Half_Memo'])}</b></div>
                <div class="sku-line">• Pen: <b>{one['Half_Pen_Pcs']:,.0f} Pcs</b> | Stationery: <b>{one['Half_Stat_Pcs']:,.0f} Pcs</b> | Khata: <b>BDT {one['Half_Khata_BDT']:,.0f}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f_col:
        st.markdown(
            f"""
            <div class="sku-card session-full">
                <div class="sku-title">Full Summary — {pick_sr} ({rep_date_str})</div>
                <div class="sku-line">• Total Amount: <b>BDT {one['Full_BDT']:,.0f}</b> | Memos: <b>{int(one['Full_Memo'])}</b></div>
                <div class="sku-line">• Pen: <b>{one['Full_Pen_Pcs']:,.0f} Pcs</b> | Stationery: <b>{one['Full_Stat_Pcs']:,.0f} Pcs</b> | Khata: <b>BDT {one['Full_Khata_BDT']:,.0f}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.dataframe(
        rep_df[[
            "SR_Name",
            "Half_BDT", "Half_Memo", "Half_Pen_Pcs", "Half_Stat_Pcs", "Half_Khata_BDT",
            "Full_BDT", "Full_Memo", "Full_Pen_Pcs", "Full_Stat_Pcs", "Full_Khata_BDT",
        ]],
        width="stretch",
        hide_index=True,
    )

with t3:
    st.subheader("6 SR Name, Working Days, Rate & Monthly Target Setup")
    with st.form("clean_cfg_form"):
        save_rows = []
        for i in range(6):
            r = cfg_df.iloc[i]
            st.markdown(f"**SR #{i+1}**")
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.6, 0.8, 1.3, 1.1, 1.3, 1.1, 1.3])
            with c1:
                s_nm = st.text_input("SR Name", value=str(r["SR_Name"]), key=f"clean_nm_{i}")
            with c2:
                s_dy = st.number_input("Working Days", min_value=1, value=safe_int(r["Working_Days"], DEFAULT_DAYS, 1), step=1, key=f"clean_dy_{i}")
            with c3:
                s_pm = st.number_input("Pen Monthly (Pcs)", min_value=0.0, value=float(r["Pen_Monthly_Pcs"]), step=100.0, format="%.0f", key=f"clean_pm_{i}")
            with c4:
                s_pr = st.number_input("Pen Rate (BDT)", min_value=0.0, value=float(r["Pen_Rate"]), step=1.0, format="%.2f", key=f"clean_pr_{i}")
            with c5:
                s_sm = st.number_input("Stationery Monthly (Pcs)", min_value=0.0, value=float(r["Stationery_Monthly_Pcs"]), step=100.0, format="%.0f", key=f"clean_sm_{i}")
            with c6:
                s_sr = st.number_input("Stationery Rate (BDT)", min_value=0.0, value=float(r["Stationery_Rate"]), step=1.0, format="%.2f", key=f"clean_sr_{i}")
            with c7:
                s_km = st.number_input("Khata Monthly (Ton)", min_value=0.0, value=float(r["Khata_Monthly_Ton"]), step=0.25, format="%.2f", key=f"clean_km_{i}")

            save_rows.append([
                f"SR-{i+1}",
                s_nm.strip() or f"SR {i+1}",
                safe_int(s_dy, DEFAULT_DAYS, 1),
                float(s_pm),
                float(s_pr),
                float(s_sm),
                float(s_sr),
                float(s_km),
            ])

        if st.form_submit_button("Save Setup"):
            cfg_ws.clear()
            cfg_ws.append_row(CONFIG_COLS)
            for sr_row in save_rows:
                cfg_ws.append_row(sr_row)
            st.success("6 SR setup saved!")
            st.rerun()

with t4:
    st.subheader("Sales Log")
    if sales_df.empty:
        st.info("No sales records found yet.")
    else:
        st.dataframe(sales_df.drop(columns=["Dt"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)
