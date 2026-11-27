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
    "Delivery_BDT",
    "Khata_Ton",
    "Delivery_Khata_Ton",
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
        sales_ws = book.add_worksheet(title=SALES_SHEET, rows=500, cols=16)
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


def write_config_all(cfg_ws, df_c):
    cfg_ws.clear()
    cfg_ws.append_row(CONFIG_COLS)
    for i in range(6):
        r = df_c.iloc[i]
        cfg_ws.append_row([
            f"SR-{i+1}",
            str(r["SR_Name"]).strip() or f"SR {i+1}",
            safe_int(r["Working_Days"], DEFAULT_DAYS, 1),
            float(r["Pen_Monthly_Pcs"]),
            float(r["Pen_Rate"]),
            float(r["Stationery_Monthly_Pcs"]),
            float(r["Stationery_Rate"]),
            float(r["Khata_Monthly_Ton"]),
        ])


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
    for col in ["Qty", "Rate", "Total_BDT", "Delivery_BDT", "Khata_Ton", "Delivery_Khata_Ton"]:
        df_s[col] = df_s[col].apply(safe_num)

    raw_deliv = pd.Series(rows, columns=SALES_COLS)["Delivery_BDT"].astype(str).str.strip()
    df_s.loc[raw_deliv == "", "Delivery_BDT"] = df_s.loc[raw_deliv == "", "Total_BDT"]

    raw_deliv_ton = pd.Series(rows, columns=SALES_COLS)["Delivery_Khata_Ton"].astype(str).str.strip()
    df_s.loc[raw_deliv_ton == "", "Delivery_Khata_Ton"] = df_s.loc[raw_deliv_ton == "", "Khata_Ton"]

    df_s["Memo"] = df_s["Memo"].apply(lambda v: safe_int(v, 0, 0))
    df_s["Dt"] = pd.to_datetime(df_s["Date"], errors="coerce").dt.date
    return df_s


def effective_sr_day_rows(df_sr_day):
    if df_sr_day.empty:
        return df_sr_day
    full_rows = df_sr_day[df_sr_day["Session"] == "Full Summary"]
    return full_rows if not full_rows.empty else df_sr_day


def effective_period_rows(df_period, sr_name):
    if df_period.empty:
        return pd.DataFrame(columns=SALES_COLS)
    sub = df_period[df_period["SR_Name"] == sr_name]
    if sub.empty:
        return pd.DataFrame(columns=SALES_COLS)
    chunks = [effective_sr_day_rows(day_grp) for _, day_grp in sub.groupby("Date", sort=False)]
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=SALES_COLS)


try:
    sales_ws, cfg_ws = connect_sheets()
    cfg_df = read_config(cfg_ws)
    sales_df = read_sales(sales_ws)
except Exception as err:
    st.error(f"Google Sheets connection error: {err}")
    st.stop()

sr_names = cfg_df["SR_Name"].tolist()

