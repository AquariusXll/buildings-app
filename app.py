import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- Настройка ---
SPREADSHEET_ID = "1pBjVOwQS8_1CVsfH3zTRg0MAHjb1STNCbWhKbFg5i60"
SHEET_NAME = "Data"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

# --- Цвета статусов ---
STATUS_COLORS = {
    "Done": "#1a7a1a",
    "Undone": "#7a1a1a",
    "Outdoors only": "#7a6a1a",
    "Unknown status": "#3a3a3a"
}

STATUS_TEXT_COLORS = {
    "Done": "#00ff00",
    "Undone": "#ff4444",
    "Outdoors only": "#ffcc00",
    "Unknown status": "#aaaaaa"
}

STATUS_ICONS = {
    "Done": "🟢",
    "Undone": "🔴",
    "Outdoors only": "🟡",
    "Unknown status": "⚪"
}

STATUS_OPTIONS = ["Done", "Undone", "Outdoors only", "Unknown status"]

# --- Подключение к Google Sheets ---
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

def load_data():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data), sheet

def update_status(sheet, row_index, new_status):
    sheet.update_cell(row_index + 2, 3, new_status)

# --- Стили ---
st.markdown("""
    <style>
    .building-card {
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .building-name {
        font-size: 16px;
        font-weight: 600;
        color: white;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- Интерфейс ---
st.set_page_config(page_title="Buildings Tracker", page_icon="🏢", layout="wide")

st.title("🏢 Buildings Tracker")

df, sheet = load_data()

# Выбор клиента
clients = sorted(df["Client:"].unique().tolist())
selected_client = st.selectbox("Select client:", clients)

# Фильтр по клиенту
client_df = df[df["Client:"] == selected_client].reset_index(drop=True)

st.markdown(f"### Buildings for: **{selected_client}**")
st.markdown(f"Total: **{len(client_df)}** buildings")

st.divider()

# Таблица зданий
for i, row in client_df.iterrows():
    current_status = row["JSON Status:"] if row["JSON Status:"] in STATUS_OPTIONS else "Unknown status"
    bg_color = STATUS_COLORS.get(current_status, "#3a3a3a")
    text_color = STATUS_TEXT_COLORS.get(current_status, "#aaaaaa")
    icon = STATUS_ICONS.get(current_status, "⚪")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown(f"""
            <div class="building-card" style="background-color: {bg_color};">
                <span class="building-name">{row['Building:']}</span>
                <span class="status-badge" style="color: {text_color};">
                    {icon} {current_status}
                </span>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        new_status = st.selectbox(
            "Change status:",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(current_status),
            key=f"status_{i}"
        )

        if new_status != current_status:
            original_index = df[
                (df["Client:"] == selected_client) &
                (df["Building:"] == row["Building:"])
            ].index[0]
            update_status(sheet, original_index, new_status)
            st.success("✅ Saved!")
            st.rerun()
