import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time

# --- Настройка ---
SPREADSHEET_ID = "1pBjVOwQS8_1CVsfH3zTRg0MAHjb1STNCbWhKbFg5i60"
SHEET_NAME = "Data"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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

# --- Google Sheets ---
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

def load_data():
    client = get_client()
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data), sheet

def update_status(sheet, row_index, new_status):
    time.sleep(0.5)
    sheet.update_cell(row_index + 2, 3, new_status)

def add_row(sheet, client_name, building_name):
    time.sleep(0.5)
    sheet.append_row([client_name, building_name, "Unknown status"])

def delete_building(sheet, client_name, building_name):
    time.sleep(0.5)
    all_values = sheet.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):
        if row[0] == client_name and row[1] == building_name:
            sheet.delete_rows(i)
            break

def delete_client(sheet, client_name):
    time.sleep(0.5)
    all_values = sheet.get_all_values()
    rows_to_delete = []
    for i, row in enumerate(all_values[1:], start=2):
        if row[0] == client_name:
            rows_to_delete.append(i)
    for row_num in reversed(rows_to_delete):
        sheet.delete_rows(row_num)
        time.sleep(0.3)

def get_client_status(client_buildings_df):
    statuses = client_buildings_df["JSON Status:"].apply(lambda x: str(x).strip()).tolist()
    done_count = sum(1 for s in statuses if s == "Done")
    total = len(statuses)
    if done_count == total:
        return "Done", done_count, total
    elif done_count == 0:
        return "Not started", done_count, total
    else:
        return "In progress", done_count, total

