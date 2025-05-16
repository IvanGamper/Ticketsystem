import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, inspect

# --- Global Configuration ---
st.set_page_config(page_title="Support Workflow & DB Admin", page_icon="⚙️")
st.title("⚙️ Support Ticket Workflow & Datenbankverwaltung")

# --- Database Configuration (from pasted_content_2.txt) ---
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"  # WICHTIG: In einer Produktivumgebung sollten Passwörter sicher verwaltet werden (z.B. Umgebungsvariablen, Secrets Manager)
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystem02"

# SQLAlchemy Engine (using pymysql as in pasted_content_2.txt)
db_connection_successful = False
engine = None
inspector = None
try:
    engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    with engine.connect() as connection: # Test connection
        pass # Connection successful if no exception
    inspector = inspect(engine)
    db_connection_successful = True
except Exception as e:
    db_error_message = str(e)
    # Error will be displayed in the relevant DB Admin tab or globally if needed

# --- Main Application Tabs ---
main_tab1, main_tab2 = st.tabs(["🎫 Support Ticket Workflow (Simuliert)", "🛠️ Datenbankverwaltung (Live)"])

# --- Tab 1: Support Ticket Workflow (Simulated - from pasted_content.txt) ---
with main_tab1:
    st.header("Simulierter Support Ticket Workflow")
    st.info("Dieser Bereich simuliert einen Ticket-Workflow mit generierten Daten. Es findet keine Interaktion mit der Datenbank statt.")

    # Generate data functions (from pasted_content.txt)
    np.random.seed(42)

    def generate_issue():
        issues = [
            "Network connectivity issues in the office", "Software application crashing on startup",
            "Printer not responding to print commands", "Email server downtime", "Data backup failure",
            "Login authentication problems", "Website performance degradation", "Security vulnerability identified",
            "Hardware malfunction in the server room", "Employee unable to access shared files",
            "Database connection failure", "Mobile application not syncing data", "VoIP phone system issues",
            "VPN connection problems for remote employees", "System updates causing compatibility issues",
            "File server running out of storage space", "Intrusion detection system alerts",
            "Inventory management system errors", "Customer data not loading in CRM",
            "Collaboration tool not sending notifications"
        ]
        return np.random.choice(issues)

    start_date_sim = datetime(2024, 6, 1)
    end_date_sim = datetime(2024, 12, 20)
    id_values_sim = [f"SIM-TICKET-{i}" for i in range(1000, 1100)]
    issue_list_sim = [generate_issue() for _ in range(100)]

    def generate_random_dates_sim(start_date, end_date, id_values):
        date_range = pd.date_range(start_date, end_date).strftime("%m-%d-%Y")
        return np.random.choice(date_range, size=len(id_values), replace=False)

    data_sim = {
        "Issue": issue_list_sim,
        "Status": np.random.choice(["Open", "In Progress", "Closed"], size=100),
        "Priority": np.random.choice(["High", "Medium", "Low"], size=100),
        "Date Submitted": generate_random_dates_sim(start_date_sim, end_date_sim, id_values_sim)
    }
    df_initial_sim = pd.DataFrame(data_sim)
    df_initial_sim.insert(0, "ID", id_values_sim)
    df_initial_sim = df_initial_sim.sort_values(by=["Status", "ID"], ascending=[False, False])

    if "df_simulated_tickets" not in st.session_state:
        st.session_state.df_simulated_tickets = df_initial_sim.copy()

    def sort_df_sim():
        st.session_state.df_simulated_tickets = st.session_state.edited_df_sim.copy().sort_values(by=["Status", "ID"], ascending=[False, False])

    sim_tabs = st.tabs(["Ticket schreiben (Simuliert)", "Ticketstatus & Analytics (Simuliert)"])

    with sim_tabs[0]:
        st.subheader("Neues simuliertes Ticket erstellen")
        if not st.session_state.df_simulated_tickets.empty:
            try:
                numeric_ids = [int(tid.split("-")[-1]) for tid in st.session_state.df_simulated_tickets.ID if tid.startswith("SIM-TICKET-") and tid.split("-")[-1].isdigit()]
                recent_ticket_number_sim = max(numeric_ids) if numeric_ids else 999
            except ValueError:
                recent_ticket_number_sim = len(st.session_state.df_simulated_tickets) + 999 # Fallback
        else:
            recent_ticket_number_sim = 999

        with st.form("sim_ticket_addition"):
            sim_issue = st.text_area("Beschreibung des Problems (Simuliert)", key="sim_issue")
            sim_priority = st.selectbox("Priorität (Simuliert)", ["High", "Medium", "Low"], key="sim_priority")
            sim_submit = st.form_submit_button("Absenden (Simuliert)")

        if sim_submit:
            if not sim_issue.strip():
                st.warning("Bitte geben Sie eine Beschreibung des simulierten Problems ein.")
            else:
                sim_today_date = datetime.now().strftime("%m-%d-%Y")
                sim_df2 = pd.DataFrame([{
                    "ID": f"SIM-TICKET-{recent_ticket_number_sim + 1}",
                    "Issue": sim_issue,
                    "Status": "Open",
                    "Priority": sim_priority,
                    "Date Submitted": sim_today_date
                }])
                st.write("Simuliertes Ticket eingereicht!")
                st.dataframe(sim_df2, use_container_width=True, hide_index=True)
                st.session_state.df_simulated_tickets = pd.concat([st.session_state.df_simulated_tickets, sim_df2], axis=0).sort_values(by=["Status", "ID"], ascending=[False, False])

    with sim_tabs[1]:
        sim_status_col = st.columns((3, 1))
        with sim_status_col[0]:
            st.subheader("Status simulierter Support Tickets")
        with sim_status_col[1]:
            st.write(f"Anzahl simulierter Tickets: `{len(st.session_state.df_simulated_tickets)}`")

        st.markdown("**Was Sie ausprobieren können:**")
        st.info("1️⃣ Aktualisieren Sie den **Status** oder die **Priorität** der simulierten Tickets und beobachten Sie, wie die Diagramme in Echtzeit aktualisiert werden!")
        st.success("2️⃣ Ändern Sie Werte in der Spalte **Status** von *\"Open\"* zu *\"In Progress\"* oder *\"Closed\"*, klicken Sie dann auf den Button **Simuliertes DataFrame nach Status sortieren**, um das aktualisierte DataFrame zu sehen.")

        st.session_state.edited_df_sim = st.data_editor(st.session_state.df_simulated_tickets, use_container_width=True, hide_index=True, height=212,
                                                        column_config={
                                                            "Status": st.column_config.SelectboxColumn(
                                                                "Status", help="Ticket Status", width="medium",
                                                                options=["Open", "In Progress", "Closed"], required=True),
                                                            "Priority": st.column_config.SelectboxColumn(
                                                                "Priorität", help="Ticket Priorität", width="medium",
                                                                options=["High", "Medium", "Low"], required=True),
                                                        }, key="sim_data_editor")
        st.button("🔄 Simuliertes DataFrame nach Status sortieren", on_click=sort_df_sim, key="sim_sort_button")

        st.subheader("Analyse simulierter Support Tickets")
        sim_plot_col = st.columns((1, 3, 1))

        with sim_plot_col[0]:
            n_tickets_queue_sim = len(st.session_state.edited_df_sim[st.session_state.edited_df_sim.Status == "Open"])
            st.metric(label="Sim. First Response Time (hr)", value=5.2, delta=-1.5)
            st.metric(label="Sim. Tickets in Warteschlange", value=n_tickets_queue_sim, delta="")
            st.metric(label="Sim. Avg. Resolution Time (hr)", value=16, delta="")

        with sim_plot_col[1]:
            df_for_plot_sim = st.session_state.edited_df_sim.copy()
            df_for_plot_sim["Date Submitted"] = pd.to_datetime(df_for_plot_sim["Date Submitted"])

            status_plot_sim = alt.Chart(df_for_plot_sim).mark_bar().encode(
                x=alt.X("month(Date Submitted):O", title="Monat der Einreichung"),
                y=alt.Y("count():Q", title="Anzahl Tickets"),
                xOffset="Status:N",
                color="Status:N"
            ).properties(title="Simulierter Ticketstatus der letzten Monate", height=300).configure_legend(orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5)
            st.altair_chart(status_plot_sim, use_container_width=True, theme="streamlit")

        with sim_plot_col[2]:
            priority_plot_sim = alt.Chart(st.session_state.edited_df_sim).mark_arc().encode(
                theta=alt.Theta("count():Q", title="Anzahl"),
                color=alt.Color("Priority:N", title="Priorität")
            ).properties(title="Aktuelle simulierte Ticketpriorität", height=300).configure_legend(orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5)
            st.altair_chart(priority_plot_sim, use_container_width=True, theme="streamlit")