st.sidebar.title("Navigation")
view_mode = st.sidebar.radio("Choose View", ["SR Self-Entry & My Report", "TSM All SRs & Total"])
rep_date = st.sidebar.date_input("Report Date", value=date.today())
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
    rows = []
    for _, r in c_df.iterrows():
        sr = r["SR_Name"]
        days = safe_int(r["Working_Days"], DEFAULT_DAYS, 1)

        pen_mt = float(r["Pen_Monthly_Pcs"])
        pen_rt = float(r["Pen_Rate"])
        stat_mt = float(r["Stationery_Monthly_Pcs"])
        stat_rt = float(r["Stationery_Rate"])
        kh_mt_ton = float(r["Khata_Monthly_Ton"])
        kh_mt_bdt = kh_mt_ton * KHATA_RATE_PER_TON

        m_target = (pen_mt * pen_rt) + (stat_mt * stat_rt) + kh_mt_bdt
        d_target = m_target / days

        raw_sd = d_df[d_df["SR_Name"] == sr] if not d_df.empty else pd.DataFrame(columns=SALES_COLS)
        sd = effective_sr_day_rows(raw_sd)
        sw = effective_period_rows(w_df, sr)
        sm = effective_period_rows(m_df, sr)

        d_sales = sd["Total_BDT"].sum() if not sd.empty else 0.0
        d_deliv = sd["Delivery_BDT"].sum() if not sd.empty else 0.0
        d_memo = int(sd["Memo"].sum()) if not sd.empty else 0
        d_short = max(0.0, d_target - d_sales)

        w_sales = sw["Total_BDT"].sum() if not sw.empty else 0.0
        w_deliv = sw["Delivery_BDT"].sum() if not sw.empty else 0.0
        w_memo = int(sw["Memo"].sum()) if not sw.empty else 0

        m_sales = sm["Total_BDT"].sum() if not sm.empty else 0.0
        m_deliv = sm["Delivery_BDT"].sum() if not sm.empty else 0.0
        m_memo = int(sm["Memo"].sum()) if not sm.empty else 0
        m_short = max(0.0, m_target - m_sales)
        ach_pct = (m_sales / m_target * 100.0) if m_target > 0 else 0.0

        rows.append({
            "SR_Name": sr,
            "Days": days,
            "Day_Target": d_target,
            "Day_Sales": d_sales,
            "Day_Delivery": d_deliv,
            "Day_Shortfall": d_short,
            "Day_Memo": d_memo,
            "Week_Sales": w_sales,
            "Week_Delivery": w_deliv,
            "Week_Memo": w_memo,
            "Month_Target": m_target,
            "Month_Sales": m_sales,
            "Month_Delivery": m_deliv,
            "Month_Shortfall": m_short,
            "Ach_%": ach_pct,
            "Month_Memo": m_memo,
            "Pen_Monthly_Pcs": pen_mt,
            "Pen_Rate": pen_rt,
            "Stationery_Monthly_Pcs": stat_mt,
            "Stationery_Rate": stat_rt,
            "Khata_Monthly_Ton": kh_mt_ton,
            "Day_Pen_Pcs": sd[sd["SKU"] == "Pen"]["Qty"].sum() if not sd.empty else 0.0,
            "Day_Stat_Pcs": sd[sd["SKU"] == "Stationery"]["Qty"].sum() if not sd.empty else 0.0,
            "Day_Khata_Ton": sd[sd["SKU"] == "Khata"]["Khata_Ton"].sum() if not sd.empty else 0.0,
            "Day_Deliv_Khata_Ton": sd[sd["SKU"] == "Khata"]["Delivery_Khata_Ton"].sum() if not sd.empty else 0.0,
            "Month_Pen_Pcs": sm[sm["SKU"] == "Pen"]["Qty"].sum() if not sm.empty else 0.0,
            "Month_Stat_Pcs": sm[sm["SKU"] == "Stationery"]["Qty"].sum() if not sm.empty else 0.0,
            "Month_Khata_Ton": sm[sm["SKU"] == "Khata"]["Khata_Ton"].sum() if not sm.empty else 0.0,
            "Month_Deliv_Khata_Ton": sm[sm["SKU"] == "Khata"]["Delivery_Khata_Ton"].sum() if not sm.empty else 0.0,
        })
    return pd.DataFrame(rows)


rep_df = build_report(cfg_df, d_sub, w_sub, m_sub)


