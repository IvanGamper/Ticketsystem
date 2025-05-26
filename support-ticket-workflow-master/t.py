import streamlit as st
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text, inspect
import pymysql
import hashlib
import secrets
import datetime
import re
import altair as alt

# Konfiguration
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystemabkoo"

class TicketsystemMitDatenbanksuche:
    """
    Hauptklasse für das Ticketsystem mit integrierter Datenbanksuche.
    Enthält alle Funktionen für Ticketverwaltung, Authentifizierung und Datenbanksuche.
    """

    def __init__(self):
        """
        Initialisiert das Ticketsystem und richtet die Datenbankverbindung ein.
        """
        # Datenbankverbindung einrichten
        self.setup_database_connection()

        # Session-State initialisieren
        self.initialize_session()

        # Seiteneinstellungen
        self.setup_page()

        # Hauptanwendung rendern
        self.render_main_app()

    def setup_database_connection(self):
        """
        Richtet die Datenbankverbindung ein.
        """
        try:
            # Verbindungsstring erstellen
            connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

            # Engine erstellen
            self.engine = create_engine(connection_string)

            # Verbindung testen
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            # Inspector für Metadaten
            self.inspector = inspect(self.engine)

            st.session_state.db_connected = True
        except Exception as e:
            st.error(f"Fehler bei der Datenbankverbindung: {str(e)}")
            st.session_state.db_connected = False

    def initialize_session(self):
        """
        Initialisiert den Session-State.
        """
        # Anmeldestatus
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

        # Benutzer-ID
        if 'user_id' not in st.session_state:
            st.session_state.user_id = None

        # Benutzername
        if 'username' not in st.session_state:
            st.session_state.username = None

        # Passwort-Reset-Ansicht
        if 'show_password_reset' not in st.session_state:
            st.session_state.show_password_reset = False

        # Passwortänderung erforderlich
        if 'password_change_required' not in st.session_state:
            st.session_state.password_change_required = False

        # Datenbankverbindung
        if 'db_connected' not in st.session_state:
            st.session_state.db_connected = False

        # Suchergebnisse
        if 'search_results' not in st.session_state:
            st.session_state.search_results = None

    def setup_page(self):
        """
        Richtet die Seiteneinstellungen ein.
        """
        st.set_page_config(
            page_title="Ticketsystem & Datenbankverwaltung",
            page_icon="🎫",
            layout="wide"
        )

    def render_main_app(self):
        """
        Rendert die Hauptanwendung basierend auf dem aktuellen Zustand.
        """
        # Prüfen, ob der Benutzer angemeldet ist
        if not st.session_state.logged_in:
            # Passwort-Wiederherstellung anzeigen, falls aktiviert
            if st.session_state.show_password_reset:
                self.show_password_reset_page()
            else:
                # Ansonsten Login-Seite anzeigen
                self.show_login_page()
            return

        # Prüfen, ob eine Passwortänderung erforderlich ist
        if st.session_state.password_change_required:
            self.show_password_change_page()
            return

        # Sidebar anzeigen und Modi abrufen
        app_mode, ticket_mode = self.show_sidebar()

        # Hauptinhalt basierend auf ausgewähltem Modus anzeigen
        if app_mode == "Ticketsystem":
            if ticket_mode == "📋 Ticketübersicht":
                self.show_ticket_overview()
            elif ticket_mode == "➕ Neues Ticket":
                self.show_new_ticket_form()
            elif ticket_mode == "📊 Statistiken":
                self.show_statistics()
            elif ticket_mode == "⚙️ Einstellungen":
                self.show_settings()
        else:  # Datenbankverwaltung
            self.show_database_management()

    def show_sidebar(self):
        """
        Zeigt die Sidebar mit Navigation und Benutzerinformationen an.
        """
        with st.sidebar:
            st.title("🎫 Ticketsystem")
            st.header("Navigation")

            app_mode = st.radio(
                "Modus wählen:",
                ["Ticketsystem", "Datenbankverwaltung"]
            )

            if app_mode == "Ticketsystem":
                ticket_mode = st.radio(
                    "Ticketsystem:",
                    ["📋 Ticketübersicht", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"]
                )

            # Angemeldeter Benutzer und Abmelden-Button
            st.markdown("---")
            st.write(f"Angemeldet als: **{st.session_state.username}**")

            # Passwort ändern Button
            if st.button("Passwort ändern"):
                st.session_state.password_change_required = True
                st.rerun()

            # Abmelden-Button
            if st.button("Abmelden"):
                self.logout_user()
                st.rerun()

            return app_mode, ticket_mode if app_mode == "Ticketsystem" else None

    # ===== Authentifizierungsfunktionen =====

    def show_login_page(self):
        """
        Zeigt die Login-Seite an.
        """
        st.title("🔐 Login")

        with st.form("login_form"):
            username = st.text_input("Benutzername oder E-Mail")
            password = st.text_input("Passwort", type="password")
            submit = st.form_submit_button("Anmelden")

        if submit:
            if username and password:
                success, user_id, password_change_required = self.authenticate_user(username, password)

                if success:
                    # Benutzer anmelden
                    self.login_user(user_id, username, password_change_required)
                    st.rerun()
                else:
                    st.error("Ungültige Anmeldedaten. Bitte versuchen Sie es erneut.")
            else:
                st.error("Bitte geben Sie Benutzername und Passwort ein.")

        # Link zur Passwort-Wiederherstellung
        if st.button("Passwort vergessen?"):
            st.session_state.show_password_reset = True
            st.rerun()

    def show_password_reset_page(self):
        """
        Zeigt die Passwort-Reset-Seite an.
        """
        st.title("🔑 Passwort zurücksetzen")

        with st.form("password_reset_form"):
            email = st.text_input("E-Mail-Adresse")
            submit = st.form_submit_button("Passwort zurücksetzen")

        if submit:
            if email:
                success, name, temp_password = self.reset_password(email)

                if success:
                    st.success(f"""
                    Passwort erfolgreich zurückgesetzt für: {name}
                    
                    Ihr temporäres Passwort lautet: **{temp_password}**
                    
                    Bitte melden Sie sich mit diesem Passwort an und ändern Sie es sofort.
                    """)

                    # Zurück zur Login-Seite
                    if st.button("Zurück zum Login"):
                        st.session_state.show_password_reset = False
                        st.rerun()
                else:
                    st.error("E-Mail-Adresse nicht gefunden.")
            else:
                st.error("Bitte geben Sie Ihre E-Mail-Adresse ein.")

        # Zurück zur Login-Seite
        if st.button("Zurück zum Login"):
            st.session_state.show_password_reset = False
            st.rerun()

    def show_password_change_page(self):
        """
        Zeigt die Passwortänderungsseite an.
        """
        st.title("🔐 Passwort ändern")

        with st.form("password_change_form"):
            new_password = st.text_input("Neues Passwort", type="password")
            confirm_password = st.text_input("Passwort bestätigen", type="password")
            submit = st.form_submit_button("Passwort ändern")

        if submit:
            if new_password and confirm_password:
                if new_password == confirm_password:
                    if len(new_password) >= 8:
                        success = self.change_password(st.session_state.user_id, new_password)

                        if success:
                            st.success("Passwort erfolgreich geändert.")
                            st.session_state.password_change_required = False
                            st.rerun()
                        else:
                            st.error("Fehler beim Ändern des Passworts.")
                    else:
                        st.error("Das Passwort muss mindestens 8 Zeichen lang sein.")
                else:
                    st.error("Die Passwörter stimmen nicht überein.")
            else:
                st.error("Bitte geben Sie ein neues Passwort ein und bestätigen Sie es.")

    def authenticate_user(self, username, password):
        """
        Authentifiziert einen Benutzer.

        Args:
            username: Benutzername oder E-Mail
            password: Passwort

        Returns:
            tuple: (success, user_id, password_change_required)
        """
        try:
            # SQL-Query für die Authentifizierung mit korrigierten Spaltennamen
            query = """
            SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required
            FROM mitarbeiter
            WHERE (Name = :username OR Email = :username)
            """

            # Query ausführen
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"username": username})
                user = result.fetchone()

            if user:
                user_id, name, stored_hash, salt, password_change_required = user

                # Passwort überprüfen
                if self.verify_password(password, stored_hash, salt):
                    return True, user_id, password_change_required

            return False, None, False

        except Exception as e:
            st.error(f"Fehler bei der Authentifizierung: {str(e)}")
            return False, None, False

    def login_user(self, user_id, username, password_change_required):
        """
        Meldet einen Benutzer an.

        Args:
            user_id: Benutzer-ID
            username: Benutzername
            password_change_required: Ob eine Passwortänderung erforderlich ist
        """
        st.session_state.logged_in = True
        st.session_state.user_id = user_id
        st.session_state.username = username
        st.session_state.password_change_required = password_change_required

    def logout_user(self):
        """
        Meldet einen Benutzer ab.
        """
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.password_change_required = False
        st.session_state.show_password_reset = False

    def reset_password(self, email):
        """
        Setzt das Passwort eines Benutzers zurück.

        Args:
            email: E-Mail-Adresse des Benutzers

        Returns:
            tuple: (success, name, temp_password)
        """
        try:
            # Benutzer suchen
            query = """
            SELECT ID_Mitarbeiter, Name
            FROM mitarbeiter
            WHERE Email = :email
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"email": email})
                user = result.fetchone()

            if user:
                user_id, name = user

                # Temporäres Passwort generieren
                temp_password = self.generate_temp_password()

                # Salt generieren
                salt = self.generate_salt()

                # Passwort hashen
                hashed_password = self.hash_password(temp_password, salt)

                # Aktuelles Datum für Token-Ablauf (24 Stunden)
                expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)

                # Passwort aktualisieren mit korrigierten Spaltennamen
                update_query = """
                UPDATE mitarbeiter
                SET Password_hash = :password, salt = :salt, password_change_required = 1,
                    reset_token = :token, reset_token_expiry = :expiry
                WHERE ID_Mitarbeiter = :user_id
                """

                with self.engine.connect() as conn:
                    conn.execute(text(update_query), {
                        "password": hashed_password,
                        "salt": salt,
                        "token": secrets.token_hex(16),  # Zufälliger Token
                        "expiry": expiry_date,
                        "user_id": user_id
                    })
                    conn.commit()

                return True, name, temp_password

            return False, None, None

        except Exception as e:
            st.error(f"Fehler beim Zurücksetzen des Passworts: {str(e)}")
            return False, None, None

    def change_password(self, user_id, new_password):
        """
        Ändert das Passwort eines Benutzers.

        Args:
            user_id: Benutzer-ID
            new_password: Neues Passwort

        Returns:
            bool: Erfolg
        """
        try:
            # Salt generieren
            salt = self.generate_salt()

            # Passwort hashen
            hashed_password = self.hash_password(new_password, salt)

            # Passwort aktualisieren mit korrigierten Spaltennamen
            query = """
            UPDATE mitarbeiter
            SET Password_hash = :password, salt = :salt, password_change_required = 0,
                reset_token = NULL, reset_token_expiry = NULL
            WHERE ID_Mitarbeiter = :user_id
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "password": hashed_password,
                    "salt": salt,
                    "user_id": user_id
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Ändern des Passworts: {str(e)}")
            return False

    # ===== Sicherheitsfunktionen =====

    def hash_password(self, password, salt):
        """
        Hasht ein Passwort mit einem Salt.

        Args:
            password: Passwort
            salt: Salt

        Returns:
            str: Gehashtes Passwort
        """
        # Passwort und Salt kombinieren
        salted_password = password + salt

        # Hash erstellen
        hash_obj = hashlib.sha256(salted_password.encode())
        hashed_password = hash_obj.hexdigest()

        return hashed_password

    def verify_password(self, password, stored_hash, salt):
        """
        Überprüft ein Passwort.

        Args:
            password: Passwort
            stored_hash: Gespeicherter Hash
            salt: Salt

        Returns:
            bool: Ob das Passwort korrekt ist
        """
        # Passwort hashen
        hashed_password = self.hash_password(password, salt)

        # Hash vergleichen
        return hashed_password == stored_hash

    def generate_salt(self):
        """
        Generiert einen Salt.

        Returns:
            str: Salt
        """
        return secrets.token_hex(16)

    def generate_temp_password(self):
        """
        Generiert ein temporäres Passwort.

        Returns:
            str: Temporäres Passwort
        """
        # Zufällige Zeichen für das Passwort
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"

        # Passwort generieren
        password = "".join(secrets.choice(chars) for _ in range(12))

        return password

    # ===== Ticketsystem-Funktionen =====

    def show_ticket_overview(self):
        """
        Zeigt die Ticketübersicht an.
        """
        st.header("📋 Ticketübersicht")

        # Suchfunktion
        st.subheader("🔍 Ticket suchen")

        # Suchparameter
        col1, col2 = st.columns(2)

        with col1:
            search_term = st.text_input("Suchbegriff", placeholder="Suchbegriff eingeben...")

        with col2:
            search_field = st.selectbox(
                "Feld durchsuchen",
                ["Alle Felder", "Titel", "Beschreibung", "Kunde", "Mitarbeiter"]
            )

        # Filter
        col1, col2, col3 = st.columns(3)

        with col1:
            status_options = ["Alle"] + self.get_status_options()
            status_filter = st.selectbox("Status", status_options)

        with col2:
            prioritaet_options = ["Alle", "niedrig", "mittel", "hoch"]
            prioritaet_filter = st.selectbox("Priorität", prioritaet_options)

        with col3:
            mitarbeiter_options = ["Alle"] + self.get_mitarbeiter_options()
            mitarbeiter_filter = st.selectbox("Mitarbeiter", mitarbeiter_options)

        # Tickets suchen
        search_params = {
            "search_term": search_term,
            "search_field": search_field,
            "status_filter": status_filter,
            "prioritaet_filter": prioritaet_filter,
            "mitarbeiter_filter": mitarbeiter_filter
        }

        tickets = self.search_tickets(search_params)

        # Tickets anzeigen
        if tickets.empty:
            st.info("Keine Tickets gefunden.")
        else:
            st.subheader(f"Gefundene Tickets: {len(tickets)}")

            # Tickets als Tabelle anzeigen
            st.dataframe(tickets, use_container_width=True)

            # Ticket auswählen
            selected_ticket_id = st.selectbox(
                "Ticket auswählen",
                tickets["ID_Ticket"].tolist(),
                format_func=lambda x: f"Ticket #{x}: {tickets[tickets['ID_Ticket'] == x]['Titel'].iloc[0]}"
            )

            if selected_ticket_id:
                self.show_ticket_details(selected_ticket_id)

    def show_ticket_details(self, ticket_id):
        """
        Zeigt die Details eines Tickets an.

        Args:
            ticket_id: Ticket-ID
        """
        # Ticket-Details abrufen
        ticket_details = self.get_ticket_details(ticket_id)

        if ticket_details:
            st.subheader(f"Ticket #{ticket_id}: {ticket_details['Titel']}")

            # Ticket-Informationen
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Status:** {ticket_details['Status']}")
                st.write(f"**Priorität:** {ticket_details['Priorität']}")

            with col2:
                st.write(f"**Kunde:** {ticket_details['Kunde']}")
                st.write(f"**Mitarbeiter:** {ticket_details['Mitarbeiter']}")

            with col3:
                st.write(f"**Erstellt am:** {ticket_details['Erstellt_am']}")
                st.write(f"**Geändert am:** {ticket_details['Geändert_am']}")

            # Beschreibung
            st.subheader("Beschreibung")
            st.write(ticket_details["Beschreibung"])

            # Kommentare
            st.subheader("Kommentare")

            comments = self.get_ticket_comments(ticket_id)

            if comments.empty:
                st.info("Keine Kommentare vorhanden.")
            else:
                for _, comment in comments.iterrows():
                    with st.expander(f"{comment['Mitarbeiter']} - {comment['Erstellt_am']}"):
                        st.write(comment["Kommentar"])

            # Neuen Kommentar hinzufügen
            st.subheader("Neuen Kommentar hinzufügen")

            with st.form(f"add_comment_form_{ticket_id}"):
                comment_text = st.text_area("Kommentar")
                submit = st.form_submit_button("Kommentar hinzufügen")

            if submit and comment_text:
                success = self.add_comment(ticket_id, st.session_state.user_id, comment_text)

                if success:
                    st.success("Kommentar erfolgreich hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Kommentars.")

    def show_new_ticket_form(self):
        """
        Zeigt das Formular zum Erstellen eines neuen Tickets an.
        """
        st.header("➕ Neues Ticket")

        with st.form("new_ticket_form"):
            # Ticket-Informationen
            titel = st.text_input("Titel")
            beschreibung = st.text_area("Beschreibung")

            col1, col2, col3 = st.columns(3)

            with col1:
                prioritaet = st.selectbox("Priorität", ["niedrig", "mittel", "hoch"])

            with col2:
                status_options = self.get_status_options()
                status_id = st.selectbox("Status", range(len(status_options)), format_func=lambda x: status_options[x])
                status_id += 1  # ID beginnt bei 1

            with col3:
                kunden = self.get_kunden()
                kunde_id = st.selectbox("Kunde", range(len(kunden)), format_func=lambda x: kunden[x]["Name"])
                kunde_id = kunden[kunde_id]["ID_Kunde"]

            # Mitarbeiter ist der angemeldete Benutzer
            mitarbeiter_id = st.session_state.user_id

            submit = st.form_submit_button("Ticket erstellen")

        if submit:
            if titel and beschreibung:
                ticket_id = self.create_ticket(
                    titel=titel,
                    beschreibung=beschreibung,
                    prioritaet=prioritaet,
                    status_id=status_id,
                    kunde_id=kunde_id,
                    mitarbeiter_id=mitarbeiter_id
                )

                if ticket_id:
                    st.success(f"Ticket #{ticket_id} erfolgreich erstellt.")

                    # Zum neuen Ticket navigieren
                    if st.button("Zum neuen Ticket"):
                        st.session_state.selected_ticket_id = ticket_id
                        st.rerun()
                else:
                    st.error("Fehler beim Erstellen des Tickets.")
            else:
                st.error("Bitte geben Sie Titel und Beschreibung ein.")

    def show_statistics(self):
        """
        Zeigt Statistiken zu den Tickets an.
        """
        st.header("📊 Statistiken")

        # Statistiken abrufen
        stats = self.get_ticket_statistics()

        if stats:
            # Tickets nach Status
            st.subheader("Tickets nach Status")

            status_chart = alt.Chart(stats["status_df"]).mark_bar().encode(
                x=alt.X("Status:N", sort="-y"),
                y=alt.Y("Anzahl:Q"),
                color=alt.Color("Status:N", scale=alt.Scale(scheme="category10"))
            ).properties(
                width=600,
                height=400
            )

            st.altair_chart(status_chart, use_container_width=True)

            # Tickets nach Priorität
            st.subheader("Tickets nach Priorität")

            prioritaet_chart = alt.Chart(stats["prioritaet_df"]).mark_bar().encode(
                x=alt.X("Priorität:N", sort=["niedrig", "mittel", "hoch"]),
                y=alt.Y("Anzahl:Q"),
                color=alt.Color("Priorität:N", scale=alt.Scale(scheme="category10"))
            ).properties(
                width=600,
                height=400
            )

            st.altair_chart(prioritaet_chart, use_container_width=True)

            # Tickets nach Mitarbeiter
            st.subheader("Tickets nach Mitarbeiter")

            mitarbeiter_chart = alt.Chart(stats["mitarbeiter_df"]).mark_bar().encode(
                x=alt.X("Mitarbeiter:N", sort="-y"),
                y=alt.Y("Anzahl:Q"),
                color=alt.Color("Mitarbeiter:N", scale=alt.Scale(scheme="category20"))
            ).properties(
                width=600,
                height=400
            )

            st.altair_chart(mitarbeiter_chart, use_container_width=True)
        else:
            st.info("Keine Statistiken verfügbar.")

    def show_settings(self):
        """
        Zeigt die Einstellungsseite an.
        """
        st.header("⚙️ Einstellungen")

        # Tabs für verschiedene Einstellungen
        tab1, tab2, tab3, tab4 = st.tabs(["Mitarbeiter", "Kunden", "Kategorien", "Status"])

        with tab1:
            self.show_mitarbeiter_settings()

        with tab2:
            self.show_kunden_settings()

        with tab3:
            self.show_kategorien_settings()

        with tab4:
            self.show_status_settings()

    def show_mitarbeiter_settings(self):
        """
        Zeigt die Mitarbeitereinstellungen an.
        """
        st.subheader("Mitarbeiter")

        # Mitarbeiter abrufen
        mitarbeiter = self.get_mitarbeiter()

        if not mitarbeiter.empty:
            st.dataframe(mitarbeiter, use_container_width=True)
        else:
            st.info("Keine Mitarbeiter gefunden.")

        # Neuen Mitarbeiter hinzufügen
        st.subheader("Neuen Mitarbeiter hinzufügen")

        with st.form("add_mitarbeiter_form"):
            name = st.text_input("Name")
            email = st.text_input("E-Mail")
            passwort = st.text_input("Passwort", type="password")

            submit = st.form_submit_button("Hinzufügen")

        if submit:
            if name and email and passwort:
                success = self.add_mitarbeiter(name, email, passwort)

                if success:
                    st.success("Mitarbeiter erfolgreich hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Mitarbeiters.")
            else:
                st.error("Bitte füllen Sie alle Felder aus.")

    def show_kunden_settings(self):
        """
        Zeigt die Kundeneinstellungen an.
        """
        st.subheader("Kunden")

        # Kunden abrufen
        kunden_df = pd.DataFrame(self.get_kunden())

        if not kunden_df.empty:
            st.dataframe(kunden_df, use_container_width=True)
        else:
            st.info("Keine Kunden gefunden.")

        # Neuen Kunden hinzufügen
        st.subheader("Neuen Kunden hinzufügen")

        with st.form("add_kunde_form"):
            name = st.text_input("Name")
            email = st.text_input("E-Mail")
            telefon = st.text_input("Telefon")

            submit = st.form_submit_button("Hinzufügen")

        if submit:
            if name:
                success = self.add_kunde(name, email, telefon)

                if success:
                    st.success("Kunde erfolgreich hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Kunden.")
            else:
                st.error("Bitte geben Sie mindestens den Namen ein.")

    def show_kategorien_settings(self):
        """
        Zeigt die Kategorieeinstellungen an.
        """
        st.subheader("Kategorien")

        # Kategorien abrufen
        kategorien = self.get_kategorien()

        if not kategorien.empty:
            st.dataframe(kategorien, use_container_width=True)
        else:
            st.info("Keine Kategorien gefunden.")

        # Neue Kategorie hinzufügen
        st.subheader("Neue Kategorie hinzufügen")

        with st.form("add_kategorie_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")

            submit = st.form_submit_button("Hinzufügen")

        if submit:
            if name:
                success = self.add_kategorie(name, beschreibung)

                if success:
                    st.success("Kategorie erfolgreich hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen der Kategorie.")
            else:
                st.error("Bitte geben Sie mindestens den Namen ein.")

    def show_status_settings(self):
        """
        Zeigt die Statuseinstellungen an.
        """
        st.subheader("Status")

        # Status abrufen
        status = self.get_status()

        if not status.empty:
            st.dataframe(status, use_container_width=True)
        else:
            st.info("Keine Status gefunden.")

        # Neuen Status hinzufügen
        st.subheader("Neuen Status hinzufügen")

        with st.form("add_status_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")

            submit = st.form_submit_button("Hinzufügen")

        if submit:
            if name:
                success = self.add_status(name, beschreibung)

                if success:
                    st.success("Status erfolgreich hinzugefügt.")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Status.")
            else:
                st.error("Bitte geben Sie mindestens den Namen ein.")

    def search_tickets(self, search_params):
        """
        Sucht Tickets basierend auf den angegebenen Parametern.

        Args:
            search_params: Suchparameter

        Returns:
            pandas.DataFrame: Gefundene Tickets
        """
        try:
            # Basis-Query
            query = """
            SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, s.Name AS Status,
                   m.Name AS Mitarbeiter, k.Name AS Kunde, t.Erstellt_am, t.Geändert_am
            FROM tickets t
            JOIN status s ON t.Status_ID = s.ID_Status
            JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
            JOIN kunden k ON t.Kunde_ID = k.ID_Kunde
            WHERE 1=1
            """

            params = {}

            # Suchbegriff
            search_term = search_params.get("search_term", "")
            search_field = search_params.get("search_field", "Alle Felder")

            if search_term:
                if search_field == "Alle Felder":
                    query += """
                    AND (
                        t.Titel LIKE :search_term
                        OR t.Beschreibung LIKE :search_term
                        OR k.Name LIKE :search_term
                        OR m.Name LIKE :search_term
                    )
                    """
                elif search_field == "Titel":
                    query += " AND t.Titel LIKE :search_term"
                elif search_field == "Beschreibung":
                    query += " AND t.Beschreibung LIKE :search_term"
                elif search_field == "Kunde":
                    query += " AND k.Name LIKE :search_term"
                elif search_field == "Mitarbeiter":
                    query += " AND m.Name LIKE :search_term"

                params["search_term"] = f"%{search_term}%"

            # Status-Filter
            status_filter = search_params.get("status_filter", "Alle")

            if status_filter != "Alle":
                query += " AND s.Name = :status"
                params["status"] = status_filter

            # Priorität-Filter
            prioritaet_filter = search_params.get("prioritaet_filter", "Alle")

            if prioritaet_filter != "Alle":
                query += " AND t.Priorität = :prioritaet"
                params["prioritaet"] = prioritaet_filter

            # Mitarbeiter-Filter
            mitarbeiter_filter = search_params.get("mitarbeiter_filter", "Alle")

            if mitarbeiter_filter != "Alle":
                query += " AND m.Name = :mitarbeiter"
                params["mitarbeiter"] = mitarbeiter_filter

            # Sortierung
            query += " ORDER BY t.Erstellt_am DESC"

            # Query ausführen
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                tickets = pd.DataFrame(result.fetchall(), columns=result.keys())

            return tickets

        except Exception as e:
            st.error(f"Fehler bei der Ticket-Suche: {str(e)}")
            return pd.DataFrame()

    def get_ticket_details(self, ticket_id):
        """
        Ruft die Details eines Tickets ab.

        Args:
            ticket_id: Ticket-ID

        Returns:
            dict: Ticket-Details
        """
        try:
            query = """
            SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, s.Name AS Status,
                   m.Name AS Mitarbeiter, k.Name AS Kunde, t.Erstellt_am, t.Geändert_am
            FROM tickets t
            JOIN status s ON t.Status_ID = s.ID_Status
            JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
            JOIN kunden k ON t.Kunde_ID = k.ID_Kunde
            WHERE t.ID_Ticket = :ticket_id
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"ticket_id": ticket_id})
                ticket = result.fetchone()

            if ticket:
                return {
                    "ID_Ticket": ticket[0],
                    "Titel": ticket[1],
                    "Beschreibung": ticket[2],
                    "Priorität": ticket[3],
                    "Status": ticket[4],
                    "Mitarbeiter": ticket[5],
                    "Kunde": ticket[6],
                    "Erstellt_am": ticket[7],
                    "Geändert_am": ticket[8]
                }

            return None

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Ticket-Details: {str(e)}")
            return None

    def get_ticket_comments(self, ticket_id):
        """
        Ruft die Kommentare eines Tickets ab.

        Args:
            ticket_id: Ticket-ID

        Returns:
            pandas.DataFrame: Kommentare
        """
        try:
            query = """
            SELECT k.ID_Kommentar, k.Kommentar, m.Name AS Mitarbeiter, k.Erstellt_am
            FROM kommentare k
            JOIN mitarbeiter m ON k.Mitarbeiter_ID = m.ID_Mitarbeiter
            WHERE k.Ticket_ID = :ticket_id
            ORDER BY k.Erstellt_am DESC
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"ticket_id": ticket_id})
                comments = pd.DataFrame(result.fetchall(), columns=result.keys())

            return comments

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Kommentare: {str(e)}")
            return pd.DataFrame()

    def add_comment(self, ticket_id, mitarbeiter_id, kommentar_text):
        """
        Fügt einen Kommentar zu einem Ticket hinzu.

        Args:
            ticket_id: Ticket-ID
            mitarbeiter_id: Mitarbeiter-ID
            kommentar_text: Kommentartext

        Returns:
            bool: Erfolg
        """
        try:
            query = """
            INSERT INTO kommentare (Ticket_ID, Mitarbeiter_ID, Kommentar, Erstellt_am)
            VALUES (:ticket_id, :mitarbeiter_id, :kommentar, NOW())
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "ticket_id": ticket_id,
                    "mitarbeiter_id": mitarbeiter_id,
                    "kommentar": kommentar_text
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")
            return False

    def create_ticket(self, titel, beschreibung, prioritaet, status_id, kunde_id, mitarbeiter_id):
        """
        Erstellt ein neues Ticket.

        Args:
            titel: Titel
            beschreibung: Beschreibung
            prioritaet: Priorität
            status_id: Status-ID
            kunde_id: Kunden-ID
            mitarbeiter_id: Mitarbeiter-ID

        Returns:
            int: Ticket-ID
        """
        try:
            query = """
            INSERT INTO tickets (Titel, Beschreibung, Priorität, Status_ID, Kunde_ID, Mitarbeiter_ID, Erstellt_am, Geändert_am)
            VALUES (:titel, :beschreibung, :prioritaet, :status_id, :kunde_id, :mitarbeiter_id, NOW(), NOW())
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(query), {
                    "titel": titel,
                    "beschreibung": beschreibung,
                    "prioritaet": prioritaet,
                    "status_id": status_id,
                    "kunde_id": kunde_id,
                    "mitarbeiter_id": mitarbeiter_id
                })
                conn.commit()

                # Ticket-ID abrufen
                ticket_id = result.lastrowid

            return ticket_id

        except Exception as e:
            st.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            return None

    def get_ticket_statistics(self):
        """
        Ruft Statistiken zu den Tickets ab.

        Returns:
            dict: Statistiken
        """
        try:
            # Tickets nach Status
            status_query = """
            SELECT s.Name AS Status, COUNT(*) AS Anzahl
            FROM tickets t
            JOIN status s ON t.Status_ID = s.ID_Status
            GROUP BY s.Name
            """

            # Tickets nach Priorität
            prioritaet_query = """
            SELECT Priorität, COUNT(*) AS Anzahl
            FROM tickets
            GROUP BY Priorität
            """

            # Tickets nach Mitarbeiter
            mitarbeiter_query = """
            SELECT m.Name AS Mitarbeiter, COUNT(*) AS Anzahl
            FROM tickets t
            JOIN mitarbeiter m ON t.Mitarbeiter_ID = m.ID_Mitarbeiter
            GROUP BY m.Name
            """

            with self.engine.connect() as conn:
                status_result = conn.execute(text(status_query))
                status_df = pd.DataFrame(status_result.fetchall(), columns=status_result.keys())

                prioritaet_result = conn.execute(text(prioritaet_query))
                prioritaet_df = pd.DataFrame(prioritaet_result.fetchall(), columns=prioritaet_result.keys())

                mitarbeiter_result = conn.execute(text(mitarbeiter_query))
                mitarbeiter_df = pd.DataFrame(mitarbeiter_result.fetchall(), columns=mitarbeiter_result.keys())

            return {
                "status_df": status_df,
                "prioritaet_df": prioritaet_df,
                "mitarbeiter_df": mitarbeiter_df
            }

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Statistiken: {str(e)}")
            return None

    def get_status_options(self):
        """
        Ruft die verfügbaren Status-Optionen ab.

        Returns:
            list: Status-Optionen
        """
        try:
            query = "SELECT Name FROM status ORDER BY ID_Status"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                status_options = [row[0] for row in result.fetchall()]

            return status_options

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Status-Optionen: {str(e)}")
            return []

    def get_mitarbeiter_options(self):
        """
        Ruft die verfügbaren Mitarbeiter-Optionen ab.

        Returns:
            list: Mitarbeiter-Optionen
        """
        try:
            query = "SELECT Name FROM mitarbeiter ORDER BY Name"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                mitarbeiter_options = [row[0] for row in result.fetchall()]

            return mitarbeiter_options

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Mitarbeiter-Optionen: {str(e)}")
            return []

    def get_mitarbeiter(self):
        """
        Ruft alle Mitarbeiter ab.

        Returns:
            pandas.DataFrame: Mitarbeiter
        """
        try:
            query = "SELECT ID_Mitarbeiter, Name, Email FROM mitarbeiter ORDER BY Name"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                mitarbeiter = pd.DataFrame(result.fetchall(), columns=result.keys())

            return mitarbeiter

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Mitarbeiter: {str(e)}")
            return pd.DataFrame()

    def add_mitarbeiter(self, name, email, passwort):
        """
        Fügt einen neuen Mitarbeiter hinzu.

        Args:
            name: Name
            email: E-Mail
            passwort: Passwort

        Returns:
            bool: Erfolg
        """
        try:
            # Salt generieren
            salt = self.generate_salt()

            # Passwort hashen
            hashed_password = self.hash_password(passwort, salt)

            # Mitarbeiter hinzufügen mit korrigierten Spaltennamen
            query = """
            INSERT INTO mitarbeiter (Name, Email, Password_hash, salt, password_change_required)
            VALUES (:name, :email, :passwort, :salt, 0)
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "name": name,
                    "email": email,
                    "passwort": hashed_password,
                    "salt": salt
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Hinzufügen des Mitarbeiters: {str(e)}")
            return False

    def get_kunden(self):
        """
        Ruft alle Kunden ab.

        Returns:
            list: Kunden
        """
        try:
            query = "SELECT ID_Kunde, Name, Email, Telefon FROM kunden ORDER BY Name"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                kunden = [dict(zip(result.keys(), row)) for row in result.fetchall()]

            return kunden

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Kunden: {str(e)}")
            return []

    def add_kunde(self, name, email, telefon):
        """
        Fügt einen neuen Kunden hinzu.

        Args:
            name: Name
            email: E-Mail
            telefon: Telefon

        Returns:
            bool: Erfolg
        """
        try:
            query = """
            INSERT INTO kunden (Name, Email, Telefon)
            VALUES (:name, :email, :telefon)
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "name": name,
                    "email": email,
                    "telefon": telefon
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Hinzufügen des Kunden: {str(e)}")
            return False

    def get_kategorien(self):
        """
        Ruft alle Kategorien ab.

        Returns:
            pandas.DataFrame: Kategorien
        """
        try:
            query = "SELECT ID_Kategorie, Name, Beschreibung FROM kategorien ORDER BY Name"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                kategorien = pd.DataFrame(result.fetchall(), columns=result.keys())

            return kategorien

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Kategorien: {str(e)}")
            return pd.DataFrame()

    def add_kategorie(self, name, beschreibung):
        """
        Fügt eine neue Kategorie hinzu.

        Args:
            name: Name
            beschreibung: Beschreibung

        Returns:
            bool: Erfolg
        """
        try:
            query = """
            INSERT INTO kategorien (Name, Beschreibung)
            VALUES (:name, :beschreibung)
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "name": name,
                    "beschreibung": beschreibung
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Hinzufügen der Kategorie: {str(e)}")
            return False

    def get_status(self):
        """
        Ruft alle Status ab.

        Returns:
            pandas.DataFrame: Status
        """
        try:
            query = "SELECT ID_Status, Name, Beschreibung FROM status ORDER BY ID_Status"

            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                status = pd.DataFrame(result.fetchall(), columns=result.keys())

            return status

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Status: {str(e)}")
            return pd.DataFrame()

    def add_status(self, name, beschreibung):
        """
        Fügt einen neuen Status hinzu.

        Args:
            name: Name
            beschreibung: Beschreibung

        Returns:
            bool: Erfolg
        """
        try:
            query = """
            INSERT INTO status (Name, Beschreibung)
            VALUES (:name, :beschreibung)
            """

            with self.engine.connect() as conn:
                conn.execute(text(query), {
                    "name": name,
                    "beschreibung": beschreibung
                })
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler beim Hinzufügen des Status: {str(e)}")
            return False

    # ===== Datenbankverwaltung =====

    def show_database_management(self):
        """
        Zeigt die Datenbankverwaltung an.
        """
        st.title("🗄️ Datenbankverwaltung")

        # Tabellen auswählen
        tabellen = self.get_table_names()

        selected_table = st.selectbox("Tabelle auswählen", tabellen)

        if selected_table:
            # Tabelleninhalt anzeigen
            st.subheader(f"Tabelle: {selected_table}")

            # Primärschlüssel ermitteln
            primary_key = self.get_primary_key(selected_table)

            # Suchfunktion implementieren
            self.show_table_search(selected_table)

            # Datensatz bearbeiten
            st.subheader("Datensatz bearbeiten")

            # Daten laden - jetzt basierend auf Suchergebnissen, falls vorhanden
            if 'search_results' in st.session_state and st.session_state.search_results is not None:
                data_df = st.session_state.search_results
            else:
                query = f"SELECT * FROM {selected_table}"
                data_df = self.execute_query_to_df(query)

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
                            # Update-Query erstellen
                            set_clauses = [f"{col} = :{col}" for col in edited_values.keys()]
                            query = f"UPDATE {selected_table} SET {', '.join(set_clauses)} WHERE {primary_key} = :id"

                            params = {**edited_values, "id": record_id}

                            try:
                                self.execute_transaction(query, params)
                                st.success("Datensatz erfolgreich aktualisiert!")
                                # Suchergebnisse zurücksetzen, um aktualisierte Daten zu sehen
                                if 'search_results' in st.session_state:
                                    st.session_state.search_results = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Aktualisieren des Datensatzes: {str(e)}")
            else:
                st.info(f"Keine Daten in der Tabelle {selected_table}.")

            # Neuen Datensatz hinzufügen
            st.subheader("Neuen Datensatz hinzufügen")

            # Spalten und Typen ermitteln
            columns = self.get_columns(selected_table)
            column_types = self.get_column_types(selected_table)

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
                    self.execute_transaction(query, new_values)
                    st.success("Datensatz erfolgreich hinzugefügt!")
                    # Suchergebnisse zurücksetzen, um aktualisierte Daten zu sehen
                    if 'search_results' in st.session_state:
                        st.session_state.search_results = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Hinzufügen des Datensatzes: {str(e)}")

    def show_table_search(self, table_name):
        """
        Zeigt die Suchfunktion für eine Tabelle an.

        Args:
            table_name: Name der Tabelle
        """
        st.subheader("🔍 Tabellensuche")

        # Durchsuchbare Spalten ermitteln
        searchable_columns = self.get_searchable_columns(table_name)

        # Suchoptionen
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            search_term = st.text_input("Suchbegriff eingeben", placeholder="Suchbegriff...")

        with col2:
            # Mehrfachauswahl für Spalten
            selected_columns = st.multiselect(
                "Zu durchsuchende Spalten (leer = alle)",
                options=searchable_columns
            )

        with col3:
            # Erweiterte Suchoptionen
            exact_match = st.checkbox("Exakte Übereinstimmung")
            case_sensitive = st.checkbox("Groß-/Kleinschreibung beachten")

        # Suchbutton
        if st.button("Suchen"):
            # Suche durchführen
            results = self.search_table(
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
            if st.button("Suche zurücksetzen"):
                st.session_state.search_results = None
                st.rerun()

            # Anzeige, dass Suchergebnisse aktiv sind
            st.info(f"Es werden Suchergebnisse angezeigt. Anzahl: {len(st.session_state.search_results)}")

        # Trennlinie
        st.markdown("---")

    def get_searchable_columns(self, table_name):
        """
        Ermittelt die durchsuchbaren Spalten einer Tabelle.

        Args:
            table_name: Name der Tabelle

        Returns:
            list: Liste der Spaltennamen
        """
        try:
            columns = self.get_columns(table_name)
            column_types = self.get_column_types(table_name)

            # Nur Text- und Zahlenspalten sind sinnvoll durchsuchbar
            searchable_columns = []
            for col in columns:
                col_type = column_types.get(col, "").lower()
                if any(text_type in col_type for text_type in ["char", "text", "varchar"]) or \
                        any(num_type in col_type for num_type in ["int", "decimal", "float", "double"]):
                    searchable_columns.append(col)

            return searchable_columns
        except Exception as e:
            st.error(f"Fehler beim Ermitteln der durchsuchbaren Spalten: {str(e)}")
            return []

    def search_table(self, table_name, search_term, search_columns=None, exact_match=False, case_sensitive=False):
        """
        Durchsucht eine Tabelle nach einem Suchbegriff.

        Args:
            table_name: Name der Tabelle
            search_term: Suchbegriff
            search_columns: Liste der zu durchsuchenden Spalten (optional, wenn None werden alle durchsuchbaren Spalten verwendet)
            exact_match: Ob exakte Übereinstimmung gefordert ist (optional, Standard: False)
            case_sensitive: Ob Groß-/Kleinschreibung beachtet werden soll (optional, Standard: False)

        Returns:
            pandas.DataFrame: Gefundene Datensätze
        """
        try:
            if not search_term:
                # Bei leerem Suchbegriff alle Datensätze zurückgeben
                query = f"SELECT * FROM {table_name}"
                return self.execute_query_to_df(query)

            # Wenn keine Spalten angegeben sind, alle durchsuchbaren Spalten verwenden
            if search_columns is None or len(search_columns) == 0:
                search_columns = self.get_searchable_columns(table_name)

            # Wenn keine durchsuchbaren Spalten gefunden wurden, leeren DataFrame zurückgeben
            if not search_columns:
                return pd.DataFrame()

            # SQL-Bedingungen für die Suche erstellen
            conditions = []
            params = {}

            for i, col in enumerate(search_columns):
                param_name = f"search_term_{i}"

                if exact_match:
                    # Exakte Übereinstimmung
                    if case_sensitive:
                        conditions.append(f"{col} = :{param_name}")
                    else:
                        conditions.append(f"LOWER({col}) = :{param_name}")
                        search_term = search_term.lower()
                else:
                    # Teilweise Übereinstimmung (LIKE)
                    if case_sensitive:
                        conditions.append(f"{col} LIKE :{param_name}")
                        params[param_name] = f"%{search_term}%"
                    else:
                        conditions.append(f"LOWER({col}) LIKE :{param_name}")
                        params[param_name] = f"%{search_term.lower()}%"

                params[param_name] = f"%{search_term}%" if not exact_match else search_term

            # SQL-Query erstellen
            query = f"SELECT * FROM {table_name} WHERE {' OR '.join(conditions)}"

            # Query ausführen und Ergebnisse zurückgeben
            return self.execute_query_to_df(query, params)

        except Exception as e:
            st.error(f"Fehler bei der Tabellensuche: {str(e)}")
            return pd.DataFrame()

    # ===== Datenbankfunktionen =====

    def execute_query_to_df(self, query, params=None):
        """
        Führt eine SQL-Abfrage aus und gibt das Ergebnis als DataFrame zurück.

        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage (optional)

        Returns:
            pandas.DataFrame: Ergebnis
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params or {})
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

            return df

        except Exception as e:
            st.error(f"Fehler bei der Datenbankabfrage: {str(e)}")
            return pd.DataFrame()

    def execute_transaction(self, query, params=None):
        """
        Führt eine SQL-Abfrage in einer Transaktion aus.

        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage (optional)

        Returns:
            bool: Erfolg
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text(query), params or {})
                conn.commit()

            return True

        except Exception as e:
            st.error(f"Fehler bei der Datenbanktransaktion: {str(e)}")
            return False

    def get_table_names(self):
        """
        Ruft die Namen aller Tabellen in der Datenbank ab.

        Returns:
            list: Tabellennamen
        """
        try:
            return self.inspector.get_table_names()

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Tabellennamen: {str(e)}")
            return []

    def get_columns(self, table_name):
        """
        Ruft die Spalten einer Tabelle ab.

        Args:
            table_name: Name der Tabelle

        Returns:
            list: Spaltennamen
        """
        try:
            columns = self.inspector.get_columns(table_name)
            return [col["name"] for col in columns]

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Spalten: {str(e)}")
            return []

    def get_column_types(self, table_name):
        """
        Ruft die Typen der Spalten einer Tabelle ab.

        Args:
            table_name: Name der Tabelle

        Returns:
            dict: Spaltentypen
        """
        try:
            columns = self.inspector.get_columns(table_name)
            return {col["name"]: str(col["type"]) for col in columns}

        except Exception as e:
            st.error(f"Fehler beim Abrufen der Spaltentypen: {str(e)}")
            return {}

    def get_primary_key(self, table_name):
        """
        Ruft den Primärschlüssel einer Tabelle ab.

        Args:
            table_name: Name der Tabelle

        Returns:
            str: Primärschlüssel
        """
        try:
            pk = self.inspector.get_pk_constraint(table_name)
            if pk and "constrained_columns" in pk and pk["constrained_columns"]:
                return pk["constrained_columns"][0]
            return None

        except Exception as e:
            st.error(f"Fehler beim Abrufen des Primärschlüssels: {str(e)}")
            return None

# Anwendung starten
if __name__ == "__main__":
    TicketsystemMitDatenbanksuche()
