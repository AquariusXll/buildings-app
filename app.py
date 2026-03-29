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

def add_building(sheet, client_name, building_name):
    sheet.append_row([client_name, building_name, "Unknown status"])

def delete_building(sheet, df, client_name, building_name):
    cell = sheet.find(building_name)
    if cell:
        row_data = sheet.row_values(cell.row)
        if row_data[0] == client_name:
            sheet.delete_rows(cell.row)

def delete_client(sheet, df, client_name):
    all_values = sheet.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(all_values[1:], start=2):
        if row[0] == client_name:
            rows_to_delete.append(i)
    for row_num in reversed(rows_to_delete):
        sheet.delete_rows(row_num)

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
clients = sorted(df["Client:"].unique().tolist())

# --- Боковая панель с управлением ---
with st.sidebar:
    st.header("⚙️ Manage")

    # Добавить клиента
    st.subheader("➕ Add Client")
    new_client = st.text_input("Client name:", key="new_client")
    if st.button("Add Client"):
        if new_client.strip() == "":
            st.error("Enter a client name!")
        elif new_client.strip() in clients:
            st.error("This client already exists!")
        else:
            add_building(sheet, new_client.strip(), "First building")
            st.success(f"✅ Client '{new_client}' added!")
            st.cache_resource.clear()
            st.rerun()

    st.divider()

    # Добавить здание
    st.subheader("➕ Add Building")
    selected_client_for_add = st.selectbox("Select client:", clients, key="add_building_client")
    new_building = st.text_input("Building name:", key="new_building")
    if st.button("Add Building"):
        if new_building.strip() == "":
            st.error("Enter a building name!")
        else:
            add_building(sheet, selected_client_for_add, new_building.strip())
            st.success(f"✅ Building '{new_building}' added!")
            st.cache_resource.clear()
            st.rerun()

    st.divider()

    # Удалить здание
    st.subheader("🗑️ Delete Building")
    selected_client_for_del = st.selectbox("Select client:", clients, key="del_building_client")
    client_buildings = df[df["Client:"] == selected_client_for_del]["Building:"].tolist()
    if client_buildings:
        building_to_delete = st.selectbox("Select building:", client_buildings, key="del_building")
        if st.button("Delete Building", type="primary"):
            delete_building(sheet, df, selected_client_for_del, building_to_delete)
            st.success(f"✅ Building '{building_to_delete}' deleted!")
            st.cache_resource.clear()
            st.rerun()
    else:
        st.info("No buildings for this client.")

    st.divider()

    # Удалить клиента
    st.subheader("🗑️ Delete Client")
    client_to_delete = st.selectbox("Select client to delete:", clients, key="del_client")
    st.warning(f"⚠️ This will delete ALL buildings of '{client_to_delete}'!")
    if st.button("Delete Client", type="primary"):
        delete_client(sheet, df, client_to_delete)
        st.success(f"✅ Client '{client_to_delete}' deleted!")
        st.cache_resource.clear()
        st.rerun()

# --- Основной экран ---
st.subheader("📋 View Buildings")
selected_client = st.selectbox("Select client:", clients)
client_df = df[df["Client:"] == selected_client].reset_index(drop=True)

st.markdown(f"### Buildings for: **{selected_client}**")
st.markdown(f"Total: **{len(client_df)}** buildings")

st.divider()

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
            st.cache_resource.clear()
            st.rerun()
