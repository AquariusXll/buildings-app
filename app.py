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
    if all(s == "Done" for s in statuses):
        return "Done"
    elif any(s == "Done" for s in statuses):
        done_count = sum(1 for s in statuses if s == "Done")
        return f"{done_count}/{len(statuses)} Done"
    else:
        return "Not started"

# --- Стили ---
st.markdown("""
    <style>
    .client-row {
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: pointer;
        background-color: #1e1e2e;
        border: 1px solid #333;
        transition: background 0.2s;
    }
    .client-name {
        font-size: 16px;
        font-weight: 600;
        color: white;
    }
    .client-badge {
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
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

# --- Инициализация ---
st.set_page_config(page_title="Buildings Tracker", page_icon="🏢", layout="wide")

if "selected_client" not in st.session_state:
    st.session_state["selected_client"] = None

df, sheet = load_data()
clients = sorted(df["Client:"].unique().tolist())

# --- Навигация (вкладки) ---
tab1, tab2 = st.tabs(["📋 All Clients", "🏢 Client Details"])

# =====================
# ВКЛАДКА 1 — Все клиенты
# =====================
with tab1:
    st.title("🏢 Buildings Tracker")
    st.markdown(f"**Total clients: {len(clients)}**")
    st.divider()

    for client in clients:
        client_df = df[df["Client:"] == client]
        client_status = get_client_status(client_df)
        total = len(client_df)
        done = sum(1 for s in client_df["JSON Status:"] if str(s).strip() == "Done")

        if client_status == "Done":
            badge_color = "#1a7a1a"
            badge_text_color = "#00ff00"
            badge_icon = "🟢"
        elif client_status == "Not started":
            badge_color = "#7a1a1a"
            badge_text_color = "#ff4444"
            badge_icon = "🔴"
        else:
            badge_color = "#7a6a1a"
            badge_text_color = "#ffcc00"
            badge_icon = "🟡"

        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"""
                <div class="client-row">
                    <span class="client-name">🏢 {client}</span>
                    <span class="client-badge" style="background-color:{badge_color}; color:{badge_text_color};">
                        {badge_icon} {client_status} &nbsp;|&nbsp; {done}/{total} facilities
                    </span>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            if st.button("Open →", key=f"open_{client}"):
                st.session_state["selected_client"] = client
                st.rerun()

    st.divider()

    # --- Добавить клиента ---
    with st.expander("➕ Add new client"):
        new_client_name = st.text_input("Client name:", key="new_client_name")
        first_building = st.text_input("First facility:", key="first_building")
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
# ВКЛАДКА 2 — Детали клиента
# =====================
with tab2:
    if st.session_state["selected_client"] is None:
        st.info("👈 Select a client from the 'All Clients' tab")
    else:
        selected_client = st.session_state["selected_client"]
        client_df = df[df["Client:"] == selected_client].reset_index(drop=True)

        col_title, col_delete = st.columns([4, 1])
        with col_title:
            st.title(f"🏢 {selected_client}")
            st.markdown(f"Total facilities: **{len(client_df)}**")
        with col_delete:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Delete client", type="primary"):
                st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning(f"⚠️ Delete **{selected_client}** and ALL facilities?")
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
