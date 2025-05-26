import streamlit as st
import pandas as pd
import altair as alt
import traceback
from datetime import datetime
import time
from database_manager import DatabaseManager

class TicketSystemUI:
    """
    Klasse für die Benutzeroberfläche des Ticketsystems.
    Enthält alle Streamlit-UI-Komponenten und Interaktionslogik.
    """
    
    def __init__(self):
        """
        Initialisiert die Benutzeroberfläche und die Datenbankverbindung.
        """
        # Seitenkonfiguration
        st.set_page_config(
            page_title="Ticketsystem mit Datenbankverwaltung",
            page_icon="🎫",
            layout="wide"
        )
        
        # Datenbankverbindung herstellen
        self.db = DatabaseManager(
            db_user="root",
            db_password="Xyz1343!!!",
            db_host="127.0.0.1",
            db_port="3306",
            db_name="ticketsystemabkoo"
        )
        
        # Sicherstellen, dass die erforderlichen Spalten existieren
        self.db.ensure_required_columns_exist()
        
        # Session-State initialisieren
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False
        
        # Hauptanwendung starten
        self.run()
    
    def run(self):
        """
        Hauptmethode zum Ausführen der Anwendung.
        """
        # Anmeldestatus prüfen
        if not st.session_state.logged_in:
            # Passwort-Wiederherstellung anzeigen, falls angefordert
            if "show_password_reset" in st.session_state and st.session_state.show_password_reset:
                self.show_password_reset_page()
            else:
                # Ansonsten Login-Seite anzeigen
                self.show_login_page()
        else:
            # Passwortänderung anzeigen, falls erforderlich
            if "password_change_required" in st.session_state and st.session_state.password_change_required and not st.session_state.get("password_changed", False):
                self.show_password_change_page()
            else:
                # Hauptanwendung anzeigen
                self.show_main_application()
    
    def show_login_page(self):
        """
        Zeigt die Login-Seite an.
        """
        st.title("🔐 Login")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image("https://img.icons8.com/color/96/000000/password.png", width=100)
        
        with col2:
            st.markdown("### Bitte melden Sie sich an")
            st.markdown("Geben Sie Ihre Zugangsdaten ein, um das Ticketsystem zu nutzen.")
        
        with st.form("login_form"):
            username = st.text_input("Benutzername oder E-Mail")
            password = st.text_input("Passwort", type="password")
            submit = st.form_submit_button("Anmelden")
        
        if submit:
            if not username or not password:
                st.error("Bitte geben Sie Benutzername und Passwort ein.")
            else:
                success, user_id, password_change_required = self.db.authenticate_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.password_change_required = password_change_required
                    
                    # Benutzername für die Anzeige speichern
                    st.session_state.username = self.db.get_user_name(user_id)
                    
                    st.success("Login erfolgreich!")
                    time.sleep(1)  # Kurze Verzögerung, damit die Erfolgsmeldung sichtbar ist
                    st.rerun()
                else:
                    st.error("Ungültiger Benutzername oder Passwort.")
        
        # Link zur Passwort-Wiederherstellung
        st.markdown("---")
        if st.button("Passwort vergessen?"):
            st.session_state.show_password_reset = True
            st.rerun()
    
    def show_password_reset_page(self):
        """
        Zeigt die Passwort-Wiederherstellungsseite an.
        """
        st.title("🔑 Passwort zurücksetzen")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image("https://img.icons8.com/color/96/000000/password-reset.png", width=100)
        
        with col2:
            st.markdown("### Passwort zurücksetzen")
            st.markdown("Geben Sie Ihre E-Mail-Adresse ein, um Ihr Passwort zurückzusetzen.")
        
        with st.form("password_reset_form"):
            email = st.text_input("E-Mail-Adresse")
            submit = st.form_submit_button("Passwort zurücksetzen")
        
        if submit:
            if not email:
                st.error("Bitte geben Sie Ihre E-Mail-Adresse ein.")
            else:
                success, name, temp_password = self.db.reset_password(email)
                if success:
                    st.success("Passwort erfolgreich zurückgesetzt!")
                    st.info(f"""
                    Hallo {name},
                    
                    Ihr temporäres Passwort lautet: **{temp_password}**
                    
                    Bitte melden Sie sich mit diesem Passwort an und ändern Sie es sofort.
                    Das temporäre Passwort ist 24 Stunden gültig.
                    """)
                    
                    # Link zur Login-Seite
                    if st.button("Zurück zur Anmeldung"):
                        st.session_state.show_password_reset = False
                        st.rerun()
                else:
                    st.error("E-Mail-Adresse nicht gefunden.")
        
        # Link zur Login-Seite
        st.markdown("---")
        if st.button("Abbrechen"):
            st.session_state.show_password_reset = False
            st.rerun()
    
    def show_password_change_page(self):
        """
        Zeigt die Passwortänderungsseite an.
        """
        st.title("🔐 Passwort ändern")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.image("https://img.icons8.com/color/96/000000/password.png", width=100)
        
        with col2:
            st.markdown("### Passwort ändern")
            st.markdown("Bitte ändern Sie Ihr temporäres Passwort.")
        
        with st.form("password_change_form"):
            new_password = st.text_input("Neues Passwort", type="password")
            confirm_password = st.text_input("Passwort bestätigen", type="password")
            submit = st.form_submit_button("Passwort ändern")
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Bitte füllen Sie alle Felder aus.")
            elif new_password != confirm_password:
                st.error("Die Passwörter stimmen nicht überein.")
            elif len(new_password) < 8:
                st.error("Das Passwort muss mindestens 8 Zeichen lang sein.")
            else:
                success = self.db.change_password(st.session_state.user_id, new_password)
                if success:
                    st.success("Passwort erfolgreich geändert!")
                    st.session_state.password_changed = True
                    time.sleep(1)  # Kurze Verzögerung, damit die Erfolgsmeldung sichtbar ist
                    st.rerun()
                else:
                    st.error("Fehler beim Ändern des Passworts.")
    
    def show_main_application(self):
        """
        Zeigt die Hauptanwendung an.
        """
        # Seitenleiste mit Benutzerinformationen und Navigation
        with st.sidebar:
            st.write(f"Angemeldet als: **{st.session_state.username}**")
            
            # Abmelden-Button
            if st.button("Abmelden"):
                # Session-State zurücksetzen
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            # Modus wählen
            app_mode = st.radio(
                "Modus wählen:",
                ["Ticketsystem", "Datenbankverwaltung"]
            )
        
        # Hauptinhalt basierend auf dem gewählten Modus
        if app_mode == "Ticketsystem":
            self.show_ticket_system()
        else:  # app_mode == "Datenbankverwaltung"
            self.show_database_management()
    
    def show_ticket_system(self):
        """
        Zeigt das Ticketsystem an.
        """
        st.title("🎫 Ticketsystem")
        
        # Tabs für verschiedene Funktionen
        ticket_tabs = st.tabs(["📋 Ticketübersicht", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"])
        
        # Tab: Ticketübersicht
        with ticket_tabs[0]:
            self.show_ticket_overview()
        
        # Tab: Neues Ticket
        with ticket_tabs[1]:
            self.show_new_ticket_form()
        
        # Tab: Statistiken
        with ticket_tabs[2]:
            self.show_ticket_statistics()
        
        # Tab: Einstellungen
        with ticket_tabs[3]:
            self.show_settings()
    
    def show_ticket_overview(self):
        """
        Zeigt die Ticketübersicht an.
        """
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
            status_options = ["Alle"] + self.db.get_status_options()
            status_filter = st.selectbox("Status", status_options)
        
        with col2:
            priority_options = ["Alle", "Hoch", "Mittel", "Niedrig"]
            priority_filter = st.selectbox("Priorität", priority_options)
        
        with col3:
            mitarbeiter_options = ["Alle"] + self.db.get_mitarbeiter_options()
            mitarbeiter_filter = st.selectbox("Mitarbeiter", mitarbeiter_options)
        
        # SQL-Query mit dynamischen Filtern
        query = """
        SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, 
               s.Name as Status, m.Name as Mitarbeiter, k.Name as Kunde,
               t.Erstellt_am, t.Geändert_am
        FROM tickets t
        LEFT JOIN status s ON t.Status_ID = s.ID_Status
        LEFT JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
        LEFT JOIN kunden k ON t.Kunde_ID = k.ID_Kunde
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
        tickets_df = self.db.execute_query_to_df(query, params)
        
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
                self.show_ticket_details(selected_ticket)
    
    def show_ticket_details(self, ticket_id):
        """
        Zeigt die Details eines Tickets an.
        
        Args:
            ticket_id: ID des Tickets
        """
        # Ticket-Details abrufen
        query = """
        SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, 
               s.Name as Status, m.Name as Mitarbeiter, k.Name as Kunde,
               t.Erstellt_am, t.Geändert_am
        FROM tickets t
        LEFT JOIN status s ON t.Status_ID = s.ID_Status
        LEFT JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
        LEFT JOIN kunden k ON t.Kunde_ID = k.ID_Kunde
        WHERE t.ID_Ticket = :ticket_id
        """
        
        ticket_df = self.db.execute_query_to_df(query, {"ticket_id": ticket_id})
        
        if not ticket_df.empty:
            ticket = ticket_df.iloc[0]
            
            # Ticket-Details anzeigen
            st.subheader(f"Ticket #{ticket['ID_Ticket']}: {ticket['Titel']}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Status:** {ticket['Status']}")
                st.write(f"**Priorität:** {ticket['Priorität']}")
            
            with col2:
                st.write(f"**Mitarbeiter:** {ticket['Mitarbeiter']}")
                st.write(f"**Kunde:** {ticket['Kunde']}")
            
            with col3:
                st.write(f"**Erstellt am:** {ticket['Erstellt_am']}")
                st.write(f"**Geändert am:** {ticket['Geändert_am']}")
            
            st.markdown("---")
            st.write("**Beschreibung:**")
            st.write(ticket['Beschreibung'])
            
            # Kommentare abrufen
            st.markdown("---")
            st.subheader("Kommentare")
            
            comments_query = """
            SELECT k.ID_Kommentar, k.Kommentar, m.Name AS Mitarbeiter, k.Erstellt_am
            FROM kommentare k
            JOIN mitarbeiter m ON k.Mitarbeiter_ID = m.ID_Mitarbeiter
            WHERE k.Ticket_ID = :ticket_id
            ORDER BY k.Erstellt_am DESC
            """
            
            comments_df = self.db.execute_query_to_df(comments_query, {"ticket_id": ticket_id})
            
            if comments_df.empty:
                st.info("Keine Kommentare vorhanden.")
            else:
                for _, comment in comments_df.iterrows():
                    st.markdown(f"""
                    **{comment['Mitarbeiter']}** - {comment['Erstellt_am']}
                    
                    {comment['Kommentar']}
                    
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
                    # Kommentar hinzufügen
                    insert_query = """
                    INSERT INTO kommentare (Ticket_ID, Mitarbeiter_ID, Kommentar, Erstellt_am)
                    VALUES (:ticket_id, :mitarbeiter_id, :kommentar, NOW())
                    """
                    
                    success = self.db.execute_query(insert_query, {
                        "ticket_id": ticket_id,
                        "mitarbeiter_id": st.session_state.user_id,
                        "kommentar": comment_text
                    })
                    
                    if success:
                        st.success("Kommentar erfolgreich hinzugefügt!")
                        st.rerun()
                    else:
                        st.error("Fehler beim Hinzufügen des Kommentars.")
    
    def show_new_ticket_form(self):
        """
        Zeigt das Formular zum Erstellen eines neuen Tickets an.
        """
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
                status_df = self.db.execute_query_to_df(status_query)
                status_options = status_df["Name"].tolist()
                status_ids = status_df["ID_Status"].tolist()
                
                status = st.selectbox("Status", status_options)
            
            with col2:
                # Kunden abrufen
                kunden_query = "SELECT ID_Kunde, Name FROM kunden ORDER BY Name"
                kunden_df = self.db.execute_query_to_df(kunden_query)
                kunden_options = kunden_df["Name"].tolist()
                kunden_ids = kunden_df["ID_Kunde"].tolist()
                
                kunde = st.selectbox("Kunde", kunden_options)
                
                # Mitarbeiter abrufen
                mitarbeiter_query = "SELECT ID_Mitarbeiter, Name FROM mitarbeiter ORDER BY Name"
                mitarbeiter_df = self.db.execute_query_to_df(mitarbeiter_query)
                mitarbeiter_options = mitarbeiter_df["Name"].tolist()
                mitarbeiter_ids = mitarbeiter_df["ID_Mitarbeiter"].tolist()
                
                mitarbeiter = st.selectbox("Mitarbeiter", mitarbeiter_options)
            
            # Submit-Button
            submit = st.form_submit_button("Ticket erstellen")
        
        if submit:
            if not titel or not beschreibung:
                st.error("Bitte füllen Sie alle Pflichtfelder aus.")
            else:
                # IDs ermitteln
                status_id = status_ids[status_options.index(status)]
                kunde_id = kunden_ids[kunden_options.index(kunde)]
                mitarbeiter_id = mitarbeiter_ids[mitarbeiter_options.index(mitarbeiter)]
                
                # Ticket erstellen
                insert_query = """
                INSERT INTO tickets (Titel, Beschreibung, Priorität, Status_ID, Kunde_ID, Mitarbeiter_ID, Erstellt_am, Geändert_am)
                VALUES (:titel, :beschreibung, :prioritaet, :status_id, :kunde_id, :mitarbeiter_id, NOW(), NOW())
                """
                
                try:
                    result = self.db.execute_transaction(insert_query, {
                        "titel": titel,
                        "beschreibung": beschreibung,
                        "prioritaet": prioritaet,
                        "status_id": status_id,
                        "kunde_id": kunde_id,
                        "mitarbeiter_id": mitarbeiter_id
                    })
                    
                    if result:
                        # Ticket-ID abrufen
                        ticket_id = result.lastrowid
                        
                        # Automatische Einträge in ticket_mitarbeiter und ticket_kategorie
                        self.db.create_ticket_relations(ticket_id, mitarbeiter_id)
                        
                        st.success(f"Ticket #{ticket_id} erfolgreich erstellt!")
                    else:
                        st.error("Fehler beim Erstellen des Tickets.")
                except Exception as e:
                    st.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
    
    def show_ticket_statistics(self):
        """
        Zeigt Statistiken zu den Tickets an.
        """
        st.subheader("📊 Ticket-Statistiken")
        
        # Statistiken abrufen
        
        # Tickets nach Status
        status_query = """
        SELECT s.Name AS Status, COUNT(*) AS Anzahl
        FROM tickets t
        JOIN status s ON t.Status_ID = s.ID_Status
        GROUP BY s.Name
        """
        
        status_stats_df = self.db.execute_query_to_df(status_query)
        
        # Tickets nach Priorität
        prioritaet_query = """
        SELECT Priorität, COUNT(*) AS Anzahl
        FROM tickets
        GROUP BY Priorität
        """
        
        prioritaet_stats_df = self.db.execute_query_to_df(prioritaet_query)
        
        # Tickets nach Mitarbeiter
        mitarbeiter_query = """
        SELECT m.Name AS Mitarbeiter, COUNT(*) AS Anzahl
        FROM tickets t
        JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
        GROUP BY m.Name
        """
        
        mitarbeiter_stats_df = self.db.execute_query_to_df(mitarbeiter_query)
        
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
    
    def show_settings(self):
        """
        Zeigt die Einstellungsseite an.
        """
        st.subheader("⚙️ Einstellungen")
        
        # Tabs für verschiedene Einstellungen
        settings_tabs = st.tabs(["👤 Mitarbeiter", "🏢 Kunden", "🏷️ Kategorien", "📋 Status"])
        
        # Tab: Mitarbeiter
        with settings_tabs[0]:
            self.show_mitarbeiter_settings()
        
        # Tab: Kunden
        with settings_tabs[1]:
            self.show_kunden_settings()
        
        # Tab: Kategorien
        with settings_tabs[2]:
            self.show_kategorien_settings()
        
        # Tab: Status
        with settings_tabs[3]:
            self.show_status_settings()
    
    def show_mitarbeiter_settings(self):
        """
        Zeigt die Mitarbeiter-Einstellungen an.
        """
        st.subheader("👤 Mitarbeiter verwalten")
        
        # Mitarbeiter abrufen
        mitarbeiter_query = "SELECT ID_Mitarbeiter, Name, Email FROM mitarbeiter ORDER BY Name"
        mitarbeiter_df = self.db.execute_query_to_df(mitarbeiter_query)
        
        # Mitarbeiter anzeigen
        if not mitarbeiter_df.empty:
            st.dataframe(mitarbeiter_df, use_container_width=True)
        else:
            st.info("Keine Mitarbeiter vorhanden.")
        
        # Neuen Mitarbeiter hinzufügen
        st.subheader("Neuen Mitarbeiter hinzufügen")
        
        with st.form("new_mitarbeiter_form"):
            name = st.text_input("Name")
            email = st.text_input("E-Mail")
            passwort = st.text_input("Passwort", type="password")
            submit = st.form_submit_button("Mitarbeiter hinzufügen")
        
        if submit:
            if not name or not email or not passwort:
                st.error("Bitte füllen Sie alle Felder aus.")
            else:
                # Salt generieren und Passwort hashen
                salt = self.db.generate_salt()
                password_hash = self.db.hash_password(passwort, salt)
                
                # Mitarbeiter hinzufügen
                insert_query = """
                INSERT INTO mitarbeiter (Name, Email, Password_hash, salt, password_change_required)
                VALUES (:name, :email, :password_hash, :salt, 0)
                """
                
                success = self.db.execute_query(insert_query, {
                    "name": name,
                    "email": email,
                    "password_hash": password_hash,
                    "salt": salt
                })
                
                if success:
                    st.success(f"Mitarbeiter {name} erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Mitarbeiters.")
    
    def show_kunden_settings(self):
        """
        Zeigt die Kunden-Einstellungen an.
        """
        st.subheader("🏢 Kunden verwalten")
        
        # Kunden abrufen
        kunden_query = "SELECT ID_Kunde, Name, Email, Telefon FROM kunden ORDER BY Name"
        kunden_df = self.db.execute_query_to_df(kunden_query)
        
        # Kunden anzeigen
        if not kunden_df.empty:
            st.dataframe(kunden_df, use_container_width=True)
        else:
            st.info("Keine Kunden vorhanden.")
        
        # Neuen Kunden hinzufügen
        st.subheader("Neuen Kunden hinzufügen")
        
        with st.form("new_kunde_form"):
            name = st.text_input("Name")
            email = st.text_input("E-Mail")
            telefon = st.text_input("Telefon")
            submit = st.form_submit_button("Kunde hinzufügen")
        
        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen ein.")
            else:
                # Kunde hinzufügen
                insert_query = """
                INSERT INTO kunden (Name, Email, Telefon)
                VALUES (:name, :email, :telefon)
                """
                
                success = self.db.execute_query(insert_query, {
                    "name": name,
                    "email": email,
                    "telefon": telefon
                })
                
                if success:
                    st.success(f"Kunde {name} erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Kunden.")
    
    def show_kategorien_settings(self):
        """
        Zeigt die Kategorien-Einstellungen an.
        """
        st.subheader("🏷️ Kategorien verwalten")
        
        # Kategorien abrufen
        kategorien_query = "SELECT ID_Kategorie, Name, Beschreibung FROM kategorien ORDER BY Name"
        kategorien_df = self.db.execute_query_to_df(kategorien_query)
        
        # Kategorien anzeigen
        if not kategorien_df.empty:
            st.dataframe(kategorien_df, use_container_width=True)
        else:
            st.info("Keine Kategorien vorhanden.")
        
        # Neue Kategorie hinzufügen
        st.subheader("Neue Kategorie hinzufügen")
        
        with st.form("new_kategorie_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")
            submit = st.form_submit_button("Kategorie hinzufügen")
        
        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen ein.")
            else:
                # Kategorie hinzufügen
                insert_query = """
                INSERT INTO kategorien (Name, Beschreibung)
                VALUES (:name, :beschreibung)
                """
                
                success = self.db.execute_query(insert_query, {
                    "name": name,
                    "beschreibung": beschreibung
                })
                
                if success:
                    st.success(f"Kategorie {name} erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen der Kategorie.")
    
    def show_status_settings(self):
        """
        Zeigt die Status-Einstellungen an.
        """
        st.subheader("📋 Status verwalten")
        
        # Status abrufen
        status_query = "SELECT ID_Status, Name, Beschreibung FROM status ORDER BY ID_Status"
        status_df = self.db.execute_query_to_df(status_query)
        
        # Status anzeigen
        if not status_df.empty:
            st.dataframe(status_df, use_container_width=True)
        else:
            st.info("Keine Status vorhanden.")
        
        # Neuen Status hinzufügen
        st.subheader("Neuen Status hinzufügen")
        
        with st.form("new_status_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")
            submit = st.form_submit_button("Status hinzufügen")
        
        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen ein.")
            else:
                # Status hinzufügen
                insert_query = """
                INSERT INTO status (Name, Beschreibung)
                VALUES (:name, :beschreibung)
                """
                
                success = self.db.execute_query(insert_query, {
                    "name": name,
                    "beschreibung": beschreibung
                })
                
                if success:
                    st.success(f"Status {name} erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Status.")
    
    def show_database_management(self):
        """
        Zeigt die Datenbankverwaltung an.
        """
        st.title("🗄️ Datenbankverwaltung")
        
        # Tabellen auswählen
        tabellen = self.db.get_table_names()
        
        selected_table = st.selectbox("Tabelle auswählen", tabellen)
        
        if selected_table:
            # Tabelleninhalt anzeigen
            st.subheader(f"Tabelle: {selected_table}")
            
            # Primärschlüssel ermitteln
            primary_key = self.db.get_primary_key(selected_table)
            
            # Suchfunktion implementieren
            self.show_table_search(selected_table)
            
            # Datensatz bearbeiten
            st.subheader("Datensatz bearbeiten")
            
            # Daten laden - jetzt basierend auf Suchergebnissen, falls vorhanden
            if 'search_results' in st.session_state and st.session_state.search_results is not None:
                data_df = st.session_state.search_results
            else:
                query = f"SELECT * FROM {selected_table}"
                data_df = self.db.execute_query_to_df(query)
            
            if not data_df.empty:
                st.dataframe(data_df, use_container_width=True)
                
                if primary_key and primary_key in data_df.columns:
                    record_id = st.selectbox(
                        f"Datensatz auswählen ({primary_key})",
                        data_df[primary_key].tolist()
                    )
                    
                    if record_id:
                        record = data_df[data_df[primary_key] == record_id].iloc[0]
                        
                        with st.form(f"edit_{selected_table}_form"):
                            edited_values = {}
                            
                            for col in data_df.columns:
                                if col != primary_key:  # Primärschlüssel nicht bearbeiten
                                    edited_values[col] = st.text_input(col, value=str(record[col]) if pd.notna(record[col]) else "")
                            
                            submit = st.form_submit_button("Aktualisieren")
                        
                        if submit:
                            # Leere Werte durch None ersetzen
                            for key, value in edited_values.items():
                                if value == "":
                                    edited_values[key] = None
                            
                            # Update-Query erstellen
                            set_clauses = [f"{col} = :{col}" for col in edited_values.keys()]
                            
                            query = f"UPDATE {selected_table} SET {', '.join(set_clauses)} WHERE {primary_key} = :primary_key"
                            
                            # Parameter für die Query
                            params = {**edited_values, "primary_key": record_id}
                            
                            try:
                                self.db.execute_query(query, params)
                                st.success("Datensatz erfolgreich aktualisiert!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Aktualisieren des Datensatzes: {str(e)}")
            else:
                st.info(f"Keine Daten in der Tabelle {selected_table}.")
            
            # Neuen Datensatz hinzufügen
            st.subheader("Neuen Datensatz hinzufügen")
            
            # Spalten und Typen ermitteln
            columns = self.db.get_columns(selected_table)
            column_types = self.db.get_column_types(selected_table)
            
            with st.form(f"add_{selected_table}_form"):
                new_values = {}
                
                for col in columns:
                    if primary_key and col == primary_key and "auto_increment" in column_types.get(col, "").lower():
                        continue  # Auto-Increment-Primärschlüssel überspringen
                    
                    new_values[col] = st.text_input(f"Neuer Wert für {col}")
                
                submit = st.form_submit_button("Hinzufügen")
            
            if submit:
                # Leere Werte durch None ersetzen
                for key, value in new_values.items():
                    if value == "":
                        new_values[key] = None
                
                # Insert-Query erstellen
                cols = list(new_values.keys())
                placeholders = [f":{col}" for col in cols]
                
                query = f"INSERT INTO {selected_table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                
                try:
                    self.db.execute_query(query, new_values)
                    st.success("Datensatz erfolgreich hinzugefügt!")
                    # Suchergebnisse zurücksetzen, um aktualisierte Daten zu sehen
                    if 'search_results' in st.session_state:
                        st.session_state.search_results = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Hinzufügen des Datensatzes: {str(e)}")
            
            # Datensatz löschen
            st.subheader("Datensatz löschen")
            
            if not data_df.empty and primary_key and primary_key in data_df.columns:
                delete_record_id = st.selectbox(
                    f"Datensatz zum Löschen auswählen ({primary_key})",
                    data_df[primary_key].tolist(),
                    key="delete_record"
                )
                
                if delete_record_id:
                    if st.button("🗑️ Löschen"):
                        try:
                            query = f"DELETE FROM {selected_table} WHERE {primary_key} = :value"
                            self.db.execute_query(query, {"value": delete_record_id})
                            st.success(f"Datensatz mit {primary_key} = {delete_record_id} gelöscht.")
                            # Suchergebnisse zurücksetzen, um aktualisierte Daten zu sehen
                            if 'search_results' in st.session_state:
                                st.session_state.search_results = None
                            st.rerun()
                        except Exception as e:
                            st.error("Fehler beim Löschen:")
                            st.exception(e)
            else:
                st.info(f"Keine Daten in der Tabelle {selected_table} oder kein Primärschlüssel gefunden.")
    
    def show_table_search(self, table_name):
        """
        Zeigt die Suchfunktion für eine Tabelle an.
        
        Args:
            table_name: Name der Tabelle
        """
        st.subheader("🔍 Tabellensuche")
        
        # Durchsuchbare Spalten ermitteln
        searchable_columns = self.db.get_searchable_columns(table_name)
        
        # Suchoptionen
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            search_term = st.text_input("Suchbegriff eingeben", placeholder="Suchbegriff...", key=f"search_term_{table_name}")
        
        with col2:
            # Mehrfachauswahl für Spalten
            selected_columns = st.multiselect(
                "Zu durchsuchende Spalten (leer = alle)",
                options=searchable_columns,
                key=f"search_columns_{table_name}"
            )
        
        with col3:
            # Erweiterte Suchoptionen
            exact_match = st.checkbox("Exakte Übereinstimmung", key=f"exact_match_{table_name}")
            case_sensitive = st.checkbox("Groß-/Kleinschreibung beachten", key=f"case_sensitive_{table_name}")
        
        # Suchbutton
        if st.button("Suchen", key=f"search_button_{table_name}"):
            # Suche durchführen
            results = self.db.search_table(
                table_name=table_name,
                search_term=search_term,
                search_columns=selected_columns if selected_columns else None,
                exact_match=exact_match,
                case_sensitive=case_sensitive
            )
            
            # Ergebnisse in Session speichern
            st.session_state.search_results = results
            
            # Ergebnisse anzeigen
            if results.empty:
                st.warning(f"Keine Ergebnisse für '{search_term}' gefunden.")
            else:
                st.success(f"{len(results)} Ergebnisse gefunden.")
        
        # Button zum Zurücksetzen der Suche
        if 'search_results' in st.session_state and st.session_state.search_results is not None:
            if st.button("Suche zurücksetzen", key=f"reset_search_{table_name}"):
                st.session_state.search_results = None
                st.rerun()
            
            # Anzeige, dass Suchergebnisse aktiv sind
            st.info(f"Es werden Suchergebnisse angezeigt. Anzahl: {len(st.session_state.search_results)}")
        
        # Trennlinie
        st.markdown("---")

# Hauptfunktion zum Starten der Anwendung
if __name__ == "__main__":
    TicketSystemUI()
