import json
from datetime import date, timedelta
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="TSM Sales Tracker", layout="wide")

# --- Colorful & Mobile Responsive CSS ---
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 38%, #f1f5f9 100%);
        }

        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.5rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
        }

        .hero-banner {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #0ea5e9 100%);
            color: #ffffff;
            padding: 18px 22px;
            border-radius: 16px;
            margin-bottom: 16px;
            box-shadow: 0 8px 20px rgba(37, 99, 235, 0.18);
        }

        .hero-banner h1 {
            color: #ffffff !important;
            margin: 0 !important;
            padding: 0 !important;
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }

        .hero-banner p {
            color: #e0f2fe !important;
            margin: 6px 0 0 0 !important;
            font-size: 0.92rem !important;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #dbeafe;
            border-top: 4px solid #2563eb;
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.12);
        }

        [data-testid="stMetricLabel"] > div {
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            color: #334155 !important;
        }

        [data-testid="stMetricValue"] > div {
            font-size: 1.32rem !important;
            font-weight: 800 !important;
            color: #0f172a !important;
        }

        .sku-card {
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
        }

        .sku-pen {
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border-left: 5px solid #2563eb;
            color: #0f172a;
        }

        .sku-stat {
            background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
            border-left: 5px solid #7c3aed;
            color: #0f172a;
        }

        .sku-khata {
            background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
            border-left: 5px solid #059669;
            color: #0f172a;
        }

        .session-half {
            background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
            border-left: 5px solid #d97706;
            color: #0f172a;
        }

        .session-full {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-left: 5px solid #0284c7;
            color: #0f172a;
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

        .stButton > button:hover, .stFormSubmitButton > button:hover {
            background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
            color: #ffffff;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #cbd5e1;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
        }

        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.85rem;
                padding-bottom: 2rem;
                padding-left: 0.75rem;
                padding-right: 0.75rem;
            }

            .hero-banner {
                padding: 14px 16px;
                border-radius: 12px;
            }

            .hero-banner h1 {
                font-size: 1.35rem !important;
            }

            .hero-banner p {
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
            cfg_ws
