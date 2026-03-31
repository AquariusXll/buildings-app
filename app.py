import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import time
import io

# --- Настройка ---
SPREADSHEET_ID = "1pBjVOwQS8_1CVsfH3zTRg0MAHjb1STNCbWhKbFg5i60"
SHEET_NAME = "Data"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

STATUS_COLORS = {
    "Done": "#1a7a1a",
    "Undone": "#7a1a1a",
    "In progress": "#1a3a7a",
    "Outdoors only": "#7a6a1a",
    "Unknown status": "#3a3a3a"
}
STATUS_TEXT_COLORS = {
    "Done": "#00ff00",
    "Undone": "#ff4444",
    "In progress": "#4488ff",
    "Outdoors only": "#ffcc00",
    "Unknown status": "#aaaaaa"
}
STATUS_ICONS = {
    "Done": "🟢",
    "Undone": "🔴",
    "In progress": "🔵",
    "Outdoors only": "🟡",
    "Unknown status": "⚪"
}
STATUS_OPTIONS = ["Done", "Undone", "In progress", "Outdoors only", "Unknown status"]

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

def update_done_by(sheet, row_index, done_by):
    time.sleep(0.5)
    sheet.update_cell(row_index + 2, 4, done_by)

def add_row(sheet, client_name, building_name):
    time.sleep(0.5)
    sheet.append_row([client_name, building_name, "Unknown status", ""])

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

def rename_client(sheet, old_name, new_name):
    time.sleep(0.5)
    all_values = sheet.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):
        if row[0] == old_name:
            sheet.update_cell(i, 1, new_name)
            time.sleep(0.2)

def rename_building(sheet, client_name, old_name, new_name):
    time.sleep(0.5)
    all_values = sheet.get_all_values()
    for i, row in enumerate(all_values[1:], start=2):
        if row[0] == client_name and row[1] == old_name:
            sheet.update_cell(i, 2, new_name)
            break

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

def export_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="All Data")
        for client in df["Client:"].unique():
            client_df = df[df["Client:"] == client]
            safe_name = client[:31]
            client_df.to_excel(writer, index=False, sheet_name=safe_name)
    return output.getvalue()

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
if "editing_client" not in st.session_state:
    st.session_state["editing_client"] = False
if "editing_building" not in st.session_state:
    st.session_state["editing_building"] = None

df, sheet = load_data()

if "Done by:" not in df.columns:
    df["Done by:"] = ""

clients = sorted(df["Client:"].unique().tolist())

