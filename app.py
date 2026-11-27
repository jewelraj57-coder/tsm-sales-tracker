import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="TSM Sales Tracker", layout="wide")

SHEET_NAME = "TSM_Sales_Database"
KHATA_TON_TO_BDT = 200000
HEADERS = [
    "Date",
    "SR_Name",
    "Product",
    "Quantity",
    "Unit",
    "Amount_BDT",
    "Khata_Tons",
    "Notes",
]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gspread_client():
    if "gcp_service_account" not in st.secrets:
        st.error("Streamlit Secrets-এ `gcp_service_account` পাওয়া যায়নি।")
        st.stop()

    raw_secret = st.secrets["gcp_service_account"]
    if isinstance(raw_secret, str):
        creds_dict = json.loads(raw_secret)
    else:
        creds_dict = dict(raw_secret)

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def get_worksheet():
    client = get_gspread_client()
    spreadsheet = client.open(SHEET_NAME)
    ws = spreadsheet.sheet1
    existing = ws.get_all_values()
    if not existing:
        ws.append_row(HEADERS)
    return ws


def load_data(ws):
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=HEADERS)

    df = pd.DataFrame(records)
    for col in HEADERS:
        if col not in df.columns:
            df[col] = 0.0 if col in ["Quantity", "Amount_BDT", "Khata_Tons"] else ""

    for col in ["Quantity", "Amount_BDT", "Khata_Tons"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["SR_Name"] = df["SR_Name"].astype(str).str.strip()
    df["Product"] = df["Product"].astype(str).str.strip()
    return df


st.title("📊 TSM Sales Tracker")
st.caption("SR-wise Sales Performance • Khata (1 Ton = 200,000 BDT), Pen & Stationery • Google Sheets Sync")

try:
    ws = get_worksheet()
    df = load_data(ws)
except Exception as e:
    st.error(f"Google Sheets সংযোগে সমস্যা হয়েছে: {e}")
    st.stop()

st.sidebar.header("নতুন সেলস এন্ট্রি")
product = st.sidebar.selectbox("পণ্য (Product)", ["Khata", "Pen", "Stationery"])

with st.sidebar.form("sales_entry_form", clear_on_submit=True):
    sale_date = st.date_input("তারিখ")
    sr_name = st.text_input("SR-এর নাম", placeholder="যেমন: SR-01 / করিম")

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
        if not sr_name.strip():
            st.sidebar.warning("অনুগ্রহ করে SR-এর নাম লিখুন।")
        elif amount_bdt <= 0 and quantity <= 0:
            st.sidebar.warning("পরিমাণ বা টাকার অঙ্ক ০-এর বেশি হতে হবে।")
        else:
            row = [
                str(sale_date),
                sr_name.strip(),
                product,
                round(float(quantity), 4),
                unit,
                round(float(amount_bdt), 2),
                round(float(khata_tons), 4),
                notes.strip(),
            ]
            ws.append_row(row)
            st.cache_resource.clear()
            st.sidebar.success("সেলস ডাটা Google Sheet-এ সেভ হয়েছে!")
            st.rerun()

# সারসংক্ষেপ (KPIs)
total_bdt = df["Amount_BDT"].sum() if not df.empty else 0.0
total_khata_tons = df["Khata_Tons"].sum() if not df.empty else 0.0
pen_bdt = df[df["Product"] == "Pen"]["Amount_BDT"].sum() if not df.empty else 0.0
stat_bdt = df[df["Product"] == "Stationery"]["Amount_BDT"].sum() if not df.empty else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("মোট সেলস (BDT)", f"৳ {total_bdt:,.2f}")
c2.metric("মোট খাতা (Ton)", f"{total_khata_tons:,.2f} Ton")
c3.metric("Pen সেলস (BDT)", f"৳ {pen_bdt:,.2f}")
c4.metric("Stationery সেলস (BDT)", f"৳ {stat_bdt:,.2f}")

st.divider()

# SR-wise Performance Summary
st.subheader("👤 SR-wise পারফরম্যান্স সামারি")
if df.empty:
    st.info("এখনো কোনো সেলস ডাটা যুক্ত করা হয়নি। বাম পাশ থেকে নতুন এন্ট্রি দিন।")
else:
    sr_summary = (
        df.groupby("SR_Name", as_index=False)
        .agg(
            Total_Sales_BDT=("Amount_BDT", "sum"),
            Khata_Tons=("Khata_Tons", "sum"),
            Pen_BDT=("Amount_BDT", lambda s: s[df.loc[s.index, "Product"] == "Pen"].sum()),
            Stationery_BDT=(
                "Amount_BDT",
                lambda s: s[df.loc[s.index, "Product"] == "Stationery"].sum(),
            ),
            Entries=("SR_Name", "count"),
        )
        .sort_values("Total_Sales_BDT", ascending=False)
    )
    st.dataframe(sr_summary, use_container_width=True, hide_index=True)

    st.subheader("📋 সাম্প্রতিক সেলস লগ")
    st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
