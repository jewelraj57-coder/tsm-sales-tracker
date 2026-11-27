import json
from datetime import date, timedelta
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="TSM Sales Tracker", layout="wide")

SHEET_NAME = "TSM_Sales_Database"
TARGETS_TAB_NAME = "SR_Targets"
KHATA_TON_TO_BDT = 200000.0
DEFAULT_WORKING_DAYS = 26

SALES_HEADERS = [
    "Date",
    "Session",
    "SR_Name",
    "Product",
    "Quantity",
    "Unit",
    "Unit_Rate",
    "Amount_BDT",
    "Khata_Tons",
    "Memos",
    "Notes",
]

TARGET_HEADERS = [
    "Slot",
    "SR_Name",
    "Working_Days",
    "Pen_Monthly_Pcs",
    "Pen_Default_Rate",
    "Stationery_Monthly_Pcs",
    "Stationery_Default_Rate",
    "Khata_Monthly_Tons",
]

DEFAULT_SRS = [
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


@st.cache_resource
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Streamlit Secrets-এ `gcp_service_account` পাওয়া যায়নি।")
        st.stop()

    raw_secret = st.secrets["gcp_service_account"]
    if isinstance(raw_secret, str):
        creds_dict = json.loads(raw_secret)
    else:
        creds_dict = dict(raw_secret)

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheets():
    client = get_gspread_client()
    spreadsheet = client.open(SHEET_NAME)

    sales_ws = spreadsheet.sheet1
    existing_sales = sales_ws.get_all_values()
    if not existing_sales:
        sales_ws.append_row(SALES_HEADERS)
    elif existing_sales[0] != SALES_HEADERS:
        sales_ws.update("A1:K1", [SALES_HEADERS])

    try:
        targets_ws = spreadsheet.worksheet(TARGETS_TAB_NAME)
    except gspread.WorksheetNotFound:
        targets_ws = spreadsheet.add_worksheet(title=TARGETS_TAB_NAME, rows=20, cols=10)
        targets_ws.append_row(TARGET_HEADERS)
        for row in DEFAULT_SRS:
            targets_ws.append_row(row)

    existing_targets = targets_ws.get_all_values()
    if not existing_targets:
        targets_ws.append_row(TARGET_HEADERS)
        for row in DEFAULT_SRS:
            targets_ws.append_row(row)
    elif existing_targets[0] != TARGET_HEADERS:
        targets_ws.update("A1:H1", [TARGET_HEADERS])

    return sales_ws, targets_ws


def load_targets(targets_ws):
    records = targets_ws.get_all_records(expected_headers=TARGET_HEADERS)
    if not records:
        return pd.DataFrame(DEFAULT_SRS, columns=TARGET_HEADERS)

    t_df = pd.DataFrame(records)
    for col in TARGET_HEADERS:
        if col not in t_df.columns:
            t_df[col] = 0.0 if col != "SR_Name" else ""

    t_df["SR_Name"] = t_df["SR_Name"].astype(str).str.strip()
    t_df["Working_Days"] = pd.to_numeric(t_df["Working_Days"], errors="coerce").fillna(DEFAULT_WORKING_DAYS).astype(int)
    t_df["Working_Days"] = t_df["Working_Days"].replace(0, DEFAULT_WORKING_DAYS)

    for num_col in [
        "Pen_Monthly_Pcs",
        "Pen_Default_Rate",
        "Stationery_Monthly_Pcs",
        "Stationery_Default_Rate",
        "Khata_Monthly_Tons",
    ]:
        t_df[num_col] = pd.to_numeric(t_df[num_col], errors="coerce").fillna(0.0)

    return t_df.head(6)


def load_sales_data(sales_ws):
    values = sales_ws.get_all_values()
    if len(values) <= 1:
        return pd.DataFrame(columns=SALES_HEADERS)

    rows = values[1:]
    normalized_rows = []
    for r in rows:
        padded = (r + [""] * len(SALES_HEADERS))[: len(SALES_HEADERS)]
        if not padded[1].strip():
            padded[1] = "Full Summary"
        normalized_rows.append(padded)

    df = pd.DataFrame(normalized_rows, columns=SALES_HEADERS)
    for col in ["Quantity", "Unit_Rate", "Amount_BDT", "Khata_Tons"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["Memos"] = pd.to_numeric(df["Memos"], errors="coerce").fillna(0).astype(int)

    for str_col in ["Date", "Session", "SR_Name", "Product", "Unit", "Notes"]:
        df[str_col] = df[str_col].astype(str).str.strip()

    df["Parsed_Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    return df


st.title("📊 TSM Sales Tracker — দৈনিক, সাপ্তাহিক ও মাসিক অ্যাকশন ড্যাশবোর্ড")
st.caption("৬ জন SR • Pen (Pcs + রেট), Stationery (Pcs + রেট) ও Khata (Ton @ 200,000 BDT) • Half & Full Summary • Memo, Shortfall ও Action Plan")

try:
    sales_ws, targets_ws = get_worksheets()
    targets_df = load_targets(targets_ws)
    df = load_sales_data(sales_ws)
except Exception as e:
    st.error(f"Google Sheets সংযোগে সমস্যা হয়েছে: {e}")
    st.stop()

sr_list = targets_df["SR_Name"].tolist()

# --- সাইডবার: দ্রুত এন্ট্রি ফর্ম ---
st.sidebar.header("📝 নতুন অর্ডার / সেলস এন্ট্রি")
product = st.sidebar.selectbox("পণ্য (SKU)", ["Pen", "Stationery", "Khata"])

with st.sidebar.form("sales_entry_form", clear_on_submit=True):
    sale_date = st.date_input("তারিখ", value=date.today())
    session_type = st.selectbox("সামারি টাইপ", ["Half Summary", "Full Summary"])
    sr_name = st.selectbox("SR সিলেক্ট করুন", sr_list)

    sr_conf = targets_df[targets_df["SR_Name"] == sr_name]
    def_pen_rate = float(sr_conf["Pen_Default_Rate"].iloc[0]) if not sr_conf.empty else 10.0
    def_stat_rate = float(sr_conf["Stationery_Default_Rate"].iloc[0]) if not sr_conf.empty else 25.0

    if product == "Pen":
        qty_pcs = st.number_input("কলম (Pcs)", min_value=0.0, step=10.0, format="%.0f")
        unit_rate = st.number_input("এক পিসের রেট (৳)", min_value=0.0, value=def_pen_rate, step=1.0, format="%.2f")
        amount_bdt = float(qty_pcs) * float(unit_rate)
        khata_tons = 0.0
        quantity = float(qty_pcs)
        unit = "Pcs"
        st.caption(f"কলমের মূল্য: **৳ {amount_bdt:,.0f}**")
    elif product == "Stationery":
        qty_pcs = st.number_input("স্টেশনারি (Pcs)", min_value=0.0, step=10.0, format="%.0f")
        unit_rate = st.number_input("এক পিসের রেট (৳)", min_value=0.0, value=def_stat_rate, step=1.0, format="%.2f")
        amount_bdt = float(qty_pcs) * float(unit_rate)
        khata_tons = 0.0
        quantity = float(qty_pcs)
        unit = "Pcs"
        st.caption(f"স্টেশনারির মূল্য: **৳ {amount_bdt:,.0f}**")
    else:
        khata_tons = st.number_input("খাতা (Ton)", min_value=0.0, step=0.25, format="%.2f")
        unit_rate = KHATA_TON_TO_BDT
        amount_bdt = float(khata_tons) * KHATA_TON_TO_BDT
        quantity = float(khata_tons)
        unit = "Ton"
        st.caption(f"খাতার মূল্য (১ টন = ২০০,০০০ ৳): **৳ {amount_bdt:,.0f}**")

    memos = st.number_input("মেমো সংখ্যা", min_value=0, step=1, format="%d")
    notes = st.text_input("এলাকা / নোট (ঐচ্ছিক)")
    submitted = st.form_submit_button("💾 Save to Google Sheet")

    if submitted:
        if quantity <= 0 and amount_bdt <= 0:
            st.sidebar.warning("পরিমাণ বা টাকা ০-এর বেশি হতে হবে।")
        else:
            row = [
                str(sale_date),
                session_type,
                sr_name.strip(),
                product,
                round(float(quantity), 4),
                unit,
                round(float(unit_rate), 2),
                round(float(amount_bdt), 2),
                round(float(khata_tons), 4),
                int(memos),
                notes.strip(),
            ]
            sales_ws.append_row(row)
            st.sidebar.success(f"{sr_name}-এর এন্ট্রি সেভ হয়েছে!")
            st.rerun()

# --- রিপোর্টের তারিখ ও সময়সীমা ফিল্টার ---
sel_date = st.date_input("রিপোর্টের তারিখ নির্বাচন করুন", value=date.today())
sel_date_str = str(sel_date)
week_start = sel_date - timedelta(days=6)
month_prefix = sel_date_str[:7]

if df.empty:
    day_df = pd.DataFrame(columns=SALES_HEADERS)
    week_df = pd.DataFrame(columns=SALES_HEADERS)
    month_df = pd.DataFrame(columns=SALES_HEADERS)
else:
    day_df = df[df["Date"] == sel_date_str]
    week_df = df[(df["Parsed_Date"] >= week_start) & (df["Parsed_Date"] <= sel_date)]
    month_df = df[df["Date"].str.startswith(month_prefix)]


def compute_summary(t_frame, d_frame, w_frame, m_frame):
    records = []
    for _, r in t_frame.iterrows():
        sr = r["SR_Name"]
        days = int(r["Working_Days"]) if int(r["Working_Days"]) > 0 else DEFAULT_WORKING_DAYS

        pen_m_t = float(r["Pen_Monthly_Pcs"])
        stat_m_t = float(r["Stationery_Monthly_Pcs"])
        khata_m_t_ton = float(r["Khata_Monthly_Tons"])
        khata_m_t_bdt = khata_m_t_ton * KHATA_TON_TO_BDT
        total_m_t_bdt = (pen_m_t * float(r["Pen_Default_Rate"])) + (stat_m_t * float(r["Stationery_Default_Rate"])) + khata_m_t_bdt

        pen_d_t = pen_m_t / days
        stat_d_t = stat_m_t / days
        khata_d_t_ton = khata_m_t_ton / days
        khata_d_t_bdt = khata_m_t_bdt / days
        total_d_t_bdt = total_m_t_bdt / days

        # Daily
        sd = d_frame[d_frame["SR_Name"] == sr] if not d_frame.empty else pd.DataFrame(columns=SALES_HEADERS)
        dh = sd[sd["Session"] == "Half Summary"]
        dfu = sd[sd["Session"] == "Full Summary"]

        d_pen_pcs = sd[sd["Product"] == "Pen"]["Quantity"].sum()
        d_pen_bdt = sd[sd["Product"] == "Pen"]["Amount_BDT"].sum()
        d_stat_pcs = sd[sd["Product"] == "Stationery"]["Quantity"].sum()
        d_stat_bdt = sd[sd["Product"] == "Stationery"]["Amount_BDT"].sum()
        d_khata_ton = sd[sd["Product"] == "Khata"]["Khata_Tons"].sum()
        d_khata_bdt = sd[sd["Product"] == "Khata"]["Amount_BDT"].sum()
        d_bdt = sd["Amount_BDT"].sum()
        d_memo = int(sd["Memos"].sum())

        d_half_bdt = dh["Amount_BDT"].sum()
        d_half_memo = int(dh["Memos"].sum())
        d_half_khata_bdt = dh[dh["Product"] == "Khata"]["Amount_BDT"].sum()
        d_half_pen_pcs = dh[dh["Product"] == "Pen"]["Quantity"].sum()
        d_half_stat_pcs = dh[dh["Product"] == "Stationery"]["Quantity"].sum()

        d_full_bdt = dfu["Amount_BDT"].sum()
        d_full_memo = int(dfu["Memos"].sum())
        d_full_khata_bdt = dfu[dfu["Product"] == "Khata"]["Amount_BDT"].sum()
        d_full_pen_pcs = dfu[dfu["Product"] == "Pen"]["Quantity"].sum()
        d_full_stat_pcs = dfu[dfu["Product"] == "Stationery"]["Quantity"].sum()

        d_short_bdt = max(0.0, total_d_t_bdt - d_bdt)
        d_short_pen = max(0.0, pen_d_t - d_pen_pcs)
        d_short_stat = max(0.0, stat_d_t - d_stat_pcs)
        d_short_khata_ton = max(0.0, khata_d_t_ton - d_khata_ton)

        # Weekly (7 days window)
        sw = w_frame[w_frame["SR_Name"] == sr] if not w_frame.empty else pd.DataFrame(columns=SALES_HEADERS)
        w_pen_pcs = sw[sw["Product"] == "Pen"]["Quantity"].sum()
        w_stat_pcs = sw[sw["Product"] == "Stationery"]["Quantity"].sum()
        w_khata_ton = sw[sw["Product"] == "Khata"]["Khata_Tons"].sum()
        w_bdt = sw["Amount_BDT"].sum()
        w_memo = int(sw["Memos"].sum())
        w_target_bdt = total_d_t_bdt * 7
        w_short_bdt = max(0.0, w_target_bdt - w_bdt)

        # Monthly
        sm = m_frame[m_frame["SR_Name"] == sr] if not m_frame.empty else pd.DataFrame(columns=SALES_HEADERS)
        m_pen_pcs = sm[sm["Product"] == "Pen"]["Quantity"].sum()
        m_pen_bdt = sm[sm["Product"] == "Pen"]["Amount_BDT"].sum()
        m_stat_pcs = sm[sm["Product"] == "Stationery"]["Quantity"].sum()
        m_stat_bdt = sm[sm["Product"] == "Stationery"]["Amount_BDT"].sum()
        m_khata_ton = sm[sm["Product"] == "Khata"]["Khata_Tons"].sum()
        m_khata_bdt = sm[sm["Product"] == "Khata"]["Amount_BDT"].sum()
        m_bdt = sm["Amount_BDT"].sum()
        m_memo = int(sm["Memos"].sum())

        m_short_bdt = max(0.0, total_m_t_bdt - m_bdt)
        m_short_pen = max(0.0, pen_m_t - m_pen_pcs)
        m_short_stat = max(0.0, stat_m_t - m_stat_pcs)
        m_short_khata_ton = max(0.0, khata_m_t_ton - m_khata_ton)

        ach_pct = (m_bdt / total_m_t_bdt * 100.0) if total_m_t_bdt > 0 else 0.0
        short_pct = max(0.0, 100.0 - ach_pct) if total_m_t_bdt > 0 else 0.0

        # Action Note
        if total_m_t_bdt <= 0:
            action = "টার্গেট সেট করুন"
        elif d_short_bdt > (total_d_t_bdt * 0.5):
            action = f"আজকে জরুরি ফোকাস দিন (৳ {d_short_bdt:,.0f} শর্টফল, মেমো {d_memo})"
        elif ach_pct < 50:
            action = f"মাসিক গতি বাড়ান ({ach_pct:.1f}% অর্জন — শর্টফল ৳ {m_short_bdt:,.0f})"
        else:
            action = f"ভালো চলছে ({ach_pct:.1f}% অর্জন) — মেমো ও খাতা ধরে রাখুন"

        records.append({
            "SR_Name": sr,
            "D_Target_BDT": total_d_t_bdt,
            "D_Sales_BDT": d_bdt,
            "D_Short_BDT": d_short_bdt,
            "D_Half_BDT": d_half_bdt,
            "D_Half_Memo": d_half_memo,
            "D_Half_Pen": d_half_pen_pcs,
            "D_Half_Stat": d_half_stat_pcs,
            "D_Half_Khata_BDT": d_half_khata_bdt,
            "D_Full_BDT": d_full_bdt,
            "D_Full_Memo": d_full_memo,
            "D_Full_Pen": d_full_pen_pcs,
            "D_Full_Stat": d_full_stat_pcs,
            "D_Full_Khata_BDT": d_full_khata_bdt,
            "D_Pen_Pcs": d_pen_pcs,
            "D_Pen_BDT": d_pen_bdt,
            "D_Short_Pen": d_short_pen,
            "D_Stat_Pcs": d_stat_pcs,
            "D_Stat_BDT": d_stat_bdt,
            "D_Short_Stat": d_short_stat,
            "D_Khata_Ton": d_khata_ton,
            "D_Khata_BDT": d_khata_bdt,
            "D_Short_Khata_Ton": d_short_khata_ton,
            "D_Memo": d_memo,
            "W_Sales_BDT": w_bdt,
            "W_Short_BDT": w_short_bdt,
            "W_Pen_Pcs": w_pen_pcs,
            "W_Stat_Pcs": w_stat_pcs,
            "W_Khata_Ton": w_khata_ton,
            "W_Memo": w_memo,
            "M_Target_BDT": total_m_t_bdt,
            "M_Sales_BDT": m_bdt,
            "M_Short_BDT": m_short_bdt,
            "Ach_%": ach_pct,
            "Short_%": short_pct,
            "M_Pen_Target": pen_m_t,
            "M_Pen_Pcs": m_pen_pcs,
            "M_Pen_BDT": m_pen_bdt,
            "M_Short_Pen": m_short_pen,
            "M_Stat_Target": stat_m_t,
            "M_Stat_Pcs": m_stat_pcs,
            "M_Stat_BDT": m_stat_bdt,
            "M_Short_Stat": m_short_stat,
            "M_Khata_Target_Ton": khata_m_t_ton,
            "M_Khata_Ton": m_khata_ton,
            "M_Khata_BDT": m_khata_bdt,
            "M_Short_Khata_Ton": m_short_khata_ton,
            "M_Memo": m_memo,
            "Action": action,
        })
    return pd.DataFrame(records)


s_df = compute_summary(targets_df, day_df, week_df, month_df)

tab1, tab2, tab3, tab4 = st.tabs([
    "⚡ একনজরে রিপোর্ট ও আজকের অ্যাকশন",
    "☀️/🌙 Half & Full Summary (৬ SR)",
    "⚙️ 6 SR টার্গেট ও রেট সেটআপ",
    "📋 সেলস লগ",
])

with tab1:
    # সবার একত্রে Top KPIs
    tot_d_t = s_df["D_Target_BDT"].sum()
    tot_d_s = s_df["D_Sales_BDT"].sum()
    tot_d_sh = max(0.0, tot_d_t - tot_d_s)
    tot_w_s = s_df["W_Sales_BDT"].sum()
    tot_w_sh = s_df["W_Short_BDT"].sum()
    tot_m_t = s_df["M_Target_BDT"].sum()
    tot_m_s = s_df["M_Sales_BDT"].sum()
    tot_m_sh = max(0.0, tot_m_t - tot_m_s)
    tot_ach = (tot_m_s / tot_m_t * 100.0) if tot_m_t > 0 else 0.0
    tot_sh_pct = max(0.0, 100.0 - tot_ach) if tot_m_t > 0 else 0.0

    st.subheader(f"🌐 সবার একত্রে সামারি — দৈনিক ({sel_date_str}), সাপ্তাহিক ({week_start} থেকে) ও মাসিক ({month_prefix})")
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(5)
    r1c1.metric("আজকের টার্গেট", f"৳ {tot_d_t:,.0f}")
    r1c2.metric("আজকের সেলস", f"৳ {tot_d_s:,.0f}", f"Memo: {int(s_df['D_Memo'].sum())}")
    r1c3.metric("আজকের শর্টফল", f"৳ {tot_d_sh:,.0f}")
    r1c4.metric("৭ দিনের সেলস", f"৳ {tot_w_s:,.0f}", f"Shortfall: ৳ {tot_w_sh:,.0f}")
    r1c5.metric("মাসিক টার্গেট", f"৳ {tot_m_t:,.0f}")

    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    r2c1.metric("মাসিক সেলস", f"৳ {tot_m_s:,.0f}", f"Memo: {int(s_df['M_Memo'].sum())}")
    r2c2.metric("মাসিক শর্টফল", f"৳ {tot_m_sh:,.0f}")
    r2c3.metric("Achievement %", f"{tot_ach:.1f}%")
    r2c4.metric("Shortfall %", f"{tot_sh_pct:.1f}%")
    r2c5.metric("মোট খাতা / কলম / স্টেশনারি", f"{s_df['M_Khata_Ton'].sum():.2f}T | {s_df['M_Pen_Pcs'].sum():,.0f}P | {s_df['M_Stat_Pcs'].sum():,.0f}S")

    # SKU-wise Grand Total
    p_col, st_col, kh_col = st.columns(3)
    with p_col:
        st.info(
            f"**Pen (কলম — Pcs)**\n\n"
            f"- আজ: **{s_df['D_Pen_Pcs'].sum():,.0f} Pcs** (৳ {s_df['D_Pen_BDT'].sum():,.0f}) | শর্টফল: **{s_df['D_Short_Pen'].sum():,.0f}**\n"
            f"- ৭ দিন: **{s_df['W_Pen_Pcs'].sum():,.0f} Pcs**\n"
            f"- মাসিক: **{s_df['M_Pen_Pcs'].sum():,.0f} / {s_df['M_Pen_Target'].sum():,.0f} Pcs** (৳ {s_df['M_Pen_BDT'].sum():,.0f}) | শর্টফল: **{s_df['M_Short_Pen'].sum():,.0f}**"
        )
    with st_col:
        st.info(
            f"**Stationery (স্টেশনারি — Pcs)**\n\n"
            f"- আজ: **{s_df['D_Stat_Pcs'].sum():,.0f} Pcs** (৳ {s_df['D_Stat_BDT'].sum():,.0f}) | শর্টফল: **{s_df['D_Short_Stat'].sum():,.0f}**\n"
            f"- ৭ দিন: **{s_df['W_Stat_Pcs'].sum():,.0f} Pcs**\n"
            f"- মাসিক: **{s_df['M_Stat_Pcs'].sum():,.0f} / {s_df['M_Stat_Target'].sum():,.0f} Pcs** (৳ {s_df['M_Stat_BDT'].sum():,.0f}) | শর্টফল: **{s_df['M_Short_Stat'].sum():,.0f}**"
        )
    with kh_col:
        st.info(
            f"**Khata (খাতা — Ton @ ২০০,০০০ ৳)**\n\n"
            f"- আজ: **{s_df['D_Khata_Ton'].sum():,.2f} Ton** (**৳ {s_df['D_Khata_BDT'].sum():,.0f}**) | শর্টফল: **{s_df['D_Short_Khata_Ton'].sum():,.2f} Ton**\n"
            f"- ৭ দিন: **{s_df['W_Khata_Ton'].sum():,.2f} Ton**\n"
            f"- মাসিক: **{s_df['M_Khata_Ton'].sum():,.2f} / {s_df['M_Khata_Target_Ton'].sum():,.2f} Ton** (**৳ {s_df['M_Khata_BDT'].sum():,.0f}**) | শর্টফল: **{s_df['M_Short_Khata_Ton'].sum():,.2f} Ton**"
        )

    st.markdown("### 🎯 আজকের অ্যাকশন তালিকা (কোন SR-এর ওপর আজ কী পদক্ষেপ নেবেন)")
    for _, row in s_df.iterrows():
        st.write(f"- **{row['SR_Name']}** → {row['Action']}")

    st.markdown("### 📊 ৬ জন SR + সবার একত্রে (Grand Total) তুলনা টেবিল")
    grand_df = pd.DataFrame([{
        "SR_Name": "GRAND TOTAL (6 SRs)",
        "D_Target_BDT": tot_d_t,
        "D_Sales_BDT": tot_d_s,
        "D_Short_BDT": tot_d_sh,
        "D_Memo": int(s_df["D_Memo"].sum()),
        "D_Pen_Pcs": s_df["D_Pen_Pcs"].sum(),
        "D_Stat_Pcs": s_df["D_Stat_Pcs"].sum(),
        "D_Khata_Ton": s_df["D_Khata_Ton"].sum(),
        "D_Khata_BDT": s_df["D_Khata_BDT"].sum(),
        "W_Sales_BDT": tot_w_s,
        "W_Short_BDT": tot_w_sh,
        "M_Target_BDT": tot_m_t,
        "M_Sales_BDT": tot_m_s,
        "M_Short_BDT": tot_m_sh,
        "Ach_%": tot_ach,
        "Short_%": tot_sh_pct,
        "M_Pen_Pcs": s_df["M_Pen_Pcs"].sum(),
        "M_Stat_Pcs": s_df["M_Stat_Pcs"].sum(),
        "M_Khata_Ton": s_df["M_Khata_Ton"].sum(),
        "M_Memo": int(s_df["M_Memo"].sum()),
        "Action": "সবাইকে নিয়ে দৈনিক শর্টফল পূরণ করুন",
    }])

    main_cols = [
        "SR_Name", "D_Target_BDT", "D_Sales_BDT", "D_Short_BDT", "D_Memo",
        "D_Pen_Pcs", "D_Stat_Pcs", "D_Khata_Ton", "D_Khata_BDT",
        "W_Sales_BDT", "W_Short_BDT",
        "M_Target_BDT", "M_Sales_BDT", "M_Short_BDT", "Ach_%", "Short_%",
        "M_Pen_Pcs", "M_Stat_Pcs", "M_Khata_Ton", "M_Memo", "Action",
    ]
    st.dataframe(pd.concat([s_df[main_cols], grand_df[main_cols]], ignore_index=True), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("☀️ দুপুর পর্যন্ত (Half Summary) ও 🌙 দিনশেষে (Full Summary)")
    chosen = st.selectbox("ইন্ডিভিজুয়াল SR বেছে নিন", sr_list)
    r_one = s_df[s_df["SR_Name"] == chosen].iloc[0]

    c1, c2 = st.columns(2)
    with c1:
        st.success(
            f"**☀️ Half Summary — {chosen} ({sel_date_str})**\n\n"
            f"- মোট টাকা: **৳ {r_one['D_Half_BDT']:,.0f}** | মেমো: **{int(r_one['D_Half_Memo'])}**\n"
            f"- Pen: **{r_one['D_Half_Pen']:,.0f} Pcs** | Stationery: **{r_one['D_Half_Stat']:,.0f} Pcs** | Khata: **৳ {r_one['D_Half_Khata_BDT']:,.0f}**"
        )
    with c2:
        st.warning(
            f"**🌙 Full Summary — {chosen} ({sel_date_str})**\n\n"
            f"- মোট টাকা: **৳ {r_one['D_Full_BDT']:,.0f}** | মেমো: **{int(r_one['D_Full_Memo'])}**\n"
            f"- Pen: **{r_one['D_Full_Pen']:,.0f} Pcs** | Stationery: **{r_one['D_Full_Stat']:,.0f} Pcs** | Khata: **৳ {r_one['D_Full_Khata_BDT']:,.0f}**"
        )

    st.markdown("#### ৬ জন SR-এর Half ও Full Summary তালিকা")
    hf_table = s_df[[
        "SR_Name",
        "D_Half_BDT", "D_Half_Memo", "D_Half_Pen", "D_Half_Stat", "D_Half_Khata_BDT",
        "D_Full_BDT", "D_Full_Memo", "D_Full_Pen", "D_Full_Stat", "D_Full_Khata_BDT",
    ]]
    st.dataframe(hf_table, use_container_width=True, hide_index=True)

with tab3:
    st.subheader("⚙️ ৬ জন SR-এর নাম, কর্মদিবস, রেট ও মাসিক টার্গেট সেটআপ")
    with st.form("target_setup_form"):
        new_rows = []
        for i in range(6):
            tr = targets_df.iloc[i]
            st.markdown(f"**SR #{i+1}**")
            c1, c2, c3, c4, c5, c6, c7 = st.columns([1.6, 0.8, 1.3, 1.1, 1.3, 1.1, 1.3])
            with c1:
                nm = st.text_input("SR নাম", value=str(tr["SR_Name"]), key=f"nm_{i}")
            with c2:
                dy = st.number_input("কর্মদিবস", min_value=1, max_value=31, value=int(tr["Working_Days"]), step=1, key=f"dy_{i}")
            with c3:
                pm = st.number_input("Pen মাসিক (Pcs)", min_value=0.0, value=float(tr["Pen_Monthly_Pcs"]), step=100.0, format="%.0f", key=f"pm_{i}")
            with c4:
                pr = st.number_input("Pen রেট (৳)", min_value=0.0, value=float(tr["Pen_Default_Rate"]), step=1.0, format="%.2f", key=f"pr_{i}")
            with c5:
                sm_val = st.number_input("Stationery মাসিক (Pcs)", min_value=0.0, value=float(tr["Stationery_Monthly_Pcs"]), step=100.0, format="%.0f", key=f"sm_{i}")
            with c6:
                sr_val = st.number_input("Stationery রেট (৳)", min_value=0.0, value=float(tr["Stationery_Default_Rate"]), step=1.0, format="%.2f", key=f"sr_{i}")
            with c7:
                km = st.number_input("Khata মাসিক (Ton)", min_value=0.0, value=float(tr["Khata_Monthly_Tons"]), step=0.25, format="%.2f", key=f"km_{i}")

            new_rows.append([f"SR-{i+1}", nm.strip() or f"SR-{i+1}", int(dy), float(pm), float(pr), float(sm_val), float(sr_val), float(km)])

        if st.form_submit_button("💾 সেটিংস সেভ করুন"):
            targets_ws.clear()
            targets_ws.append_row(TARGET_HEADERS)
            for nr in new_rows:
                targets_ws.append_row(nr)
            st.success("৬ জন SR-এর টার্গেট ও রেট সেভ হয়েছে!")
            st.rerun()

with tab4:
    st.subheader("📋 বিস্তারিত সেলস লগ")
    if df.empty:
        st.info("এখনো কোনো ডাটা যুক্ত করা হয়নি।")
    else:
        view_df = df.drop(columns=["Parsed_Date"], errors="ignore")
        st.dataframe(view_df.iloc[::-1], use_container_width=True, hide_index=True)
