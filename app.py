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

# Цвета статусов
STATUS_COLORS = {
    "Done": "🟢",
    "Undone": "🔴",
    "Outdoors only": "🟡",
    "Unknown status": "⚪"
}

STATUS_OPTIONS = ["Done", "Undone", "Outdoors only", "Unknown status"]

# Таблица зданий
for i, row in client_df.iterrows():
    col1, col2 = st.columns([3, 2])

    with col1:
        st.write(f"**{row['Building:']}**")

    with col2:
        icon = STATUS_COLORS.get(row["JSON Status:"], "⚪")
        new_status = st.selectbox(
            f"{icon} Status",
            STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(row["JSON Status:"]) if row["JSON Status:"] in STATUS_OPTIONS else 3,
            key=f"status_{i}"
        )

        if new_status != row["JSON Status:"]:
            original_index = df[
                (df["Client:"] == selected_client) &
                (df["Building:"] == row["Building:"])
            ].index[0]
            update_status(sheet, original_index, new_status)
            st.success("✅ Saved!")
            st.rerun()
