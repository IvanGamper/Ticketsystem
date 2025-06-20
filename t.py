import altair as alt
import streamlit as st
import pandas as pd
from sqlalchemy import text
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from a import (generate_salt, hash_password)

# Ticketsystem anzeigen
def show_ticket_system():

    from d import engine
    st.title("🎫 Ticketsystem")

    # Tabs für verschiedene Funktionen
    ticket_tabs = st.tabs(["📋 Ticketübersicht", "✏️ Ticket bearbeiten", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen", "📧 EMAIL"])

    # Tab: Ticketübersicht
    with ticket_tabs[0]:
        show_ticket_overview()

    # Tab: Ticket bearbeiten (NEU)
    with ticket_tabs[1]:
        show_ticket_edit_tab()

    # Tab: Neues Ticket
    with ticket_tabs[2]:
        show_new_ticket_form()

    # Tab: Statistiken
    with ticket_tabs[3]:
        show_ticket_statistics()

    # Tab: Einstellungen
    with ticket_tabs[4]:
        show_settings()

    # Tab: EMAIL
    with ticket_tabs[5]:
        show_email_tab()

# Ticketübersicht anzeigen
def show_ticket_overview():
    from d import engine
    st.subheader("📋 Ticketübersicht")

    # Suchfunktion
    st.subheader("🔍 Ticket suchen")
    search_col1, search_col2 = st.columns([3, 1])

    with search_col1:
        search_term = st.text_input("Suchbegriff eingeben (Titel, Beschreibung, Kunde, Mitarbeiter)", placeholder="z.B. Server, Netzwerk, Max Mustermann...")

    with search_col2:
        search_field = st.selectbox(
            "Suchfeld",
            ["Alle Felder", "Titel", "Beschreibung", "Kunde", "Mitarbeiter"]
        )

    # Filter-Optionen
    st.subheader("Filter")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Status-Optionen abrufen
        status_query = "SELECT Name FROM status ORDER BY Name"
        status_df = pd.read_sql(status_query, con=engine)
        status_options = ["Alle"] + status_df["Name"].tolist()
        status_filter = st.selectbox("Status", status_options)

    with col2:
        priority_options = ["Alle", "Hoch", "Mittel", "Niedrig"]
        priority_filter = st.selectbox("Priorität", priority_options)

    with col3:
        # Mitarbeiter-Optionen abrufen
        mitarbeiter_query = "SELECT Name FROM mitarbeiter ORDER BY Name"
        mitarbeiter_df = pd.read_sql(mitarbeiter_query, con=engine)
        mitarbeiter_options = ["Alle"] + mitarbeiter_df["Name"].tolist()
        mitarbeiter_filter = st.selectbox("Mitarbeiter", mitarbeiter_options)

    # SQL-Query mit dynamischen Filtern
    query = """
    SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, 
           s.Name as Status, m.Name as Mitarbeiter, k.Name as Kunde,
           t.Erstellt_am, t.Geändert_am
    FROM ticket t
    LEFT JOIN status s ON t.ID_Status = s.ID_Status
    LEFT JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
    LEFT JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
    WHERE 1=1
    """

    params = {}

    # Filter anwenden
    if status_filter != "Alle":
        query += " AND s.Name = :status"
        params["status"] = status_filter

    if priority_filter != "Alle":
        query += " AND t.Priorität = :priority"
        params["priority"] = priority_filter

    if mitarbeiter_filter != "Alle":
        query += " AND m.Name = :mitarbeiter"
        params["mitarbeiter"] = mitarbeiter_filter

    # Suchbegriff anwenden
    if search_term:
        if search_field == "Alle Felder":
            query += """ AND (
                t.Titel LIKE :search_term OR 
                t.Beschreibung LIKE :search_term OR 
                k.Name LIKE :search_term OR 
                m.Name LIKE :search_term
            )"""
            params["search_term"] = f"%{search_term}%"
        elif search_field == "Titel":
            query += " AND t.Titel LIKE :search_term"
            params["search_term"] = f"%{search_term}%"
        elif search_field == "Beschreibung":
            query += " AND t.Beschreibung LIKE :search_term"
            params["search_term"] = f"%{search_term}%"
        elif search_field == "Kunde":
            query += " AND k.Name LIKE :search_term"
            params["search_term"] = f"%{search_term}%"
        elif search_field == "Mitarbeiter":
            query += " AND m.Name LIKE :search_term"
            params["search_term"] = f"%{search_term}%"

    # Sortierung
    query += " ORDER BY t.Erstellt_am DESC"

    # Tickets abrufen
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            tickets_df = pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Tickets: {str(e)}")
        tickets_df = pd.DataFrame()

    # Anzeige der Tickets
    st.write(f"**{len(tickets_df)} Tickets gefunden**")

    if tickets_df.empty:
        if search_term:
            st.warning(f"Keine Tickets gefunden, die den Suchkriterien '{search_term}' entsprechen.")
        else:
            st.info("Keine Tickets gefunden, die den Filterkriterien entsprechen.")
    else:
        # Ticket-Tabelle anzeigen
        st.dataframe(tickets_df, use_container_width=True)

        # Ticket-Details anzeigen
        if "selected_ticket_id" not in st.session_state:
            st.session_state.selected_ticket_id = None

        # Ticket auswählen
        selected_ticket = st.selectbox(
            "Ticket auswählen",
            tickets_df["ID_Ticket"].tolist(),
            format_func=lambda x: f"#{x} - {tickets_df[tickets_df['ID_Ticket'] == x]['Titel'].iloc[0]}"
        )

        if selected_ticket:
            st.session_state.selected_ticket_id = selected_ticket
            show_ticket_details(selected_ticket)

# Ticket-Details anzeigen
def show_ticket_details(ticket_id):
    from d import engine
    # Ticket-Details abrufen
    query = """
    SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, 
           s.Name as Status, m.Name as Mitarbeiter, k.Name as Kunde,
           t.Erstellt_am, t.Geändert_am
    FROM ticket t
    LEFT JOIN status s ON t.ID_Status = s.ID_Status
    LEFT JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
    LEFT JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
    WHERE t.ID_Ticket = :ticket_id
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"ticket_id": ticket_id})
            ticket = result.fetchone()
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Ticket-Details: {str(e)}")
        return

    if ticket:
        # Ticket-Details anzeigen
        st.subheader(f"Ticket #{ticket.ID_Ticket}: {ticket.Titel}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"**Status:** {ticket.Status}")
            st.write(f"**Priorität:** {ticket.Priorität}")

        with col2:
            st.write(f"**Mitarbeiter:** {ticket.Mitarbeiter}")
            st.write(f"**Kunde:** {ticket.Kunde}")

        with col3:
            st.write(f"**Erstellt am:** {ticket.Erstellt_am}")
            st.write(f"**Geändert am:** {ticket.Geändert_am}")

        st.markdown("---")
        st.write("**Beschreibung:**")
        st.write(ticket.Beschreibung)

        # Kommentare abrufen
        st.markdown("---")
        st.subheader("Kommentare")

        kommentar_query = """
        SELECT k.ID_Kommentar, k.Kommentar_Text AS Kommentar, m.Name as Mitarbeiter, k.Erstellt_am
        FROM ticket_kommentar k
        JOIN mitarbeiter m ON k.ID_Mitarbeiter = m.ID_Mitarbeiter
        WHERE k.ID_Ticket = :ID_Ticket
        ORDER BY k.Erstellt_am DESC
        """

        try:
            with engine.connect() as conn:
                result = conn.execute(text(kommentar_query), {"ID_Ticket": ticket_id})
                kommentare = result.fetchall()
        except Exception as e:
            st.error(f"Fehler beim Abrufen der Kommentare: {str(e)}")
            kommentare = []

        if not kommentare:
            st.info("Keine Kommentare vorhanden.")
        else:
            for kommentar in kommentare:
                st.markdown(f"""
                **{kommentar.Mitarbeiter}** - {kommentar.Erstellt_am}
                
                {kommentar.Kommentar}
                
                ---
                """)

        # Neuen Kommentar hinzufügen
        st.subheader("Neuer Kommentar")

        with st.form(f"new_comment_form_{ticket_id}"):
            comment_text = st.text_area("Kommentar")
            submit_comment = st.form_submit_button("Kommentar hinzufügen")

        if submit_comment:
            if not comment_text:
                st.error("Bitte geben Sie einen Kommentar ein.")
            else:
                try:
                    with engine.begin() as conn:
                        insert_query = text("""
                        INSERT INTO ticket_kommentar (ID_Ticket, ID_Mitarbeiter, Kommentar_Text, Erstellt_am)
                        VALUES (:ID_Ticket, :ID_Mitarbeiter, :Kommentar_Text, NOW())
                        """)
                        conn.execute(insert_query, {
                            "ID_Ticket": ticket_id,
                            "ID_Mitarbeiter": st.session_state.user_id,
                            "Kommentar_Text": comment_text
                        })

                    st.success("Kommentar erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")

        # --- Ticket-Historie anzeigen ---
        st.markdown("---")
        st.subheader("🕘 Änderungshistorie")

        try:
            historie_query = """
            SELECT th.Feldname, th.Alter_Wert, th.Neuer_Wert, m.Name AS Geändert_von, th.Geändert_am
            FROM ticket_historie th
            LEFT JOIN mitarbeiter m ON th.Geändert_von = m.ID_Mitarbeiter
            WHERE th.ID_Ticket = :ticket_id
            ORDER BY th.Geändert_am DESC
            """
            with engine.connect() as conn:
                result = conn.execute(text(historie_query), {"ticket_id": ticket_id})
                history_entries = result.fetchall()
        except Exception as e:
            st.error(f"Fehler beim Abrufen der Historie: {str(e)}")
            history_entries = []

        if not history_entries:
            st.info("Keine Änderungen protokolliert.")
        else:
            for eintrag in history_entries:
                st.markdown(f"""
                🔹 **{eintrag.Feldname}** geändert von **{eintrag.Alter_Wert}** zu **{eintrag.Neuer_Wert}**  
                🧑‍💼 Durch: *{eintrag.Geändert_von}* am *{eintrag.Geändert_am}*
                """)

# Ticket-Bearbeitungstab anzeigen (NEU)
def show_ticket_edit_tab():
    from d import engine
    st.subheader("✏️ Ticket bearbeiten")

    # Alle Tickets laden für die Auswahl
    try:
        query = text("""
            SELECT t.ID_Ticket, t.Titel, s.Name as Status
            FROM ticket t
            LEFT JOIN status s ON t.ID_Status = s.ID_Status
            ORDER BY t.ID_Ticket DESC
        """)
        with engine.connect() as conn:
            result = conn.execute(query)
            tickets_df = pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Fehler beim Laden der Tickets: {str(e)}")
        return

    if tickets_df.empty:
        st.info("Keine Tickets gefunden.")
        return

    # Ticket-Auswahl
    col1, col2 = st.columns([3, 1])

    with col1:
        ticket_options = [f"#{row['ID_Ticket']} - {row['Titel']} ({row['Status']})" for _, row in tickets_df.iterrows()]
        selected_ticket_option = st.selectbox("Ticket auswählen:", options=ticket_options)

        # Ticket-ID aus der Auswahl extrahieren
        selected_ticket_id = int(selected_ticket_option.split("#")[1].split(" - ")[0])

    with col2:
        search_term = st.text_input("Ticket-ID suchen:", "")
        if search_term and search_term.isdigit():
            search_id = int(search_term)
            if search_id in tickets_df["ID_Ticket"].values:
                selected_ticket_id = search_id
                st.success(f"Ticket #{search_id} gefunden!")
            else:
                st.error(f"Ticket #{search_id} nicht gefunden!")

    # Tabs für Bearbeitung, Historie und Kommentare
    tab1, tab2, tab3 = st.tabs(["📝 Bearbeiten", "📜 Historie", "💬 Kommentare"])

    # Tab 1: Ticket bearbeiten
    with tab1:
        # Ticket-Daten laden
        try:
            query = text("""
                SELECT t.*, s.Name as Status_Name
                FROM ticket t
                LEFT JOIN status s ON t.ID_Status = s.ID_Status
                WHERE t.ID_Ticket = :ticket_id
            """)
            with engine.connect() as conn:
                result = conn.execute(query, {"ticket_id": selected_ticket_id})
                ticket_data = result.fetchone()

                if not ticket_data:
                    st.error(f"Ticket #{selected_ticket_id} konnte nicht geladen werden.")
                    return

                # Ticket-Daten in ein Dictionary umwandeln
                ticket_dict = {column: value for column, value in zip(result.keys(), ticket_data)}
        except Exception as e:
            st.error(f"Fehler beim Laden des Tickets: {str(e)}")
            return

        # Status-Optionen laden
        status_df = pd.read_sql("SELECT ID_Status, Name FROM status ORDER BY Name", con=engine)

        # Mitarbeiter-Optionen laden
        mitarbeiter_df = pd.read_sql("SELECT ID_Mitarbeiter, Name FROM mitarbeiter ORDER BY Name", con=engine)

        # Kunden-Optionen laden
        kunden_df = pd.read_sql("SELECT ID_Kunde, Name FROM kunde ORDER BY Name", con=engine)

        # Kategorien laden
        kategorien_df = pd.read_sql("SELECT ID_Kategorie, Name FROM kategorie ORDER BY Name", con=engine)

        # Aktuelle Kategorie ermitteln
        try:
            query = text("""
                SELECT k.ID_Kategorie, k.Name
                FROM ticket_kategorie tk
                JOIN kategorie k ON tk.ID_Kategorie = k.ID_Kategorie
                WHERE tk.ID_Ticket = :ticket_id
                LIMIT 1
            """)
            with engine.connect() as conn:
                result = conn.execute(query, {"ticket_id": selected_ticket_id})
                kategorie_data = result.fetchone()

                if kategorie_data:
                    current_kategorie_id = kategorie_data[0]
                    current_kategorie_name = kategorie_data[1]
                else:
                    current_kategorie_id = None
                    current_kategorie_name = None
        except Exception as e:
            st.error(f"Fehler beim Laden der Kategorie: {str(e)}")
            current_kategorie_id = None
            current_kategorie_name = None

        # Bearbeitungsformular
        with st.form(f"edit_ticket_form_{selected_ticket_id}"):
            st.subheader(f"Ticket #{selected_ticket_id} bearbeiten")

            titel = st.text_input("Titel:", value=ticket_dict.get("Titel", ""))
            beschreibung = st.text_area("Beschreibung:", value=ticket_dict.get("Beschreibung", ""), height=150)

            col1, col2 = st.columns(2)

            with col1:
                # Status-Dropdown
                status_index = 0
                for i, row in status_df.iterrows():
                    if row["ID_Status"] == ticket_dict.get("ID_Status"):
                        status_index = i
                        break

                selected_status = st.selectbox(
                    "Status:",
                    options=status_df.to_dict('records'),
                    index=status_index,
                    format_func=lambda x: x["Name"]
                )

                # Priorität-Dropdown
                prioritaet_options = ["Niedrig", "Mittel", "Hoch", "Kritisch"]
                prioritaet_index = prioritaet_options.index(ticket_dict.get("Priorität", "Mittel")) if ticket_dict.get("Priorität") in prioritaet_options else 1
                prioritaet = st.selectbox("Priorität:", options=prioritaet_options, index=prioritaet_index)

            with col2:
                # Mitarbeiter-Dropdown
                mitarbeiter_index = 0
                for i, row in mitarbeiter_df.iterrows():
                    if row["ID_Mitarbeiter"] == ticket_dict.get("ID_Mitarbeiter"):
                        mitarbeiter_index = i
                        break

                selected_mitarbeiter = st.selectbox(
                    "Zugewiesener Mitarbeiter:",
                    options=mitarbeiter_df.to_dict('records'),
                    index=mitarbeiter_index,
                    format_func=lambda x: x["Name"]
                )

                # Kunde-Dropdown
                kunde_index = 0
                for i, row in kunden_df.iterrows():
                    if row["ID_Kunde"] == ticket_dict.get("ID_Kunde"):
                        kunde_index = i
                        break

                selected_kunde = st.selectbox(
                    "Kunde:",
                    options=kunden_df.to_dict('records'),
                    index=kunde_index,
                    format_func=lambda x: x["Name"]
                )

            # Kategorie-Dropdown
            kategorie_index = 0
            if current_kategorie_id:
                for i, row in kategorien_df.iterrows():
                    if row["ID_Kategorie"] == current_kategorie_id:
                        kategorie_index = i
                        break

            selected_kategorie = st.selectbox(
                "Kategorie:",
                options=kategorien_df.to_dict('records'),
                index=kategorie_index,
                format_func=lambda x: x["Name"]
            )

            # Speichern-Button
            submit_button = st.form_submit_button("Änderungen speichern")

            if submit_button:
                try:
                    # Änderungen sammeln und vergleichen
                    changes = []

                    # Funktion zum Überprüfen von Änderungen
                    def check_change(field_name, old_value, new_value, display_name=None):
                        if old_value != new_value:
                            display = display_name if display_name else field_name
                            changes.append({
                                "field": field_name,
                                "old": str(old_value) if old_value is not None else "",
                                "new": str(new_value) if new_value is not None else "",
                                "display": display
                            })

                    # Änderungen überprüfen
                    check_change("Titel", ticket_dict.get("Titel"), titel)
                    check_change("Beschreibung", ticket_dict.get("Beschreibung"), beschreibung)
                    check_change("Priorität", ticket_dict.get("Priorität"), prioritaet)
                    check_change("ID_Status", ticket_dict.get("ID_Status"), selected_status["ID_Status"], "Status")
                    check_change("ID_Mitarbeiter", ticket_dict.get("ID_Mitarbeiter"), selected_mitarbeiter["ID_Mitarbeiter"], "Mitarbeiter")
                    check_change("ID_Kunde", ticket_dict.get("ID_Kunde"), selected_kunde["ID_Kunde"], "Kunde")

                    # Kategorie-Änderung überprüfen
                    if current_kategorie_id != selected_kategorie["ID_Kategorie"]:
                        changes.append({
                            "field": "Kategorie",
                            "old": current_kategorie_name if current_kategorie_name else "",
                            "new": selected_kategorie["Name"],
                            "display": "Kategorie"
                        })

                    if changes:
                        # Ticket aktualisieren
                        update_query = text("""
                            UPDATE ticket
                            SET Titel = :titel,
                                Beschreibung = :beschreibung,
                                Priorität = :prioritaet,
                                ID_Status = :status,
                                ID_Mitarbeiter = :mitarbeiter,
                                ID_Kunde = :kunde,
                                Geändert_am = NOW()
                            WHERE ID_Ticket = :ticket_id
                        """)

                        with engine.connect() as conn:
                            with conn.begin():
                                conn.execute(update_query, {
                                    "titel": titel,
                                    "beschreibung": beschreibung,
                                    "prioritaet": prioritaet,
                                    "status": selected_status["ID_Status"],
                                    "mitarbeiter": selected_mitarbeiter["ID_Mitarbeiter"],
                                    "kunde": selected_kunde["ID_Kunde"],
                                    "ticket_id": selected_ticket_id
                                })

                            # Kategorie aktualisieren
                            if current_kategorie_id != selected_kategorie["ID_Kategorie"]:
                                # Bestehende Kategorie-Zuordnung löschen
                                delete_query = text("""
                                    DELETE FROM ticket_kategorie WHERE ID_Ticket = :ticket_id
                                """)
                                conn.execute(delete_query, {"ticket_id": selected_ticket_id})

                                # Neue Kategorie-Zuordnung erstellen
                                insert_query = text("""
                                    INSERT INTO ticket_kategorie (ID_Ticket, ID_Kategorie)
                                    VALUES (:ticket_id, :kategorie_id)
                                """)
                                conn.execute(insert_query, {
                                    "ticket_id": selected_ticket_id,
                                    "kategorie_id": selected_kategorie["ID_Kategorie"]
                                })

                            # Änderungen in der Historie protokollieren
                            for change in changes:
                                log_ticket_change(
                                    selected_ticket_id,
                                    change["display"],
                                    change["old"],
                                    change["new"],
                                    st.session_state.user_id
                                )

                        st.success("Ticket erfolgreich aktualisiert!")
                        st.rerun()
                    else:
                        st.info("Keine Änderungen erkannt.")
                except Exception as e:
                    st.error(f"Fehler beim Aktualisieren des Tickets: {str(e)}")

    # Tab 2: Ticket-Historie
    with tab2:
        st.subheader(f"Historie für Ticket #{selected_ticket_id}")

        # Filter-Optionen für die Historie
        with st.expander("Filter-Optionen"):
            col1, col2, col3 = st.columns(3)

            with col1:
                filter_field = st.text_input("Nach Feld filtern:", "")

            with col2:
                filter_date_from = st.date_input("Von Datum:", value=None)

            with col3:
                filter_date_to = st.date_input("Bis Datum:", value=None)

        # Historie laden
        try:
            query = text("""
                SELECT th.ID_Historie, th.Feldname, th.Alter_Wert, th.Neuer_Wert, 
                       th.Geändert_am, m.Name as Mitarbeiter_Name
                FROM ticket_historie th
                LEFT JOIN mitarbeiter m ON th.Geändert_von = m.ID_Mitarbeiter
                WHERE th.ID_Ticket = :ticket_id
                ORDER BY th.Geändert_am DESC
            """)
            with engine.connect() as conn:
                result = conn.execute(query, {"ticket_id": selected_ticket_id})
                history_df = pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            st.error(f"Fehler beim Laden der Ticket-Historie: {str(e)}")
            history_df = pd.DataFrame()

        if history_df.empty:
            st.info("Keine Historieneinträge für dieses Ticket gefunden.")
        else:
            # Filter anwenden
            filtered_df = history_df.copy()

            if filter_field:
                filtered_df = filtered_df[filtered_df["Feldname"].str.contains(filter_field, case=False)]

            if filter_date_from:
                filtered_df = filtered_df[filtered_df["Geändert_am"].dt.date >= filter_date_from]

            if filter_date_to:
                filtered_df = filtered_df[filtered_df["Geändert_am"].dt.date <= filter_date_to]

            # Formatierte Anzeige der Historie
            for _, row in filtered_df.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 3])

                    with col1:
                        st.write(f"**{row['Geändert_am'].strftime('%d.%m.%Y %H:%M')}**")
                        st.write(f"*{row['Mitarbeiter_Name']}*")

                    with col2:
                        st.write(f"**Feld:** {row['Feldname']}")

                        # Spezielle Formatierung für bestimmte Feldtypen
                        if row['Feldname'] == 'Kommentar':
                            st.write(f"**Neuer Kommentar:** {row['Neuer_Wert']}")
                        else:
                            st.write(f"**Alt:** {row['Alter_Wert']}")
                            st.write(f"**Neu:** {row['Neuer_Wert']}")

                    st.divider()

    # Tab 3: Kommentare
    with tab3:
        st.subheader(f"Kommentare für Ticket #{selected_ticket_id}")

        # Formular für neue Kommentare
        with st.form("new_comment_form"):
            new_comment = st.text_area("Neuer Kommentar:", height=100)
            submit_comment = st.form_submit_button("Kommentar hinzufügen")

            if submit_comment:
                if not new_comment.strip():
                    st.error("Kommentar darf nicht leer sein")
                else:
                    try:
                        # Kommentar in die Datenbank einfügen
                        insert_query = text("""
                            INSERT INTO ticket_kommentar (ID_Ticket, Kommentar_Text, Erstellt_von, Erstellt_am)
                            VALUES (:ticket_id, :comment_text, :mitarbeiter_id, NOW())
                        """)

                        with engine.begin() as conn:
                            conn.execute(insert_query, {
                                "ticket_id": selected_ticket_id,
                                "comment_text": new_comment,
                                "mitarbeiter_id": st.session_state.user_id
                            })

                        # Kommentar auch in Historie loggen
                        log_ticket_change(selected_ticket_id, "Kommentar", "", new_comment, st.session_state.user_id)

                        st.success("Kommentar erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")

        # Bestehende Kommentare anzeigen
        try:
            query = text("""
                SELECT tk.ID_Kommentar, tk.Kommentar_Text, tk.Erstellt_am, 
                       m.Name as Mitarbeiter_Name
                FROM ticket_kommentar tk
                LEFT JOIN mitarbeiter m ON tk.Erstellt_von = m.ID_Mitarbeiter
                WHERE tk.ID_Ticket = :ticket_id
                ORDER BY tk.Erstellt_am DESC
            """)
            with engine.connect() as conn:
                result = conn.execute(query, {"ticket_id": selected_ticket_id})
                comments_df = pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            st.error(f"Fehler beim Laden der Ticket-Kommentare: {str(e)}")
            comments_df = pd.DataFrame()

        if comments_df.empty:
            st.info("Keine Kommentare für dieses Ticket gefunden.")
        else:
            for _, row in comments_df.iterrows():
                with st.container():
                    st.markdown(f"""
                    **{row['Mitarbeiter_Name']}** - {row['Erstellt_am'].strftime('%d.%m.%Y %H:%M')}
                    
                    {row['Kommentar_Text']}
                    """)
                    st.divider()
# Neues Ticket-Formular anzeigen
def show_new_ticket_form():
    from d import engine
    st.subheader("➕ Neues Ticket erstellen")

    # Formular zum Erstellen eines neuen Tickets
    with st.form("new_ticket_form"):
        # Titel und Beschreibung
        titel = st.text_input("Titel")
        beschreibung = st.text_area("Beschreibung")

        # Priorität, Status, Kunde und Mitarbeiter
        col1, col2 = st.columns(2)

        with col1:
            prioritaet = st.selectbox("Priorität", ["Hoch", "Mittel", "Niedrig"])

            # Status abrufen
            status_query = "SELECT ID_Status, Name FROM status ORDER BY ID_Status"
            status_df = pd.read_sql(status_query, con=engine)
            status_options = status_df["Name"].tolist()
            ID_Statuss = status_df["ID_Status"].tolist()

            status = st.selectbox("Status", status_options)

        with col2:
            # Kunden abrufen
            kunden_query = "SELECT ID_Kunde, Name FROM kunde ORDER BY Name"
            kunden_df = pd.read_sql(kunden_query, con=engine)
            kunden_options = kunden_df["Name"].tolist()
            kunden_ids = kunden_df["ID_Kunde"].tolist()

            kunde = st.selectbox("Kunde", kunden_options)

            # Mitarbeiter abrufen
            mitarbeiter_query = "SELECT ID_Mitarbeiter, Name FROM mitarbeiter ORDER BY Name"
            mitarbeiter_df = pd.read_sql(mitarbeiter_query, con=engine)
            mitarbeiter_options = mitarbeiter_df["Name"].tolist()
            ID_Mitarbeiters = mitarbeiter_df["ID_Mitarbeiter"].tolist()

            mitarbeiter = st.selectbox("Mitarbeiter", mitarbeiter_options)

        # Submit-Button
        submit = st.form_submit_button("Ticket erstellen")

    if submit:
        if not titel or not beschreibung:
            st.error("Bitte füllen Sie alle Pflichtfelder aus.")
        else:
            # IDs ermitteln
            ID_Status = ID_Statuss[status_options.index(status)]
            ID_Kunde = kunden_ids[kunden_options.index(kunde)]
            ID_Mitarbeiter = ID_Mitarbeiters[mitarbeiter_options.index(mitarbeiter)]

            # Ticket erstellen
            try:
                with engine.begin() as conn:
                    insert_query = text("""
                    INSERT INTO ticket (Titel, Beschreibung, Priorität, ID_Status, ID_Kunde, ID_Mitarbeiter, Erstellt_am, Geändert_am)
                    VALUES (:titel, :beschreibung, :prioritaet, :ID_Status, :ID_Kunde, :ID_Mitarbeiter, NOW(), NOW())
                    """)
                    result = conn.execute(insert_query, {
                        "titel": titel,
                        "beschreibung": beschreibung,
                        "prioritaet": prioritaet,
                        "ID_Status": ID_Status,
                        "ID_Kunde": ID_Kunde,
                        "ID_Mitarbeiter": ID_Mitarbeiter
                    })

                    # Ticket-ID abrufen
                    ticket_id = result.lastrowid

                    # Automatische Einträge in ticket_mitarbeiter und ticket_kategorie
                    create_ticket_relations(ticket_id, ID_Mitarbeiter)

                st.success(f"Ticket #{ticket_id} erfolgreich erstellt!")
            except Exception as e:
                st.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
# Hilfsfunktion: Automatische Einträge in ticket_mitarbeiter und ticket_kategorie
def create_ticket_relations(ticket_id, ID_Mitarbeiter, kategorie_id=1):
    from d import engine
    try:
        with engine.begin() as conn:
            # Eintrag in ticket_mitarbeiter
            if ID_Mitarbeiter:
                # Prüfen, ob der Eintrag bereits existiert
                check_query = text("SELECT COUNT(*) FROM ticket_mitarbeiter WHERE ID_Ticket = :ticket_id AND ID_Mitarbeiter = :ID_Mitarbeiter")
                result = conn.execute(check_query, {"ticket_id": ticket_id, "ID_Mitarbeiter": ID_Mitarbeiter}).scalar()

                if result == 0:  # Eintrag existiert noch nicht
                    insert_query = text("INSERT INTO ticket_mitarbeiter (ID_Ticket, ID_Mitarbeiter, Rolle_im_Ticket) VALUES (:ticket_id, :ID_Mitarbeiter, 'Hauptverantwortlicher')")
                    conn.execute(insert_query, {"ticket_id": ticket_id, "ID_Mitarbeiter": ID_Mitarbeiter})

            # Eintrag in ticket_kategorie
            if kategorie_id:
                # Prüfen, ob die Kategorie existiert
                check_kategorie = text("SELECT COUNT(*) FROM kategorie WHERE ID_Kategorie = :kategorie_id")
                kategorie_exists = conn.execute(check_kategorie, {"kategorie_id": kategorie_id}).scalar()

                if kategorie_exists > 0:
                    # Prüfen, ob der Eintrag bereits existiert
                    check_query = text("SELECT COUNT(*) FROM ticket_kategorie WHERE ID_Ticket = :ticket_id AND ID_Kategorie = :kategorie_id")
                    result = conn.execute(check_query, {"ticket_id": ticket_id, "kategorie_id": kategorie_id}).scalar()

                    if result == 0:  # Eintrag existiert noch nicht
                        insert_query = text("INSERT INTO ticket_kategorie (ID_Ticket, ID_Kategorie) VALUES (:ticket_id, :kategorie_id)")
                        conn.execute(insert_query, {"ticket_id": ticket_id, "kategorie_id": kategorie_id})

        return True
    except Exception as e:
        st.error(f"Fehler beim Erstellen der Ticket-Beziehungen: {str(e)}")
        return False

# Ticket-Statistiken anzeigen
def show_ticket_statistics():
    from d import engine
    st.subheader("📊 Ticket-Statistiken")

    # Statistiken abrufen
    try:
        # Tickets nach Status
        status_query = """
        SELECT s.Name AS Status, COUNT(*) AS Anzahl
        FROM ticket t
        JOIN status s ON t.ID_Status = s.ID_Status
        GROUP BY s.Name
        """
        status_stats_df = pd.read_sql(status_query, con=engine)

        # Tickets nach Priorität
        prioritaet_query = """
        SELECT Priorität, COUNT(*) AS Anzahl
        FROM ticket
        GROUP BY Priorität
        """
        prioritaet_stats_df = pd.read_sql(prioritaet_query, con=engine)

        # Tickets nach Mitarbeiter
        mitarbeiter_query = """
        SELECT m.Name AS Mitarbeiter, COUNT(*) AS Anzahl
        FROM ticket t
        JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
        GROUP BY m.Name
        """
        mitarbeiter_stats_df = pd.read_sql(mitarbeiter_query, con=engine)

        # Statistiken anzeigen
        if not status_stats_df.empty and not prioritaet_stats_df.empty and not mitarbeiter_stats_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Tickets nach Status")

                # Altair-Diagramm für Status
                status_chart = alt.Chart(status_stats_df).mark_bar().encode(
                    x=alt.X('Status:N', sort='-y'),
                    y='Anzahl:Q',
                    color='Status:N'
                ).properties(
                    width=400,
                    height=300
                )

                st.altair_chart(status_chart, use_container_width=True)

                st.subheader("Tickets nach Mitarbeiter")

                # Altair-Diagramm für Mitarbeiter
                mitarbeiter_chart = alt.Chart(mitarbeiter_stats_df).mark_bar().encode(
                    x=alt.X('Mitarbeiter:N', sort='-y'),
                    y='Anzahl:Q',
                    color='Mitarbeiter:N'
                ).properties(
                    width=400,
                    height=300
                )

                st.altair_chart(mitarbeiter_chart, use_container_width=True)

            with col2:
                st.subheader("Tickets nach Priorität")

                # Altair-Diagramm für Priorität
                prioritaet_chart = alt.Chart(prioritaet_stats_df).mark_bar().encode(
                    x=alt.X('Priorität:N', sort='-y'),
                    y='Anzahl:Q',
                    color='Priorität:N'
                ).properties(
                    width=400,
                    height=300
                )

                st.altair_chart(prioritaet_chart, use_container_width=True)
        else:
            st.info("Keine Statistiken verfügbar. Erstellen Sie zuerst einige Tickets.")
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Statistiken: {str(e)}")

# Einstellungen anzeigen
def show_settings():
    from d import engine
    st.subheader("⚙️ Einstellungen")

    # Tabs für verschiedene Einstellungen
    settings_tabs = st.tabs(["👤 Mitarbeiter", "🏢 Kunden", "🏷️ Kategorien", "📋 Status"])

    # Tab: Mitarbeiter
    with settings_tabs[0]:
        st.subheader("Mitarbeiter verwalten")

        # Mitarbeiter anzeigen
        mitarbeiter_df = pd.read_sql("SELECT ID_Mitarbeiter, Name, Email FROM mitarbeiter ORDER BY Name", con=engine)
        st.dataframe(mitarbeiter_df, use_container_width=True)

        # Neuen Mitarbeiter hinzufügen
        with st.expander("Neuen Mitarbeiter hinzufügen"):
            with st.form(key="add_mitarbeiter_form"):
                name = st.text_input("Name")
                email = st.text_input("E-Mail")
                passwort = st.text_input("Passwort", type="password")

                submit_mitarbeiter = st.form_submit_button("Mitarbeiter hinzufügen")

            if submit_mitarbeiter:
                if not name or not email or not passwort:
                    st.error("Bitte füllen Sie alle Felder aus.")
                else:
                    try:
                        # Salt generieren und Passwort hashen
                        salt = generate_salt()
                        password_hash = hash_password(passwort, salt)

                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO mitarbeiter (Name, Email, Password_hash, salt, password_change_required)
                            VALUES (:name, :email, :password_hash, :salt, FALSE)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "email": email,
                                "password_hash": password_hash,
                                "salt": salt
                            })

                        st.success(f"Mitarbeiter '{name}' erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Mitarbeiters: {str(e)}")

    # Tab: Kunden
    with settings_tabs[1]:
        st.subheader("Kunden verwalten")

        # Kunden anzeigen
        kunden_df = pd.read_sql("SELECT ID_Kunde, Name, Kontaktperson, Email, Telefon FROM kunde ORDER BY Name", con=engine)
        st.dataframe(kunden_df, use_container_width=True)

        # Neuen Kunden hinzufügen
        with st.expander("Neuen Kunden hinzufügen"):
            with st.form(key="add_kunde_form"):
                name = st.text_input("Name")
                Kontaktperson = st.text_input("Kontaktperson")
                email = st.text_input("E-Mail")
                telefon = st.text_input("Telefon")

                submit_kunde = st.form_submit_button("Kunden hinzufügen")

            if submit_kunde:
                if not name:
                    st.error("Bitte geben Sie mindestens den Namen des Kunden ein.")
                else:
                    try:
                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO kunde (Name, Kontaktperson, Email, Telefon)
                            VALUES (:name, :Kontaktperson, :email, :telefon)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "Kontaktperson": Kontaktperson,
                                "email": email,
                                "telefon": telefon
                            })

                        st.success(f"Kunde '{name}' erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Kunden: {str(e)}")

    # Tab: Kategorien
    with settings_tabs[2]:
        st.subheader("Kategorien verwalten")

        # Kategorien anzeigen
        kategorien_df = pd.read_sql("SELECT ID_Kategorie, Name, Beschreibung FROM kategorie ORDER BY Name", con=engine)
        st.dataframe(kategorien_df, use_container_width=True)

        # Neue Kategorie hinzufügen
        with st.expander("Neue Kategorie hinzufügen"):
            with st.form(key="add_kategorie_form"):
                name = st.text_input("Name")
                beschreibung = st.text_area("Beschreibung")

                submit_kategorie = st.form_submit_button("Kategorie hinzufügen")

            if submit_kategorie:
                if not name:
                    st.error("Bitte geben Sie mindestens den Namen der Kategorie ein.")
                else:
                    try:
                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO kategorie (Name, Beschreibung)
                            VALUES (:name, :beschreibung)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "beschreibung": beschreibung
                            })

                        st.success(f"Kategorie '{name}' erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen der Kategorie: {str(e)}")

    # Tab: Status
    with settings_tabs[3]:
        st.subheader("Status verwalten")

        # Status anzeigen
        status_df = pd.read_sql("SELECT ID_Status, Name, Beschreibung FROM status ORDER BY ID_Status", con=engine)
        st.dataframe(status_df, use_container_width=True)

        # Neuen Status hinzufügen
        with st.expander("Neuen Status hinzufügen"):
            with st.form(key="add_status_form"):
                name = st.text_input("Name")
                beschreibung = st.text_area("Beschreibung")

                submit_status = st.form_submit_button("Status hinzufügen")

            if submit_status:
                if not name:
                    st.error("Bitte geben Sie mindestens den Namen des Status ein.")
                else:
                    try:
                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO status (Name, Beschreibung)
                            VALUES (:name, :beschreibung)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "beschreibung": beschreibung
                            })

                        st.success(f"Status '{name}' erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Status: {str(e)}")

# E-Mail-Funktionen
def send_email(smtp_server, smtp_port, email, app_password, to_email, subject, body, use_ssl=True):
    """
    Sendet eine E-Mail über SMTP
    """
    try:
        # E-Mail-Nachricht erstellen
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Text zur E-Mail hinzufügen
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # SMTP-Verbindung aufbauen
        if use_ssl:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # TLS aktivieren
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)

        # Anmelden
        server.login(email, app_password)

        # E-Mail senden
        text = msg.as_string()
        server.sendmail(email, to_email, text)
        server.quit()

        return True, "E-Mail erfolgreich gesendet!"

    except Exception as e:
        return False, f"Fehler beim Senden der E-Mail: {str(e)}"

def show_email_tab():
    from d import engine
    """
    Zeigt das EMAIL-Tab mit E-Mail-Versendungsfunktionalität an
    """
    st.subheader("📧 E-Mail versenden")

    # E-Mail-Konfiguration
    st.markdown("### E-Mail-Konfiguration")

    col1, col2 = st.columns(2)

    with col1:
        smtp_server = st.text_input("SMTP-Server", value="smtp.gmail.com", help="z.B. smtp.gmail.com für Gmail")
        smtp_port = st.number_input("SMTP-Port", value=587, min_value=1, max_value=65535, help="587 für TLS, 465 für SSL")
        use_ssl = st.checkbox("TLS verwenden", value=True, help="Für Gmail sollte TLS aktiviert sein")

    with col2:
        sender_email = st.text_input("Absender E-Mail", help="Ihre E-Mail-Adresse")
        app_password = st.text_input("App-Passwort", type="password", help="App-spezifisches Passwort (nicht Ihr normales Passwort)")

    st.markdown("---")

    # E-Mail-Inhalt
    st.markdown("### E-Mail-Inhalt")

    # Ticket-Auswahl für E-Mail-Kontext
    try:
        ticket_query = """
        SELECT t.ID_Ticket, t.Titel, k.Name as Kunde, k.Email as Kunde_Email
        FROM ticket t
        LEFT JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
        ORDER BY t.ID_Ticket DESC
        """
        with engine.connect() as conn:
            result = conn.execute(text(ticket_query))
            tickets_df = pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Fehler beim Laden der Tickets: {str(e)}")
        tickets_df = pd.DataFrame()

    # Ticket-Auswahl
    if not tickets_df.empty:
        st.markdown("#### Ticket-bezogene E-Mail (optional)")

        ticket_options = ["Keine Ticket-Auswahl"] + [f"#{row['ID_Ticket']} - {row['Titel']} ({row['Kunde']})" for _, row in tickets_df.iterrows()]
        selected_ticket_option = st.selectbox("Ticket auswählen (optional):", options=ticket_options)

        selected_ticket_data = None
        if selected_ticket_option != "Keine Ticket-Auswahl":
            ticket_id = int(selected_ticket_option.split("#")[1].split(" - ")[0])
            selected_ticket_data = tickets_df[tickets_df['ID_Ticket'] == ticket_id].iloc[0]

    # E-Mail-Formular
    col1, col2 = st.columns(2)

    with col1:
        # Empfänger vorausfüllen, wenn Ticket ausgewählt
        default_recipient = ""
        if 'selected_ticket_data' in locals() and selected_ticket_data is not None and selected_ticket_data['Kunde_Email']:
            default_recipient = selected_ticket_data['Kunde_Email']

        recipient_email = st.text_input("Empfänger E-Mail", value=default_recipient)

    with col2:
        # Betreff vorausfüllen, wenn Ticket ausgewählt
        default_subject = ""
        if 'selected_ticket_data' in locals() and selected_ticket_data is not None:
            default_subject = f"Ticket #{selected_ticket_data['ID_Ticket']}: {selected_ticket_data['Titel']}"

        email_subject = st.text_input("Betreff", value=default_subject)

    # E-Mail-Text
    default_body = ""
    if 'selected_ticket_data' in locals() and selected_ticket_data is not None:
        default_body = f"""Sehr geehrte Damen und Herren,

bezugnehmend auf Ihr Ticket #{selected_ticket_data['ID_Ticket']} "{selected_ticket_data['Titel']}" möchten wir Sie über den aktuellen Status informieren.

[Hier können Sie Ihre Nachricht eingeben]

Mit freundlichen Grüßen
Ihr Support-Team"""

    email_body = st.text_area("E-Mail-Text", value=default_body, height=200)

    # Vorschau
    if st.checkbox("E-Mail-Vorschau anzeigen"):
        st.markdown("### Vorschau")
        st.markdown(f"**Von:** {sender_email}")
        st.markdown(f"**An:** {recipient_email}")
        st.markdown(f"**Betreff:** {email_subject}")
        st.markdown("**Nachricht:**")
        st.text(email_body)

    st.markdown("---")

    # Senden-Button
    if st.button("📧 E-Mail senden", type="primary"):
        # Validierung
        if not sender_email:
            st.error("Bitte geben Sie eine Absender-E-Mail-Adresse ein.")
        elif not app_password:
            st.error("Bitte geben Sie ein App-Passwort ein.")
        elif not recipient_email:
            st.error("Bitte geben Sie eine Empfänger-E-Mail-Adresse ein.")
        elif not email_subject:
            st.error("Bitte geben Sie einen Betreff ein.")
        elif not email_body:
            st.error("Bitte geben Sie einen E-Mail-Text ein.")
        else:
            # E-Mail senden
            with st.spinner("E-Mail wird gesendet..."):
                success, message = send_email(
                    smtp_server=smtp_server,
                    smtp_port=smtp_port,
                    email=sender_email,
                    app_password=app_password,
                    to_email=recipient_email,
                    subject=email_subject,
                    body=email_body,
                    use_ssl=use_ssl
                )

            if success:
                st.success(message)

                # E-Mail-Versendung in Ticket-Historie protokollieren (falls Ticket ausgewählt)
                if 'selected_ticket_data' in locals() and selected_ticket_data is not None:
                    try:
                        log_ticket_change(
                            selected_ticket_data['ID_Ticket'],
                            "E-Mail gesendet",
                            "",
                            f"E-Mail an {recipient_email} mit Betreff '{email_subject}' gesendet",
                            st.session_state.user_id
                        )
                        st.info("E-Mail-Versendung wurde in der Ticket-Historie protokolliert.")
                    except Exception as e:
                        st.warning(f"E-Mail wurde gesendet, aber Protokollierung in Ticket-Historie fehlgeschlagen: {str(e)}")

            else:
                st.error(message)

    # Hilfe-Bereich
    with st.expander("ℹ️ Hilfe zur E-Mail-Konfiguration"):
        st.markdown("""
        ### Gmail-Konfiguration:
        - **SMTP-Server:** smtp.gmail.com
        - **Port:** 587 (mit TLS)
        - **App-Passwort:** Sie benötigen ein App-spezifisches Passwort, nicht Ihr normales Gmail-Passwort
        
        ### App-Passwort erstellen (Gmail):
        1. Gehen Sie zu Ihrem Google-Konto
        2. Wählen Sie "Sicherheit"
        3. Aktivieren Sie die 2-Faktor-Authentifizierung (falls noch nicht aktiviert)
        4. Wählen Sie "App-Passwörter"
        5. Erstellen Sie ein neues App-Passwort für "Mail"
        6. Verwenden Sie dieses 16-stellige Passwort hier
        
        ### Andere E-Mail-Anbieter:
        - **Outlook/Hotmail:** smtp-mail.outlook.com, Port 587
        - **Yahoo:** smtp.mail.yahoo.com, Port 587
        - Konsultieren Sie die Dokumentation Ihres E-Mail-Anbieters für spezifische Einstellungen
        """)

# Diese Funktion fügt einen Lösch-Button zum Ticket-Details-Bereich hinzu
def add_ticket_delete_button(ticket_id):

    from d import engine

    """
    Fügt einen Lösch-Button für ein Ticket hinzu und implementiert die Löschlogik.

    Args:
        ticket_id: Die ID des zu löschenden Tickets
    """
    # Lösch-Button mit Warnfarbe
    col1, col2 = st.columns([3, 1])
    with col2:
        delete_button = st.button("🗑️ Ticket löschen", type="primary", use_container_width=True, key=f"delete_ticket_{ticket_id}")

    # Wenn der Lösch-Button geklickt wurde
    if delete_button:
        # Bestätigungsdialog anzeigen
        st.warning(f"Sind Sie sicher, dass Sie Ticket #{ticket_id} löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden!")

        col1, col2 = st.columns([1, 1])
        with col1:
            confirm_delete = st.button("✅ Ja, Ticket löschen", type="primary", key=f"confirm_delete_{ticket_id}")
        with col2:
            cancel_delete = st.button("❌ Nein, abbrechen", key=f"cancel_delete_{ticket_id}")

        if confirm_delete:
            try:
                # Ticket löschen - die abhängigen Datensätze werden durch ON DELETE CASCADE automatisch gelöscht
                with engine.begin() as conn:
                    delete_query = text("""
                        DELETE FROM ticket 
                        WHERE ID_Ticket = :ticket_id
                    """)
                    result = conn.execute(delete_query, {"ticket_id": ticket_id})

                    if result.rowcount > 0:
                        st.success(f"✅ Ticket #{ticket_id} wurde erfolgreich gelöscht!")

                        # Session-State zurücksetzen
                        if "selected_ticket_id" in st.session_state and st.session_state.selected_ticket_id == ticket_id:
                            st.session_state.selected_ticket_id = None

                        # Kurze Verzögerung für bessere Benutzererfahrung
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Ticket #{ticket_id} konnte nicht gelöscht werden.")

            except Exception as e:
                st.error(f"❌ Fehler beim Löschen des Tickets: {str(e)}")

                # Detaillierte Fehlermeldung für Fremdschlüssel-Probleme
                error_str = str(e)
                if "foreign key constraint fails" in error_str.lower():
                    st.error("""
                    **Fremdschlüssel-Constraint-Fehler erkannt!**
                    
                    Das Ticket kann nicht gelöscht werden, da es noch von anderen Tabellen referenziert wird.
                    Bitte stellen Sie sicher, dass die ON DELETE CASCADE-Optionen in der Datenbank korrekt konfiguriert sind.
                    """)

        elif cancel_delete:
            st.info("Löschvorgang abgebrochen.")

# Hilfsfunktion: Spaltennamen einer Tabelle
def get_columns(table):

    from d import engine, inspector

    try:
        return [col["name"] for col in inspector.get_columns(table)]
    except:
        return []

#Hilfsfunktion Historie
def log_ticket_change(ticket_id, feldname, alter_wert, neuer_wert, mitarbeiter_id):

    from d import engine

    # Typkonvertierung für den Vergleich
    alter_wert_str = str(alter_wert) if alter_wert is not None else ""
    neuer_wert_str = str(neuer_wert) if neuer_wert is not None else ""

    # Nur speichern, wenn sich die Werte tatsächlich unterscheiden
    if alter_wert_str.strip() == neuer_wert_str.strip():
        return  # Nur Änderungen speichern

    # Kürzere Transaktion mit Wiederholungslogik
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            insert_query = text("""
                INSERT INTO ticket_historie (ID_Ticket, Feldname, Alter_Wert, Neuer_Wert, Geändert_von, Geändert_am)
                VALUES (:ticket_id, :feldname, :alter_wert, :neuer_wert, :geändert_von, NOW())
            """)

            with engine.begin() as conn:
                conn.execute(insert_query, {
                    "ticket_id": ticket_id,
                    "feldname": feldname,
                    "alter_wert": alter_wert_str,
                    "neuer_wert": neuer_wert_str,
                    "geändert_von": mitarbeiter_id
                })

            # Wenn erfolgreich, Schleife beenden
            return True

        except Exception as e:
            # Nur bei Lock-Timeout-Fehlern wiederholen
            if "Lock wait timeout exceeded" in str(e) and retry_count < max_retries - 1:
                retry_count += 1
                time.sleep(0.5)  # Kurze Pause vor dem nächsten Versuch
            else:
                # Bei anderen Fehlern oder zu vielen Versuchen, Fehler protokollieren
                print(f"FEHLER: Historien-Eintrag konnte nicht gespeichert werden: {str(e)}")
                # Fehler weitergeben
                raise
