import json
from datetime import date
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="TSM Sales Tracker", layout="wide")

SHEET_NAME = "TSM_Sales_Database"
TARGETS_TAB_NAME = "SR_Targets"
KHATA_TON_TO_BDT = 200000

SALES_HEADERS = [
    "Date",
    "Session",
    "SR_Name",
    "Product",
    "Quantity",
    "Unit",
    "Amount_BDT",
    "Khata_Tons",
    "Notes",
]

TARGET_HEADERS = [
    "Slot",
    "SR_Name",
    "Monthly_Target_BDT",
    "Working_Days",
]

DEFAULT_SRS = [
    ["SR-1", "SR 1 (নাম লিখুন)", 500000.0, 26],
    ["SR-2", "SR 2 (নাম লিখুন)", 500000.0, 26],
    ["SR-3", "SR 3 (নাম লিখুন)", 500000.0, 26],
    ["SR-4", "SR 4 (নাম লিখুন)", 500000.0, 26],
    ["SR-5", "SR 5 (নাম লিখুন)", 500000.0, 26],
    ["SR-6", "SR 6 (নাম লিখুন)", 500000.0, 26],
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

    # 1. Sales Log Worksheet (sheet1)
    sales_ws = spreadsheet.sheet1
    existing_sales = sales_ws.get_all_values()
    if not existing_sales:
        sales_ws.append_row(SALES_HEADERS)
    elif existing_sales[0] != SALES_HEADERS:
        # পুরনো ডাটা থাকলে কলাম হেডার আপডেট নিশ্চিত করা
        if "Session" not in existing_sales[0]:
            sales_ws.update("A1:I1", [SALES_HEADERS])

    # 2. SR Targets Worksheet
    try:
        targets_ws = spreadsheet.worksheet(TARGETS_TAB_NAME)
    except gspread.WorksheetNotFound:
        targets_ws = spreadsheet.add_worksheet(title=TARGETS_TAB_NAME, rows=20, cols=5)
        targets_ws.append_row(TARGET_HEADERS)
        for row in DEFAULT_SRS:
            targets_ws.append_row(row)

    existing_targets = targets_ws.get_all_values()
    if not existing_targets:
        targets_ws.append_row(TARGET_HEADERS)
        for row in DEFAULT_SRS:
            targets_ws.append_row(row)

    return sales_ws, targets_ws


def load_targets(targets_ws):
    records = targets_ws.get_all_records()
    if not records:
        return pd.DataFrame(DEFAULT_SRS, columns=TARGET_HEADERS)

    t_df = pd.DataFrame(records)
    for col in TARGET_HEADERS:
        if col not in t_df.columns:
            t_df[col] = 0.0 if col in ["Monthly_Target_BDT", "Working_Days"] else ""

    t_df["SR_Name"] = t_df["SR_Name"].astype(str).str.strip()
    t_df["Monthly_Target_BDT"] = pd.to_numeric(t_df["Monthly_Target_BDT"], errors="coerce").fillna(0.0)
    t_df["Working_Days"] = pd.to_numeric(t_df["Working_Days"], errors="coerce").fillna(26).astype(int)
    t_df["Working_Days"] = t_df["Working_Days"].replace(0, 26)
    return t_df.head(6)


def load_sales_data(sales_ws):
    values = sales_ws.get_all_values()
    if len(values) <= 1:
        return pd.DataFrame(columns=SALES_HEADERS)

    raw_headers = values[0]
    rows = values[1:]

    # পুরনো ৮ কলামের রো এবং নতুন ৯ কলামের রো সামঞ্জস্য করা
    normalized_rows = []
    for r in rows:
        if len(r) == 8 and "Session" not in raw_headers:
            # [Date, SR_Name, Product, Quantity, Unit, Amount_BDT, Khata_Tons, Notes]
            normalized_rows.append([r[0], "Full Summary (দিনশেষে)", r[1], r[2], r[3], r[4], r[5], r[6], r[7]])
        else:
            padded = (r + [""] * 9)[:9]
            if not padded[1].strip():
                padded[1] = "Full Summary (দিনশেষে)"
            normalized_rows.append(padded)

    df = pd.DataFrame(normalized_rows, columns=SALES_HEADERS)
    for col in ["Quantity", "Amount_BDT", "Khata_Tons"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["Date"] = df["Date"].astype(str).str.strip()
    df["Session"] = df["Session"].astype(str).str.strip()
    df["SR_Name"] = df["SR_Name"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip()
    return df


st.title("📊 TSM Sales Tracker")
st.caption("৬ জন SR পারফরম্যান্স • দৈনিক হাফ ও ফুল সামারি • দৈনিক ও মাসিক টার্গেট, শর্টফল এবং অ্যাচিভমেন্ট %")

try:
    sales_ws, targets_ws = get_worksheets()
    targets_df = load_targets(targets_ws)
    df = load_sales_data(sales_ws)
except Exception as e:
    st.error(f"Google Sheets সংযোগে সমস্যা হয়েছে: {e}")
    st.stop()

sr_list = targets_df["SR_Name"].tolist()

# --- সাইডবার: নতুন সেলস এন্ট্রি ---
st.sidebar.header("📝 নতুন সেলস এন্ট্রি")
product = st.sidebar.selectbox("পণ্য (Product)", ["Khata", "Pen", "Stationery"])

with st.sidebar.form("sales_entry_form", clear_on_submit=True):
    sale_date = st.date_input("তারিখ", value=date.today())
    session_type = st.selectbox(
        "রিপোর্টের ধরন (Session)",
        ["Half Summary (দুপুর পর্যন্ত)", "Full Summary (দিনশেষে)"],
    )
    sr_name = st.selectbox("SR-এর নাম সিলেক্ট করুন", sr_list)

    if product == "Khata":
        khata_mode = st.radio(
            "খাতার হিসাবের মাধ্যম",
            ["Ton (১ Ton = ২০০,০০০ BDT)", "BDT (সরাসরি টাকা)"],
        )
        if khata_mode == "Ton (১ Ton = ২০০,০০০ BDT)":
            input_val = st.number_input("খাতার পরিমাণ (Ton)", min_value=0.0, step=0.25, format="%.2f")
            khata_tons = float(input_val)
            amount_bdt = float(input_val) * KHATA_TON_TO_BDT
            quantity = float(input_val)
            unit = "Ton"
        else:
            input_val = st.number_input("খাতার মোট টাকা (BDT)", min_value=0.0, step=100.0, format="%.2f")
            amount_bdt = float(input_val)
            khata_tons = float(input_val) / KHATA_TON_TO_BDT if KHATA_TON_TO_BDT else 0.0
            quantity = float(input_val)
            unit = "BDT"
    else:
        quantity = st.number_input(f"{product} পরিমাণ (Pcs)", min_value=0.0, step=1.0, format="%.2f")
        amount_bdt = st.number_input(f"{product} মোট টাকা (BDT)", min_value=0.0, step=10.0, format="%.2f")
        khata_tons = 0.0
        unit = "Pcs"

    notes = st.text_input("নোট / এলাকা (ঐচ্ছিক)")
    submitted = st.form_submit_button("Save to Google Sheet")

    if submitted:
        if amount_bdt <= 0 and quantity <= 0:
            st.sidebar.warning("পরিমাণ বা টাকার অঙ্ক ০-এর বেশি হতে হবে।")
        else:
            row = [
                str(sale_date),
                session_type,
                sr_name.strip(),
                product,
                round(float(quantity), 4),
                unit,
                round(float(amount_bdt), 2),
                round(float(khata_tons), 4),
                notes.strip(),
            ]
            sales_ws.append_row(row)
            st.sidebar.success(f"{sr_name}-এর ডাটা Google Sheet-এ সেভ হয়েছে!")
            st.rerun()

# --- মেইন ট্যাবসমূহ ---
tab1, tab2, tab3 = st.tabs([
    "📈 ড্যাশবোর্ড ও পারফরম্যান্স রিপোর্ট",
    "⚙️ ৬ জন SR ও টার্গেট কাস্টমাইজ",
    "📋 বিস্তারিত সেলস লগ",
])

with tab1:
    # তারিখ ফিল্টার
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_date = st.date_input("কোন দিনের রিপোর্ট দেখতে চান?", value=date.today())
    selected_date_str = str(selected_date)
    selected_month_prefix = selected_date_str[:7]  # যেমন: "2026-11"

    # নির্বাচিত দিন এবং চলতি মাসের ডাটা ফিল্টার
    daily_df = df[df["Date"] == selected_date_str] if not df.empty else pd.DataFrame(columns=SALES_HEADERS)
    monthly_df = df[df["Date"].str.startswith(selected_month_prefix)] if not df.empty else pd.DataFrame(columns=SALES_HEADERS)

    # প্রত্যেক SR-এর হিসাব তৈরি
    report_rows = []
    for _, t_row in targets_df.iterrows():
        s_name = t_row["SR_Name"]
        m_target = float(t_row["Monthly_Target_BDT"])
        w_days = int(t_row["Working_Days"])
        d_target = m_target / w_days if w_days > 0 else 0.0

        # দৈনিক হিসাব
        sr_daily = daily_df[daily_df["SR_Name"] == s_name]
        half_sales = sr_daily[sr_daily["Session"].str.contains("Half", case=False, na=False)]["Amount_BDT"].sum()
        full_session_sales = sr_daily[sr_daily["Session"].str.contains("Full", case=False, na=False)]["Amount_BDT"].sum()
        daily_total_sales = sr_daily["Amount_BDT"].sum()
        daily_shortfall = max(0.0, d_target - daily_total_sales)

        # মাসিক হিসাব
        sr_monthly = monthly_df[monthly_df["SR_Name"] == s_name]
        monthly_sales = sr_monthly["Amount_BDT"].sum()
        monthly_khata_tons = sr_monthly["Khata_Tons"].sum()
        monthly_shortfall = max(0.0, m_target - monthly_sales)

        ach_pct = (monthly_sales / m_target * 100.0) if m_target > 0 else 0.0
        shortfall_pct = max(0.0, 100.0 - ach_pct) if m_target > 0 else 0.0

        report_rows.append({
            "SR_Name": s_name,
            "দৈনিক টার্গেট (BDT)": d_target,
            "হাফ সামারি সেলস": half_sales,
            "দিনশেষে ফুল সামারি": full_session_sales,
            "আজকের মোট সেলস": daily_total_sales,
            "আজকের শর্টফল": daily_shortfall,
            "মাসিক টার্গেট (BDT)": m_target,
            "মাসিক মোট সেলস": monthly_sales,
            "মাসিক খাতা (Ton)": monthly_khata_tons,
            "মাসিক শর্টফল": monthly_shortfall,
            "Achievement %": ach_pct,
            "Shortfall %": shortfall_pct,
        })

    rep_df = pd.DataFrame(report_rows)

    # --- সবার একত্রিত গ্র্যান্ড টোটাল (Overall KPIs) ---
    tot_daily_target = rep_df["দৈনিক টার্গেট (BDT)"].sum()
    tot_half_sales = rep_df["হাফ সামারি সেলস"].sum()
    tot_full_sales = rep_df["দিনশেষে ফুল সামারি"].sum()
    tot_daily_sales = rep_df["আজকের মোট সেলস"].sum()
    tot_daily_shortfall = max(0.0, tot_daily_target - tot_daily_sales)

    tot_monthly_target = rep_df["মাসিক টার্গেট (BDT)"].sum()
    tot_monthly_sales = rep_df["মাসিক মোট সেলস"].sum()
    tot_monthly_shortfall = max(0.0, tot_monthly_target - tot_monthly_sales)
    tot_ach_pct = (tot_monthly_sales / tot_monthly_target * 100.0) if tot_monthly_target > 0 else 0.0
    tot_shortfall_pct = max(0.0, 100.0 - tot_ach_pct) if tot_monthly_target > 0 else 0.0

    st.subheader(f"🌐 সবার একত্রিত সামারি ({selected_date_str})")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("দৈনিক টোটাল টার্গেট", f"৳ {tot_daily_target:,.0f}")
    k2.metric("আজকের হাফ সামারি", f"৳ {tot_half_sales:,.0f}")
    k3.metric("আজকের দিনশেষে ফুল", f"৳ {tot_full_sales:,.0f}")
    k4.metric("আজকের মোট সেলস", f"৳ {tot_daily_sales:,.0f}")
    k5.metric("আজকের শর্টফল", f"৳ {tot_daily_shortfall:,.0f}")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("মাসিক টোটাল টার্গেট", f"৳ {tot_monthly_target:,.0f}")
    m2.metric("মাসিক টোটাল সেলস", f"৳ {tot_monthly_sales:,.0f}")
    m3.metric("মাসিক টোটাল শর্টফল", f"৳ {tot_monthly_shortfall:,.0f}")
    m4.metric("মোট Achievement %", f"{tot_ach_pct:.2f}%")
    m5.metric("মোট Shortfall %", f"{tot_shortfall_pct:.2f}%")

    st.divider()

    # --- ইন্ডিভিজুয়াল ৬ জন SR-এর পূর্ণাঙ্গ টেবিল ---
    st.subheader("👤 প্রত্যেক SR-এর আলাদা পারফরম্যান্স ও টোটাল সামারি")

    total_row = pd.DataFrame([{
        "SR_Name": "সবার একত্রে (GRAND TOTAL)",
        "দৈনিক টার্গেট (BDT)": tot_daily_target,
        "হাফ সামারি সেলস": tot_half_sales,
        "দিনশেষে ফুল সামারি": tot_full_sales,
        "আজকের মোট সেলস": tot_daily_sales,
        "আজকের শর্টফল": tot_daily_shortfall,
        "মাসিক টার্গেট (BDT)": tot_monthly_target,
        "মাসিক মোট সেলস": tot_monthly_sales,
        "মাসিক খাতা (Ton)": rep_df["মাসিক খাতা (Ton)"].sum(),
        "মাসিক শর্টফল": tot_monthly_shortfall,
        "Achievement %": tot_ach_pct,
        "Shortfall %": tot_shortfall_pct,
    }])

    display_df = pd.concat([rep_df, total_row], ignore_index=True)

    st.dataframe(
        display_df.style.format({
            "দৈনিক টার্গেট (BDT)": "৳ {:,.0f}",
            "হাফ সামারি সেলস": "৳ {:,.0f}",
            "দিনশেষে ফুল সামারি": "৳ {:,.0f}",
            "আজকের মোট সেলস": "৳ {:,.0f}",
            "আজকের শর্টফল": "৳ {:,.0f}",
            "মাসিক টার্গেট (BDT)": "৳ {:,.0f}",
            "মাসিক মোট সেলস": "৳ {:,.0f}",
            "মাসিক খাতা (Ton)": "{:,.2f} Ton",
            "মাসিক শর্টফল": "৳ {:,.0f}",
            "Achievement %": "{:.2f}%",
            "Shortfall %": "{:.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("⚙️ ৬ জন SR-এর নাম ও মাসিক টার্গেট কাস্টমাইজ করুন")
    st.info("যেকোনো সময় SR-এর নাম, মাসিক টার্গেট (BDT) বা মাসের কর্মদিবস পরিবর্তন করে নিচের সেভ বাটনে ক্লিক করুন।")

    with st.form("customize_srs_form"):
        updated_rows = []
        for i in range(6):
            row_data = targets_df.iloc[i]
            c_name, c_target, c_days = st.columns([2, 2, 1])
            with c_name:
                new_name = st.text_input(
                    f"SR #{i+1} এর নাম",
                    value=str(row_data["SR_Name"]),
                    key=f"sr_name_{i}",
                )
            with c_target:
                new_target = st.number_input(
                    f"SR #{i+1} মাসিক টার্গেট (BDT)",
                    min_value=0.0,
                    value=float(row_data["Monthly_Target_BDT"]),
                    step=10000.0,
                    format="%.0f",
                    key=f"sr_target_{i}",
                )
            with c_days:
                new_days = st.number_input(
                    f"কর্মদিবস (দিন)",
                    min_value=1,
                    max_value=31,
                    value=int(row_data["Working_Days"]),
                    step=1,
                    key=f"sr_days_{i}",
                )
            updated_rows.append([f"SR-{i+1}", new_name.strip() or f"SR-{i+1}", new_target, new_days])

        save_targets_btn = st.form_submit_button("💾 SR ও টার্গেট সেভ করুন")
        if save_targets_btn:
            targets_ws.clear()
            targets_ws.append_row(TARGET_HEADERS)
            for u_row in updated_rows:
                targets_ws.append_row(u_row)
            st.success("৬ জন SR-এর নাম ও টার্গেট সফলভাবে আপডেট হয়েছে!")
            st.rerun()

with tab3:
    st.subheader("📋 সব সেলস এন্ট্রির বিস্তারিত লগ")
    if df.empty:
        st.info("এখনো কোনো সেলস ডাটা যুক্ত করা হয়নি।")
    else:
        filter_sr = st.selectbox("SR অনুযায়ী ফিল্টার করুন", ["সবাই (All)"] + sr_list)
        filtered_log = df if filter_sr == "সবাই (All)" else df[df["SR_Name"] == filter_sr]
        st.dataframe(filtered_log.iloc[::-1], use_container_width=True, hide_index=True)