# --- Tab 2: Datenbankverwaltung (Live - from pasted_content_2.txt) ---
with main_tab2:
    st.header("Datenbankverwaltung (Live)")

    if not db_connection_successful:
        st.error(f"❌ Datenbankverbindung fehlgeschlagen: {db_error_message}")
        st.warning("Bitte überprüfen Sie die Datenbankkonfiguration und stellen Sie sicher, dass der MySQL-Server läuft und erreichbar ist.")
    else:
        st.info("Dieser Bereich interagiert direkt mit der konfigurierten MySQL-Datenbank.")
        @st.cache_data(ttl=30)
        def get_db_columns(table_name):
            try:
                return [col["name"] for col in inspector.get_columns(table_name)]
            except Exception as e:
                st.error(f"Fehler beim Abrufen der Spalten für Tabelle {table_name}: {e}")
                return []

        db_admin_tabs = st.tabs(["📋 Tabellen Anzeigen", "➕ Datensatz Einfügen", "❌ Datensatz Löschen"])

        with db_admin_tabs[0]: # Anzeigen
            st.subheader("Tabelle anzeigen")
            try:
                tabellen = inspector.get_table_names()
                if not tabellen:
                    st.warning("Keine Tabellen in der Datenbank gefunden.")
                else:
                    table_choice_view = st.selectbox("Wähle eine Tabelle zum Anzeigen", tabellen, key="db_view_table_select")
                    if st.button("🔄 Daten der Tabelle laden", key="db_view_data_button"):
                        if table_choice_view:
                            try:
                                df_table_view = pd.read_sql(f"SELECT * FROM {table_choice_view}", con=engine)
                                st.dataframe(df_table_view, use_container_width=True)
                            except Exception as e_view:
                                st.error(f"Fehler beim Laden der Daten aus Tabelle {table_choice_view}: {e_view}")
                        else:
                            st.info("Bitte eine Tabelle auswählen.")
            except Exception as e:
                st.error(f"❌ Fehler beim Laden der Tabellenübersicht: {e}")

        with db_admin_tabs[1]: # Einfügen
            st.subheader("Datensatz einfügen")
            try:
                tabellen_insert = inspector.get_table_names()
                if not tabellen_insert:
                    st.warning("Keine Tabellen zum Einfügen von Daten gefunden.")
                else:
                    table_choice_insert = st.selectbox("Tabelle wählen (Einfügen)", tabellen_insert, key="db_insert_table_select")
                    if table_choice_insert:
                        spalten_insert = get_db_columns(table_choice_insert)
                        if not spalten_insert:
                            st.info(f"Keine Spalten für Tabelle {table_choice_insert} gefunden oder die Tabelle ist möglicherweise leer und die Struktur konnte nicht ermittelt werden.")
                        else:
                            with st.form(key=f"db_insert_form_{table_choice_insert}"):
                                inputs_insert = {}
                                for spalte in spalten_insert:
                                    inputs_insert[spalte] = st.text_input(f"{spalte}", key=f"db_insert_{table_choice_insert}_{spalte}")
                                submitted_insert = st.form_submit_button("💾 Einfügen")

                            if submitted_insert:
                                try:
                                    data_to_insert = {col: (inputs_insert[col] if inputs_insert[col] else None) for col in spalten_insert}
                                    with engine.begin() as conn:
                                        placeholders = ", ".join([f":{col}" for col in spalten_insert])
                                        query_insert = text(f"INSERT INTO {table_choice_insert} ({', '.join(spalten_insert)}) VALUES ({placeholders})")
                                        conn.execute(query_insert, data_to_insert)
                                    st.success(f"✅ Datensatz in {table_choice_insert} eingefügt!")
                                    get_db_columns.clear()
                                except Exception as e_insert:
                                    st.error(f"❌ Fehler beim Einfügen: {e_insert}")
                    else:
                        st.info("Bitte eine Tabelle zum Einfügen auswählen.")
            except Exception as e:
                st.error(f"❌ Fehler bei der Tabellenauswahl für das Einfügen: {e}")

        with db_admin_tabs[2]: # Löschen
            st.subheader("Datensatz löschen")
            try:
                tabellen_delete = inspector.get_table_names()
                if not tabellen_delete:
                    st.warning("Keine Tabellen zum Löschen von Daten gefunden.")
                else:
                    table_choice_delete = st.selectbox("Tabelle wählen (Löschen)", tabellen_delete, key="db_delete_table_select")
                    if table_choice_delete:
                        spalten_delete = get_db_columns(table_choice_delete)
                        if not spalten_delete:
                            st.info(f"Keine Spalten für Tabelle {table_choice_delete} gefunden.")
                        else:
                            id_spalte_delete = st.selectbox("Primär-/Identifikationsspalte wählen (z.B. ID)", spalten_delete, key=f"db_delete_id_col_{table_choice_delete}")

                            try:
                                df_delete_preview = pd.read_sql(f"SELECT * FROM {table_choice_delete}", con=engine)
                                if df_delete_preview.empty:
                                    st.info(f"Tabelle {table_choice_delete} ist leer.")
                                elif id_spalte_delete not in df_delete_preview.columns:
                                    st.error(f"Die ausgewählte Spalte {id_spalte_delete} existiert nicht in der Tabelle {table_choice_delete}.")
                                else:
                                    cols_to_show = [id_spalte_delete] + [col for col in df_delete_preview.columns if col != id_spalte_delete][:2]
                                    df_delete_preview["_display_for_delete"] = df_delete_preview[id_spalte_delete].astype(str) + " | " + \
                                                                               df_delete_preview[cols_to_show[1:]].astype(str).agg(" | ".join, axis=1)

                                    selected_row_display = st.selectbox("Zu löschenden Datensatz wählen (basierend auf Primärspalte und Vorschau)",
                                                                        df_delete_preview["_display_for_delete"],
                                                                        key=f"db_delete_row_select_{table_choice_delete}")

                                    actual_id_value_to_delete = selected_row_display.split(" | ")[0]

                                    if st.button("🗑️ Ausgewählten Datensatz löschen", key=f"db_delete_button_{table_choice_delete}"):
                                        try:
                                            with engine.begin() as conn:
                                                query_delete = text(f"DELETE FROM {table_choice_delete} WHERE {id_spalte_delete} = :value")
                                                conn.execute(query_delete, {"value": actual_id_value_to_delete})
                                            st.success(f"✅ Datensatz mit {id_spalte_delete} = {actual_id_value_to_delete} aus {table_choice_delete} gelöscht.")
                                            get_db_columns.clear()
                                        except Exception as e_delete:
                                            st.error(f"❌ Fehler beim Löschen: {e_delete}")
                            except Exception as e_load_del_preview:
                                st.error(f"Fehler beim Laden der Daten für die Löschvorschau: {e_load_del_preview}")
                    else:
                        st.info("Bitte eine Tabelle zum Löschen auswählen.")
            except Exception as e:
                st.error(f"❌ Fehler bei der Tabellenauswahl für das Löschen: {e}")


