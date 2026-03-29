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

# --- Выбор клиента ---
st.subheader("Select client:")

selected_client = st.selectbox(
    "Select client:",
    clients + ["➕ Add new client..."],
    label_visibility="collapsed"
)

# --- Добавить нового клиента ---
if selected_client == "➕ Add new client...":
    st.markdown("### ➕ Add New Client")
    new_client_name = st.text_input("Client name:")
    first_building_name = st.text_input("First facility name:")
    if st.button("Create Client", type="primary"):
        if new_client_name.strip() == "" or first_building_name.strip() == "":
            st.error("Please fill in both fields!")
        elif new_client_name.strip() in clients:
            st.error("This client already exists!")
        else:
            add_row(sheet, new_client_name.strip(), first_building_name.strip())
            st.success(f"✅ Client '{new_client_name}' created!")
            st.cache_resource.clear()
            st.rerun()

else:
    client_df = df[df["Client:"] == selected_client].reset_index(drop=True)

    col_title, col_delete_client = st.columns([4, 1])
    with col_title:
        st.markdown(f"### 🏢 {selected_client}")
        st.markdown(f"Total facilities: **{len(client_df)}**")
    with col_delete_client:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Delete this client", type="primary"):
            st.session_state["confirm_delete_client"] = True

    if st.session_state.get("confirm_delete_client"):
        st.warning(f"⚠️ Are you sure you want to delete **{selected_client}** and ALL their facilities?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("Yes, delete"):
                delete_client(sheet, selected_client)
                st.success(f"✅ Client '{selected_client}' deleted!")
                st.cache_resource.clear()
                st.session_state["confirm_delete_client"] = False
                st.rerun()
        with col_no:
            if st.button("Cancel"):
                st.session_state["confirm_delete_client"] = False
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

        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{i}", help="Delete this facility"):
                delete_building(sheet, selected_client, row["Building:"])
                st.success("✅ Deleted!")
                st.cache_resource.clear()
                st.rerun()

    st.divider()

    # --- Добавить здание ---
    st.markdown("### ➕ Add new facility")
    new_building = st.text_input("Facility name:", key="new_building_input")
    if st.button("Add facility", type="primary"):
        if new_building.strip() == "":
            st.error("Enter a facility name!")
        else:
            add_row(sheet, selected_client, new_building.strip())
            st.success(f"✅ '{new_building}' added!")
            st.cache_resource.clear()
            st.rerun()