# =====================
# ЭКРАН 1 — Все клиенты
# =====================
if st.session_state["selected_client"] is None:

    st.title("🏢 Buildings Tracker")

    # --- Счётчик ---
    client_statuses = [get_client_status(df[df["Client:"] == c]) for c in clients]
    done_clients = sum(1 for s in client_statuses if s[0] == "Done")
    progress_clients = sum(1 for s in client_statuses if s[0] == "In progress")
    not_started_clients = sum(1 for s in client_statuses if s[0] == "Not started")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total clients", len(clients))
    c2.metric("🟢 Done", done_clients)
    c3.metric("🟡 In progress", progress_clients)
    c4.metric("🔴 Not started", not_started_clients)

    st.divider()

    # --- Поиск + Фильтр + Сортировка ---
    col_search, col_filter, col_sort = st.columns([3, 2, 2])
    with col_search:
        search = st.text_input("🔍 Search client:", placeholder="Type client name...")
    with col_filter:
        status_filter = st.selectbox("Filter by status:", ["All", "Done", "In progress", "Not started"])
    with col_sort:
        sort_by = st.selectbox("Sort by:", ["Name (A-Z)", "Name (Z-A)", "Status (Done first)", "Status (Not started first)"])

    excel_data = export_excel(df)
    st.download_button(
        label="📥 Export to Excel",
        data=excel_data,
        file_name="buildings_tracker.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # --- Фильтрация и сортировка ---
    client_data = []
    for client, (status_label, done_count, total) in zip(clients, client_statuses):
        client_data.append({
            "name": client,
            "status": status_label,
            "done": done_count,
            "total": total
        })

    if search:
        client_data = [c for c in client_data if search.lower() in c["name"].lower()]
    if status_filter != "All":
        client_data = [c for c in client_data if c["status"] == status_filter]

    order_map = {
        "Name (A-Z)": lambda x: x["name"],
        "Name (Z-A)": lambda x: x["name"],
        "Status (Done first)": lambda x: {"Done": 0, "In progress": 1, "Not started": 2}[x["status"]],
        "Status (Not started first)": lambda x: {"Not started": 0, "In progress": 1, "Done": 2}[x["status"]]
    }
    reverse = sort_by == "Name (Z-A)"
    client_data = sorted(client_data, key=order_map[sort_by], reverse=reverse)

    st.markdown(f"Showing **{len(client_data)}** clients")

    # --- Список клиентов ---
    for c in client_data:
        client = c["name"]
        status_label = c["status"]
        done_count = c["done"]
        total = c["total"]
        progress = done_count / total if total > 0 else 0

        if status_label == "Done":
            icon = "🟢"
        elif status_label == "Not started":
            icon = "🔴"
        else:
            icon = "🟡"

        progress_bar = "▓" * int(progress * 20) + "░" * (20 - int(progress * 20))

        if st.button(
            f"🏢  {client}   |   {icon} {status_label}  ·  {done_count}/{total}  {progress_bar}",
            key=f"open_{client}",
            use_container_width=True
        ):
            st.session_state["selected_client"] = client
            st.session_state["confirm_delete"] = False
            st.session_state["editing_client"] = False
            st.session_state["editing_building"] = None
            st.rerun()

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

    if st.button("← Back to all clients"):
        st.session_state["selected_client"] = None
        st.session_state["confirm_delete"] = False
        st.session_state["editing_client"] = False
        st.session_state["editing_building"] = None
        st.rerun()

    status_label, done_count, total = get_client_status(client_df)
    if status_label == "Done":
        badge_bg = "#1a7a1a"; badge_color = "#00ff00"; icon = "🟢"
    elif status_label == "Not started":
        badge_bg = "#7a1a1a"; badge_color = "#ff4444"; icon = "🔴"
    else:
        badge_bg = "#7a6a1a"; badge_color = "#ffcc00"; icon = "🟡"

    col_title, col_edit, col_delete = st.columns([4, 1, 1])
    with col_title:
        st.markdown(f"## 🏢 {selected_client}")
        st.markdown(f"""
            <span class="badge" style="background-color:{badge_bg}; color:{badge_color};">
                {icon} {status_label} &nbsp;|&nbsp; {done_count}/{total} facilities
            </span>
        """, unsafe_allow_html=True)
        progress = done_count / total if total > 0 else 0
        st.markdown(f"""
            <div style="margin-top:10px; background:#333; border-radius:10px; height:8px; width:50%;">
                <div style="width:{int(progress*100)}%; background:{badge_color};
                border-radius:10px; height:8px;"></div>
            </div>
        """, unsafe_allow_html=True)

    with col_edit:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✏️ Rename"):
            st.session_state["editing_client"] = True

    with col_delete:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Delete", type="primary"):
            st.session_state["confirm_delete"] = True

    if st.session_state.get("editing_client"):
        new_name = st.text_input("New client name:", value=selected_client)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save name", type="primary"):
                if new_name.strip() and new_name.strip() != selected_client:
                    rename_client(sheet, selected_client, new_name.strip())
                    st.session_state["selected_client"] = new_name.strip()
                    st.session_state["editing_client"] = False
                    st.cache_resource.clear()
                    st.rerun()
        with c2:
            if st.button("Cancel rename"):
                st.session_state["editing_client"] = False
                st.rerun()

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

    client_export = export_excel(df[df["Client:"] == selected_client])
    st.download_button(
        label="📥 Export to Excel",
        data=client_export,
        file_name=f"{selected_client}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # --- Здания ---
    for i, row in client_df.iterrows():
        raw_status = str(row["JSON Status:"]).strip()
        current_status = raw_status if raw_status in STATUS_OPTIONS else "Unknown status"
        bg_color = STATUS_COLORS.get(current_status, "#3a3a3a")
        text_color = STATUS_TEXT_COLORS.get(current_status, "#aaaaaa")
        icon = STATUS_ICONS.get(current_status, "⚪")
        current_done_by = str(row.get("Done by:", "")).strip() if "Done by:" in row else ""

        col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])

        with col1:
            st.markdown(f"""
                <div class="building-card" style="background-color: {bg_color};">
                    <span class="building-name">{row['Building:']}</span>
                    &nbsp;&nbsp;
                    <span class="badge" style="color: {text_color};">
                        {icon} {current_status}
                    </span>
                    {f'<br><span style="font-size:12px; color:#ddd; margin-top:4px; display:block;">👤 {current_done_by}</span>' if current_done_by else ''}
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
            new_done_by = st.text_input(
                "Done by:",
                value=current_done_by,
                placeholder="Enter name...",
                key=f"done_by_{selected_client}_{i}"
            )
            if st.button("💾 Save", key=f"save_done_by_{selected_client}_{i}"):
                original_index = df[
                    (df["Client:"] == selected_client) &
                    (df["Building:"] == row["Building:"])
                ].index[0]
                update_done_by(sheet, original_index, new_done_by.strip())
                st.success("✅ Saved!")
                st.cache_resource.clear()
                st.rerun()

        with col4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️", key=f"edit_{selected_client}_{i}", help="Rename facility"):
                st.session_state["editing_building"] = i

        with col5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_{selected_client}_{i}", help="Delete facility"):
                delete_building(sheet, selected_client, row["Building:"])
                st.success("✅ Deleted!")
                st.cache_resource.clear()
                st.rerun()

        if st.session_state.get("editing_building") == i:
            new_building_name = st.text_input(
                "New facility name:",
                value=row["Building:"],
                key=f"rename_input_{i}"
            )
            r1, r2 = st.columns(2)
            with r1:
                if st.button("Save", type="primary", key=f"save_rename_{i}"):
                    if new_building_name.strip() and new_building_name.strip() != row["Building:"]:
                        rename_building(sheet, selected_client, row["Building:"], new_building_name.strip())
                        st.session_state["editing_building"] = None
                        st.cache_resource.clear()
                        st.rerun()
            with r2:
                if st.button("Cancel", key=f"cancel_rename_{i}"):
                    st.session_state["editing_building"] = None
                    st.rerun()

    st.divider()

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