def show_entry_form(prefix, sr_name, cfg_row, sales_ws):
    sku = st.selectbox("Select SKU", ["Pen", "Stationery", "Khata"], key=f"{prefix}_sku")
    with st.form(f"{prefix}_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            e_date = st.date_input("Date", value=date.today(), key=f"{prefix}_date")
        with c2:
            e_ses = st.selectbox("Session", ["Half Summary", "Full Summary"], key=f"{prefix}_ses")

        if sku == "Pen":
            qty = st.number_input("Pen Quantity (Pcs)", min_value=0.0, step=10.0, format="%.0f", key=f"{prefix}_pq")
            rate = st.number_input("Pen Rate (BDT)", min_value=0.0, value=float(cfg_row["Pen_Rate"]), step=1.0, format="%.2f", key=f"{prefix}_pr")
            total_bdt = float(qty) * float(rate)
            deliv_bdt = st.number_input("Delivered Amount (BDT)", min_value=0.0, value=float(total_bdt), step=100.0, format="%.2f", key=f"{prefix}_pd")
            kh_ton = 0.0
            deliv_ton = 0.0
            unit = "Pcs"
        elif sku == "Stationery":
            qty = st.number_input("Stationery Quantity (Pcs)", min_value=0.0, step=10.0, format="%.0f", key=f"{prefix}_sq")
            rate = st.number_input("Stationery Rate (BDT)", min_value=0.0, value=float(cfg_row["Stationery_Rate"]), step=1.0, format="%.2f", key=f"{prefix}_sr")
            total_bdt = float(qty) * float(rate)
            deliv_bdt = st.number_input("Delivered Amount (BDT)", min_value=0.0, value=float(total_bdt), step=100.0, format="%.2f", key=f"{prefix}_sd")
            kh_ton = 0.0
            deliv_ton = 0.0
            unit = "Pcs"
        else:
            kh_ton = st.number_input("Khata Order (Ton)", min_value=0.0, step=0.25, format="%.2f", key=f"{prefix}_kt")
            deliv_ton = st.number_input("Khata Delivery (Ton)", min_value=0.0, value=float(kh_ton), step=0.25, format="%.2f", key=f"{prefix}_kdt")
            rate = KHATA_RATE_PER_TON
            total_bdt = float(kh_ton) * KHATA_RATE_PER_TON
            deliv_bdt = float(deliv_ton) * KHATA_RATE_PER_TON
            qty = float(kh_ton)
            unit = "Ton"

        c3, c4 = st.columns(2)
        with c3:
            memo = st.number_input("Memos", min_value=0, step=1, format="%d", key=f"{prefix}_memo")
        with c4:
            note = st.text_input("Area / Note", key=f"{prefix}_note")

        if st.form_submit_button("Submit Entry"):
            if qty <= 0 and total_bdt <= 0 and deliv_bdt <= 0:
                st.warning("Enter quantity or amount greater than 0.")
            else:
                sales_ws.append_row([
                    str(e_date),
                    e_ses,
                    sr_name,
                    sku,
                    round(float(qty), 4),
                    unit,
                    round(float(rate), 2),
                    round(float(total_bdt), 2),
                    round(float(deliv_bdt), 2),
                    round(float(kh_ton), 4),
                    round(float(deliv_ton), 4),
                    int(memo),
                    note.strip(),
                ])
                st.success("Saved!")
                st.rerun()


# ==============================================================================
# VIEW 1: SR SELF-ENTRY, OWN TARGET & MY REPORT
# ==============================================================================
if view_mode == "SR Self-Entry & My Report":
    st.markdown(
        """
        <div class="hero-box">
            <h1>SR Self-Entry &amp; My Sales Report</h1>
            <p>Set your own target &amp; rates, submit daily sales &amp; delivery entries, and view your full calculation</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sr_name = st.selectbox("Select SR", sr_names)
    sr_idx = sr_names.index(sr_name)
    cfg_row = cfg_df.iloc[sr_idx]

    with st.expander("My Target & Rate Setup", expanded=False):
        with st.form(f"my_cfg_{sr_idx}"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                w_days = st.number_input("Working Days", min_value=1, value=safe_int(cfg_row["Working_Days"], DEFAULT_DAYS, 1), step=1)
            with c2:
                p_mt = st.number_input("Pen Monthly (Pcs)", min_value=0.0, value=float(cfg_row["Pen_Monthly_Pcs"]), step=100.0, format="%.0f")
            with c3:
                p_rt = st.number_input("Pen Rate (BDT)", min_value=0.0, value=float(cfg_row["Pen_Rate"]), step=1.0, format="%.2f")
            with c4:
                k_mt = st.number_input("Khata Monthly (Ton)", min_value=0.0, value=float(cfg_row["Khata_Monthly_Ton"]), step=0.25, format="%.2f")

            c5, c6 = st.columns(2)
            with c5:
                s_mt = st.number_input("Stationery Monthly (Pcs)", min_value=0.0, value=float(cfg_row["Stationery_Monthly_Pcs"]), step=100.0, format="%.0f")
            with c6:
                s_rt = st.number_input("Stationery Rate (BDT)", min_value=0.0, value=float(cfg_row["Stationery_Rate"]), step=1.0, format="%.2f")

            if st.form_submit_button("Save My Target"):
                new_cfg = cfg_df.copy()
                new_cfg.loc[sr_idx, "Working_Days"] = safe_int(w_days, DEFAULT_DAYS, 1)
                new_cfg.loc[sr_idx, "Pen_Monthly_Pcs"] = float(p_mt)
                new_cfg.loc[sr_idx, "Pen_Rate"] = float(p_rt)
                new_cfg.loc[sr_idx, "Stationery_Monthly_Pcs"] = float(s_mt)
                new_cfg.loc[sr_idx, "Stationery_Rate"] = float(s_rt)
                new_cfg.loc[sr_idx, "Khata_Monthly_Ton"] = float(k_mt)
                write_config_all(cfg_ws, new_cfg)
                st.success("Target saved!")
                st.rerun()

    st.subheader("Daily Sales & Delivery Entry")
    show_entry_form("sr_tab", sr_name, cfg_row, sales_ws)

    me = rep_df[rep_df["SR_Name"] == sr_name].iloc[0]
    st.subheader(f"My Summary ({rep_date_str})")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Day Target", f"BDT {me['Day_Target']:,.0f}")
    m2.metric("Day Sales", f"BDT {me['Day_Sales']:,.0f}", f"Memo: {int(me['Day_Memo'])}")
    m3.metric("Day Delivery", f"BDT {me['Day_Delivery']:,.0f}")
    m4.metric("Day Shortfall", f"BDT {me['Day_Shortfall']:,.0f}")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Month Target", f"BDT {me['Month_Target']:,.0f}")
    m6.metric("Month Sales", f"BDT {me['Month_Sales']:,.0f}", f"Memo: {int(me['Month_Memo'])}")
    m7.metric("Month Delivery", f"BDT {me['Month_Delivery']:,.0f}")
    m8.metric("Achievement %", f"{me['Ach_%']:.1f}%")

    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(
            f"""
            <div class="sku-card sku-pen">
                <div class="sku-title">{sr_name} — Pen</div>
                <div class="sku-line">• Today: <b>{me['Day_Pen_Pcs']:,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{me['Month_Pen_Pcs']:,.0f} / {me['Pen_Monthly_Pcs']:,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            f"""
            <div class="sku-card sku-stat">
                <div class="sku-title">{sr_name} — Stationery</div>
                <div class="sku-line">• Today: <b>{me['Day_Stat_Pcs']:,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{me['Month_Stat_Pcs']:,.0f} / {me['Stationery_Monthly_Pcs']:,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f"""
            <div class="sku-card sku-khata">
                <div class="sku-title">{sr_name} — Khata</div>
                <div class="sku-line">• Today Order: <b>{me['Day_Khata_Ton']:,.2f} Ton</b> | Delivery: <b>{me['Day_Deliv_Khata_Ton']:,.2f} Ton</b></div>
                <div class="sku-line">• Monthly Order: <b>{me['Month_Khata_Ton']:,.2f} / {me['Khata_Monthly_Ton']:,.2f} Ton</b> | Delivery: <b>{me['Month_Deliv_Khata_Ton']:,.2f} Ton</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("My Submitted Entries")
    my_df = sales_df[sales_df["SR_Name"] == sr_name] if not sales_df.empty else pd.DataFrame(columns=SALES_COLS)
    if my_df.empty:
        st.info("No entries yet.")
    else:
        st.dataframe(my_df.drop(columns=["Dt"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)


# ==============================================================================
# VIEW 2: TSM ALL SRs & TOTAL
# ==============================================================================
else:
    st.markdown(
        """
        <div class="hero-box">
            <h1>TSM Sales &amp; Delivery Tracker — All SRs &amp; Total</h1>
            <p>View every SR's daily &amp; monthly sales, delivery, target, shortfall &amp; Grand Total</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tot_dt = rep_df["Day_Target"].sum()
    tot_ds = rep_df["Day_Sales"].sum()
    tot_dd = rep_df["Day_Delivery"].sum()
    tot_dsh = max(0.0, tot_dt - tot_ds)

    tot_mt = rep_df["Month_Target"].sum()
    tot_ms = rep_df["Month_Sales"].sum()
    tot_md = rep_df["Month_Delivery"].sum()
    tot_msh = max(0.0, tot_mt - tot_ms)
    tot_ach = (tot_ms / tot_mt * 100.0) if tot_mt > 0 else 0.0

    st.subheader(f"Grand Total — All SRs ({rep_date_str})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Day Target", f"BDT {tot_dt:,.0f}")
    c2.metric("Total Day Sales", f"BDT {tot_ds:,.0f}", f"Memo: {int(rep_df['Day_Memo'].sum())}")
    c3.metric("Total Day Delivery", f"BDT {tot_dd:,.0f}")
    c4.metric("Total Day Shortfall", f"BDT {tot_dsh:,.0f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Total Month Target", f"BDT {tot_mt:,.0f}")
    c6.metric("Total Month Sales", f"BDT {tot_ms:,.0f}", f"Memo: {int(rep_df['Month_Memo'].sum())}")
    c7.metric("Total Month Delivery", f"BDT {tot_md:,.0f}")
    c8.metric("Total Achievement %", f"{tot_ach:.1f}%", f"Short: BDT {tot_msh:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown(
            f"""
            <div class="sku-card sku-pen">
                <div class="sku-title">All SRs — Pen</div>
                <div class="sku-line">• Today: <b>{rep_df['Day_Pen_Pcs'].sum():,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{rep_df['Month_Pen_Pcs'].sum():,.0f} / {rep_df['Pen_Monthly_Pcs'].sum():,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            f"""
            <div class="sku-card sku-stat">
                <div class="sku-title">All SRs — Stationery</div>
                <div class="sku-line">• Today: <b>{rep_df['Day_Stat_Pcs'].sum():,.0f} Pcs</b></div>
                <div class="sku-line">• Monthly: <b>{rep_df['Month_Stat_Pcs'].sum():,.0f} / {rep_df['Stationery_Monthly_Pcs'].sum():,.0f} Pcs</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            f"""
            <div class="sku-card sku-khata">
                <div class="sku-title">All SRs — Khata</div>
                <div class="sku-line">• Today Order: <b>{rep_df['Day_Khata_Ton'].sum():,.2f} Ton</b> | Delivery: <b>{rep_df['Day_Deliv_Khata_Ton'].sum():,.2f} Ton</b></div>
                <div class="sku-line">• Monthly Order: <b>{rep_df['Month_Khata_Ton'].sum():,.2f} / {rep_df['Khata_Monthly_Ton'].sum():,.2f} Ton</b> | Delivery: <b>{rep_df['Month_Deliv_Khata_Ton'].sum():,.2f} Ton</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("All SRs Summary")
    summary_cols = [
        "SR_Name", "Day_Target", "Day_Sales", "Day_Delivery", "Day_Shortfall", "Day_Memo",
        "Month_Target", "Month_Sales", "Month_Delivery", "Month_Shortfall", "Ach_%", "Month_Memo",
    ]
    grand_row = pd.DataFrame([{
        "SR_Name": "GRAND TOTAL",
        "Day_Target": tot_dt,
        "Day_Sales": tot_ds,
        "Day_Delivery": tot_dd,
        "Day_Shortfall": tot_dsh,
        "Day_Memo": int(rep_df["Day_Memo"].sum()),
        "Month_Target": tot_mt,
        "Month_Sales": tot_ms,
        "Month_Delivery": tot_md,
        "Month_Shortfall": tot_msh,
        "Ach_%": tot_ach,
        "Month_Memo": int(rep_df["Month_Memo"].sum()),
    }])
    st.dataframe(pd.concat([rep_df[summary_cols], grand_row[summary_cols]], ignore_index=True), width="stretch", hide_index=True)

    st.subheader("All SR Entries Log")
    if sales_df.empty:
        st.info("No entries yet.")
    else:
        st.dataframe(sales_df.drop(columns=["Dt"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)