# --- Стили ---
st.markdown("""
    <style>
    .building-card {
        padding: 12px 16px;
        border-radius: 10px;
        margin-bottom: 8px;
    }
    .building-name {
        font-size: 16px;
        font-weight: 600;
        color: white;
    }
    .badge {
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- Инициализация ---
st.set_page_config(page_title="Buildings Tracker", page_icon="🏢", layout="wide")

if "selected_client" not in st.session_state:
    st.session_state["selected_client"] = None
if "confirm_delete" not in st.session_state:
    st.session_state["confirm_delete"] = False

df, sheet = load_data()
clients = sorted(df["Client:"].unique().tolist())

# =====================
# ЭКРАН 1 — Все клиенты
# =====================
if st.session_state["selected_client"] is None:

    st.title("🏢 Buildings Tracker")
    st.markdown(f"**Total clients: {len(clients)}**")
    st.divider()

    for client in clients:
        client_df = df[df["Client:"] == client]
        status_label, done_count, total = get_client_status(client_df)

        if status_label == "Done":
            badge_bg = "#1a7a1a"; badge_color = "#00ff00"; icon = "🟢"
        elif status_label == "Not started":
            badge_bg = "#7a1a1a"; badge_color = "#ff4444"; icon = "🔴"
        else:
            badge_bg = "#7a6a1a"; badge_color = "#ffcc00"; icon = "🟡"

        st.markdown(f"""
            <div style="position:relative; padding:14px 18px; border-radius:10px;
            margin-bottom:8px; background-color:#1e1e2e; border:1px solid #333;">
                <span style="font-size:16px; font-weight:600; color:white;">
                    🏢 {client}
                </span>
                &nbsp;&nbsp;
                <span style="padding:4px 14px; border-radius:20px; font-size:13px;
                font-weight:600; background-color:{badge_bg}; color:{badge_color};">
                    {icon} {status_label} &nbsp;|&nbsp; {done_count}/{total} facilities
                </span>
            </div>
        """, unsafe_allow_html=True)

        if st.button("", key=f"open_{client}", help=f"Open {client}", use_container_width=True):
            st.session_state["selected_client"] = client
            st.session_state["confirm_delete"] = False
            st.rerun()

        st.markdown("""
            <style>
            div[data-testid="stButton"] button {
                margin-top: -58px;
                height: 50px;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }
            div[data-testid="stButton"] button:hover {
                background: rgba(255,255,255,0.05) !important;
                border-radius: 10px !important;
            }
            </style>
        """, unsafe_allow_html=True)

    st.divider()

    with st.expander("➕ Add new client"):
        new_client_name = st.text_input("Client name:")
        first_building = st.text_input("First facility:")
        if st.button("Create", type="primary"):
            if new_client_name.strip() == "" or first_building.strip() == "":
                st.error("Please fill in both fields!")
            elif new_client_name.strip() in clients:
                st.error("Client already exists!")
            else:
                add_row(sheet, new_client_name.strip(), first_building.strip())
                st.success(f"✅ Client '{new_client_name}' created!")
                st.cache_resource.clear()
                st.rerun()

# =====================
# ЭКРАН 2 — Детали клиента
# =====================
else:
    selected_client = st.session_state["selected_client"]
    client_df = df[df["Client:"] == selected_client].reset_index(drop=True)

    # --- Назад ---
    if st.button("← Back to all clients"):
        st.session_state["selected_client"] = None
        st.session_state["confirm_delete"] = False
        st.rerun()

    # --- Заголовок ---
    status_label, done_count, total = get_client_status(client_df)
    if status_label == "Done":
        badge_bg = "#1a7a1a"; badge_color = "#00ff00"; icon = "🟢"
    elif status_label == "Not started":
        badge_bg = "#7a1a1a"; badge_color = "#ff4444"; icon = "🔴"
    else:
        badge_bg = "#7a6a1a"; badge_color = "#ffcc00"; icon = "🟡"

    st.markdown(f"## 🏢 {selected_client}")
    st.markdown(f"""
        <span class="badge" style="background-color:{badge_bg}; color:{badge_color};">
            {icon} {status_label} &nbsp;|&nbsp; {done_count}/{total} facilities
        </span>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Удалить клиента ---
    if st.button("🗑️ Delete this client", type="primary"):
        st.session_state["confirm_delete"] = True

    if st.session_state["confirm_delete"]:
        st.warning(f"⚠️ Delete **{selected_client}** and ALL their facilities?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete"):
                delete_client(sheet, selected_client)
                st.session_state["selected_client"] = None
                st.session_state["confirm_delete"] = False
                st.cache_resource.clear()
                st.rerun()
        with c2:
            if st.button("Cancel"):
                st.session_state["confirm_delete"] = False
                st.rerun()

    st.divider()

    # --- Здания ---
    for i, row in client_df.iterrows():
        raw_status = str(row["JSON Status:"]).strip()
        current_status = raw_status if raw_status in STATUS_OPTIONS else "Unknown status"
        bg_color = STATUS_COLORS.get(current_status, "#3a3a3a")
        text_color = STATUS_TEXT_COLORS.get(current_status, "#aaaaaa")
        icon = STATUS_ICONS.get(current_status, "⚪")

        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.markdown(f"""
                <div class="building-card" style="background-color: {bg_color};">
                    <span class="building-name">{row['Building:']}</span>
                    &nbsp;&nbsp;
                    <span class="badge" style="color: {text_color};">
                        {icon} {current_status}
                    </span>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            new_status = st.selectbox(
                "Change status:",
                STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(current_status),
                key=f"status_{selected_client}_{i}"
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

        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{selected_client}_{i}", help="Delete facility"):
                delete_building(sheet, selected_client, row["Building:"])
                st.success("✅ Deleted!")
                st.cache_resource.clear()
                st.rerun()

    st.divider()

    # --- Добавить здание ---
    with st.expander("➕ Add new facility"):
        new_building = st.text_input("Facility name:", key="new_building_input")
        if st.button("Add facility", type="primary"):
            if new_building.strip() == "":
                st.error("Enter a facility name!")
            else:
                add_row(sheet, selected_client, new_building.strip())
                st.success(f"✅ '{new_building}' added!")
                st.cache_resource.clear()
                st.rerun()
