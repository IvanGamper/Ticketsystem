import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timedelta
import traceback
import altair as alt
import hashlib
import secrets
import time
import string
import random

# DB-Konfiguration
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystemabkoo"

# SQLAlchemy Engine
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

inspector = inspect(engine)

# Hilfsfunktion: Spaltennamen einer Tabelle
def get_columns(table):
    try:
        return [col["name"] for col in inspector.get_columns(table)]
    except:
        return []

# Hilfsfunktion: Primärschlüssel einer Tabelle ermitteln
def get_primary_key(table):
    try:
        pk = inspector.get_pk_constraint(table)
        if pk and 'constrained_columns' in pk and pk['constrained_columns']:
            return pk['constrained_columns'][0]
        # Fallback: Suche nach Spalten mit 'id' im Namen
        columns = get_columns(table)
        for col in columns:
            if col.lower() == 'id':
                return col
        # Zweiter Fallback: Erste Spalte
        if columns:
            return columns[0]
        return None
    except:
        return None

# Hilfsfunktion: Spaltentypen einer Tabelle
def get_column_types(table):
    try:
        return {col["name"]: str(col["type"]) for col in inspector.get_columns(table)}
    except:
        return {}

# Hilfsfunktion: Automatische Einträge in ticket_mitarbeiter und ticket_kategorie
def create_ticket_relations(ticket_id, mitarbeiter_id, kategorie_id=1):
    try:
        with engine.begin() as conn:
            # Eintrag in ticket_mitarbeiter
            if mitarbeiter_id:
                # Prüfen, ob der Eintrag bereits existiert
                check_query = text("SELECT COUNT(*) FROM ticket_mitarbeiter WHERE ID_Ticket = :ticket_id AND ID_Mitarbeiter = :mitarbeiter_id")
                result = conn.execute(check_query, {"ticket_id": ticket_id, "mitarbeiter_id": mitarbeiter_id}).scalar()

                if result == 0:  # Eintrag existiert noch nicht
                    insert_query = text("INSERT INTO ticket_mitarbeiter (ID_Ticket, ID_Mitarbeiter, Rolle_im_Ticket) VALUES (:ticket_id, :mitarbeiter_id, 'Hauptverantwortlicher')")
                    conn.execute(insert_query, {"ticket_id": ticket_id, "mitarbeiter_id": mitarbeiter_id})

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

# Passwort-Hashing-Funktionen
def generate_salt():
    """Generiert einen zufälligen Salt für das Passwort-Hashing."""
    return secrets.token_hex(16)

def hash_password(password, salt):
    """Hasht ein Passwort mit dem angegebenen Salt."""
    salted_password = password + salt
    password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    return password_hash

def verify_password(password, stored_hash, salt):
    """Überprüft, ob das eingegebene Passwort korrekt ist."""
    calculated_hash = hash_password(password, salt)
    return calculated_hash == stored_hash

# Funktion zur Generierung eines temporären Passworts
def generate_temp_password(length=12):
    """Generiert ein zufälliges temporäres Passwort."""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    # Sicherstellen, dass mindestens ein Zeichen aus jeder Kategorie enthalten ist
    password = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        random.choice("!@#$%^&*")
    ]
    # Restliche Zeichen zufällig auswählen
    password.extend(random.choice(characters) for _ in range(length - 4))
    # Mischen der Zeichen
    random.shuffle(password)
    return ''.join(password)

# Authentifizierungsfunktion
def authenticate_user(username_or_email, password):
    """Authentifiziert einen Benutzer anhand von Benutzername/E-Mail und Passwort."""
    try:
        # Kleine Verzögerung als Schutz vor Brute-Force-Angriffen
        time.sleep(0.5)

        # Benutzer in der Datenbank suchen
        query = text("""
        SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required 
        FROM mitarbeiter 
        WHERE Name = :username OR Email = :email
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"username": username_or_email, "email": username_or_email}).fetchone()

        if not result:
            return False, None, False

        user_id, name, stored_hash, salt, password_change_required = result

        # Falls kein Salt vorhanden ist (Altdaten), Passwort direkt vergleichen
        # und bei Erfolg ein Salt generieren und das Passwort hashen
        if not salt:
            if password == stored_hash:
                # Passwort ist korrekt, aber ungehasht - jetzt hashen und speichern
                new_salt = generate_salt()
                new_hash = hash_password(password, new_salt)

                # Datensatz aktualisieren
                update_query = text("""
                UPDATE mitarbeiter 
                SET Password_hash = :password_hash, salt = :salt 
                WHERE ID_Mitarbeiter = :user_id
                """)

                with engine.begin() as conn:
                    conn.execute(update_query, {
                        "password_hash": new_hash,
                        "salt": new_salt,
                        "user_id": user_id
                    })

                return True, user_id, password_change_required
            else:
                return False, None, False

        # Ansonsten mit Salt hashen und vergleichen
        if verify_password(password, stored_hash, salt):
            return True, user_id, password_change_required
        else:
            return False, None, False

    except Exception as e:
        st.error(f"Fehler bei der Authentifizierung: {str(e)}")
        return False, None, False

# Funktion zur Überprüfung, ob die erforderlichen Spalten existieren, und falls nicht, sie hinzufügen
def ensure_required_columns_exist():
    try:
        # Prüfen, ob die salt-Spalte bereits existiert
        mitarbeiter_columns = get_columns("mitarbeiter")

        # Salt-Spalte hinzufügen, falls nicht vorhanden
        if "salt" not in mitarbeiter_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN salt VARCHAR(64)"))

        # Reset-Token-Spalte hinzufügen, falls nicht vorhanden
        if "reset_token" not in mitarbeiter_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN reset_token VARCHAR(64)"))

        # Reset-Token-Expiry-Spalte hinzufügen, falls nicht vorhanden
        if "reset_token_expiry" not in mitarbeiter_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN reset_token_expiry DATETIME"))

        # Password-Change-Required-Spalte hinzufügen, falls nicht vorhanden
        if "password_change_required" not in mitarbeiter_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN password_change_required BOOLEAN DEFAULT FALSE"))

        return True
    except Exception as e:
        st.error(f"Fehler beim Überprüfen/Hinzufügen der erforderlichen Spalten: {str(e)}")
        return False

# Funktion zur Passwort-Wiederherstellung
def reset_password(email):
    """Setzt das Passwort eines Benutzers zurück und generiert ein temporäres Passwort."""
    try:
        # Benutzer in der Datenbank suchen
        query = text("""
        SELECT ID_Mitarbeiter, Name, Email 
        FROM mitarbeiter 
        WHERE Email = :email
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"email": email}).fetchone()

        if not result:
            return False, None, None

        user_id, name, user_email = result

        # Temporäres Passwort generieren
        temp_password = generate_temp_password()

        # Salt generieren und temporäres Passwort hashen
        salt = generate_salt()
        password_hash = hash_password(temp_password, salt)

        # Ablaufdatum für das temporäre Passwort (24 Stunden)
        expiry = datetime.now() + timedelta(hours=24)

        # Datensatz aktualisieren
        update_query = text("""
        UPDATE mitarbeiter 
        SET Password_hash = :password_hash, 
            salt = :salt, 
            reset_token = :reset_token, 
            reset_token_expiry = :expiry, 
            password_change_required = TRUE 
        WHERE ID_Mitarbeiter = :user_id
        """)

        with engine.begin() as conn:
            conn.execute(update_query, {
                "password_hash": password_hash,
                "salt": salt,
                "reset_token": secrets.token_hex(16),  # Zusätzlicher Token für Sicherheit
                "expiry": expiry,
                "user_id": user_id
            })

        return True, name, temp_password

    except Exception as e:
        st.error(f"Fehler bei der Passwort-Wiederherstellung: {str(e)}")
        return False, None, None

# Funktion zum Ändern des Passworts
def change_password(user_id, new_password):
    """Ändert das Passwort eines Benutzers."""
    try:
        # Salt generieren und neues Passwort hashen
        salt = generate_salt()
        password_hash = hash_password(new_password, salt)

        # Datensatz aktualisieren
        update_query = text("""
        UPDATE mitarbeiter 
        SET Password_hash = :password_hash, 
            salt = :salt, 
            reset_token = NULL, 
            reset_token_expiry = NULL, 
            password_change_required = FALSE 
        WHERE ID_Mitarbeiter = :user_id
        """)

        with engine.begin() as conn:
            conn.execute(update_query, {
                "password_hash": password_hash,
                "salt": salt,
                "user_id": user_id
            })

        return True

    except Exception as e:
        st.error(f"Fehler beim Ändern des Passworts: {str(e)}")
        return False

# Passwort-Wiederherstellungsseite anzeigen
def show_password_reset_page():
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
            success, name, temp_password = reset_password(email)
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

# Passwortänderungsseite anzeigen
def show_password_change_page():
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
            success = change_password(st.session_state.user_id, new_password)
            if success:
                st.success("Passwort erfolgreich geändert!")
                st.session_state.password_changed = True
                time.sleep(1)  # Kurze Verzögerung, damit die Erfolgsmeldung sichtbar ist
                st.rerun()
            else:
                st.error("Fehler beim Ändern des Passworts.")

# Login-Seite anzeigen
def show_login_page():
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
            success, user_id, password_change_required = authenticate_user(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.user_id = user_id
                st.session_state.password_change_required = password_change_required

                # Benutzername für die Anzeige speichern
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT Name FROM mitarbeiter WHERE ID_Mitarbeiter = :user_id"),
                                          {"user_id": user_id}).fetchone()
                    if result:
                        st.session_state.username = result[0]

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

# Hauptanwendung
def main():
    # Sicherstellen, dass die erforderlichen Spalten existieren
    ensure_required_columns_exist()

    # Seiteneinstellungen
    st.set_page_config(page_title="Ticketsystem & Datenbankverwaltung", page_icon="🎫", layout="wide")

    # Session-State initialisieren
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "show_password_reset" not in st.session_state:
        st.session_state.show_password_reset = False

    if "password_change_required" not in st.session_state:
        st.session_state.password_change_required = False

    if "password_changed" not in st.session_state:
        st.session_state.password_changed = False

    # Passwort-Wiederherstellungsseite anzeigen, wenn angefordert
    if st.session_state.show_password_reset:
        show_password_reset_page()
        return

    # Prüfen, ob der Benutzer angemeldet ist
    if not st.session_state.logged_in:
        show_login_page()
        return

    # Prüfen, ob eine Passwortänderung erforderlich ist
    if st.session_state.password_change_required and not st.session_state.password_changed:
        show_password_change_page()
        return

    # Sidebar für Navigation und Datenbankinfo
    with st.sidebar:
        st.title("🎫 Ticketsystem")
        st.header("Navigation")

        app_mode = st.radio(
            "Modus wählen:",
            ["Ticketsystem", "Datenbankverwaltung"]
        )

        st.header("Datenbankübersicht")
        st.write(f"**Verbunden mit:** {DB_NAME} auf {DB_HOST}")

        # Tabellen anzeigen
        tabellen = inspector.get_table_names()
        with st.expander("Verfügbare Tabellen"):
            for table in tabellen:
                st.write(f"- {table}")

        # Datenbank-Schema anzeigen
        with st.expander("Datenbank-Schema"):
            for table_name in tabellen:
                st.write(f"**Tabelle: {table_name}**")
                columns = inspector.get_columns(table_name)
                for column in columns:
                    st.write(f"- {column['name']}")
                st.write("---")

        # Angemeldeter Benutzer und Abmelden-Button
        st.markdown("---")
        st.write(f"Angemeldet als: **{st.session_state.username}**")

        # Passwort ändern Button
        if st.button("Passwort ändern"):
            st.session_state.password_change_required = True
            st.session_state.password_changed = False
            st.rerun()

        # Abmelden Button
        if st.button("Abmelden"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.password_change_required = False
            st.session_state.password_changed = False
            st.rerun()

    # Ticketsystem-Modus
    if app_mode == "Ticketsystem":
        st.title("🎫 Ticketsystem")

        # Tabs für verschiedene Ticketsystem-Funktionen
        ticket_tabs = st.tabs(["📋 Ticketübersicht", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"])

        # Tab: Ticketübersicht
        with ticket_tabs[0]:
            st.header("Ticketübersicht")
#################################################################################
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
###############################################################################################################################
            # Filter-Optionen
            st.subheader("Filter")
            col1, col2, col3 = st.columns(3)

            with col1:
                # Status-Filter
                status_df = pd.read_sql("SELECT ID_Status, Name FROM status", con=engine)
                status_options = ["Alle"] + status_df["Name"].tolist()
                status_filter = st.selectbox("Status", status_options)

            with col2:
                # Prioritäts-Filter
                prioritaet_options = ["Alle", "niedrig", "mittel", "hoch"]
                prioritaet_filter = st.selectbox("Priorität", prioritaet_options)

            with col3:
                # Mitarbeiter-Filter
                mitarbeiter_df = pd.read_sql("SELECT ID_Mitarbeiter, Name FROM mitarbeiter", con=engine)
                mitarbeiter_options = ["Alle"] + mitarbeiter_df["Name"].tolist()
                mitarbeiter_filter = st.selectbox("Mitarbeiter", mitarbeiter_options)

            # SQL-Query mit Filtern und Suchbegriff erstellen
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

            if prioritaet_filter != "Alle":
                query += " AND t.Priorität = :prioritaet"
                params["prioritaet"] = prioritaet_filter

            if mitarbeiter_filter != "Alle":
                query += " AND m.Name = :mitarbeiter"
                params["mitarbeiter"] = mitarbeiter_filter
###################################################################################################
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
##########################################################################################################################
            # Tickets laden
            try:
                tickets_df = pd.read_sql(text(query), con=engine, params=params)

                if tickets_df.empty:
                    if search_term:
                        st.warning(f"Keine Tickets gefunden, die den Suchkriterien '{search_term}' entsprechen.")
                    else:
                        st.info("Keine Tickets gefunden, die den Filterkriterien entsprechen.")
                else:
                    # Anzeige der Tickets
                    st.write(f"**{len(tickets_df)} Tickets gefunden**")
                    st.dataframe(tickets_df, use_container_width=True)

                    # Ticket-Details anzeigen
                    if "selected_ticket_id" not in st.session_state:
                        st.session_state.selected_ticket_id = None

                    ticket_ids = tickets_df["ID_Ticket"].tolist()
                    selected_ticket_id = st.selectbox("Ticket zur Detailansicht auswählen", ticket_ids)

                    if selected_ticket_id:
                        st.session_state.selected_ticket_id = selected_ticket_id

                        # Ticket-Details laden
                        ticket_details = tickets_df[tickets_df["ID_Ticket"] == selected_ticket_id].iloc[0]

                        # Kategorien des Tickets laden
                        kategorien_query = """
                        SELECT k.Name
                        FROM ticket_kategorie tk
                        JOIN kategorie k ON tk.ID_Kategorie = k.ID_Kategorie
                        WHERE tk.ID_Ticket = :ticket_id
                        """
                        kategorien_df = pd.read_sql(text(kategorien_query), con=engine, params={"ticket_id": selected_ticket_id})

                        # Kommentare zum Ticket laden
                        kommentare_query = """
                        SELECT tk.Kommentar_Text, m.Name as Mitarbeiter, tk.Erstellt_am
                        FROM ticket_kommentar tk
                        LEFT JOIN mitarbeiter m ON tk.ID_Mitarbeiter = m.ID_Mitarbeiter
                        WHERE tk.ID_Ticket = :ticket_id
                        ORDER BY tk.Erstellt_am DESC
                        """
                        kommentare_df = pd.read_sql(text(kommentare_query), con=engine, params={"ticket_id": selected_ticket_id})
##################################################################################################################################################################
                        # Ticket-Details anzeigen
                        st.subheader(f"Ticket #{selected_ticket_id}: {ticket_details['Titel']}")

                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Status:** {ticket_details['Status']}")
                            st.markdown(f"**Priorität:** {ticket_details['Priorität']}")
                            st.markdown(f"**Zugewiesen an:** {ticket_details['Mitarbeiter']}")
                            st.markdown(f"**Kunde:** {ticket_details['Kunde']}")

                        with col2:
                            st.markdown(f"**Erstellt am:** {ticket_details['Erstellt_am']}")
                            st.markdown(f"**Zuletzt geändert:** {ticket_details['Geändert_am']}")
                            st.markdown(f"**Kategorien:** {', '.join(kategorien_df['Name'].tolist()) if not kategorien_df.empty else 'Keine'}")

                        st.markdown("**Beschreibung:**")
                        st.markdown(ticket_details['Beschreibung'])

                        # Kommentare anzeigen
                        st.markdown("---")
                        st.subheader("Kommentare")

                        if kommentare_df.empty:
                            st.info("Keine Kommentare vorhanden.")
                        else:
                            for _, kommentar in kommentare_df.iterrows():
                                st.markdown(f"**{kommentar['Mitarbeiter']}** am {kommentar['Erstellt_am']}:")
                                st.markdown(kommentar['Kommentar_Text'])
                                st.markdown("---")

                        # Neuen Kommentar hinzufügen
                        with st.form(key=f"add_comment_form_{selected_ticket_id}"):
                            st.subheader("Neuen Kommentar hinzufügen")

                            # Aktuellen angemeldeten Mitarbeiter als Standard verwenden
                            mitarbeiter_id = st.session_state.user_id
                            mitarbeiter_name = st.session_state.username
                            st.write(f"Kommentar als: **{mitarbeiter_name}**")

                            kommentar_text = st.text_area("Kommentar")

                            submit_comment = st.form_submit_button("Kommentar hinzufügen")

                        if submit_comment and kommentar_text:
                            try:
                                with engine.begin() as conn:
                                    insert_query = text("""
                                    INSERT INTO ticket_kommentar (ID_Ticket, ID_Mitarbeiter, Kommentar_Text)
                                    VALUES (:ticket_id, :mitarbeiter_id, :kommentar_text)
                                    """)
                                    conn.execute(insert_query, {
                                        "ticket_id": selected_ticket_id,
                                        "mitarbeiter_id": mitarbeiter_id,
                                        "kommentar_text": kommentar_text
                                    })

                                st.success("Kommentar erfolgreich hinzugefügt!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")

            except Exception as e:
                st.error(f"Fehler beim Laden der Tickets: {str(e)}")

        # Tab: Neues Ticket
        with ticket_tabs[1]:
            st.header("Neues Ticket erstellen")

            with st.form(key="new_ticket_form"):
                # Ticket-Informationen
                titel = st.text_input("Titel", max_chars=255)
                beschreibung = st.text_area("Beschreibung")

                col1, col2, col3 = st.columns(3)

                with col1:
                    # Priorität
                    prioritaet = st.selectbox("Priorität", ["niedrig", "mittel", "hoch"], index=1)

                with col2:
                    # Status
                    status_df = pd.read_sql("SELECT ID_Status, Name FROM status", con=engine)
                    status_id = st.selectbox(
                        "Status",
                        status_df["ID_Status"].tolist(),
                        format_func=lambda x: status_df[status_df["ID_Status"] == x]["Name"].iloc[0]
                    )

                with col3:
                    # Kunde
                    kunden_df = pd.read_sql("SELECT ID_Kunde, Name FROM kunde", con=engine)
                    kunde_id = st.selectbox(
                        "Kunde",
                        kunden_df["ID_Kunde"].tolist(),
                        format_func=lambda x: kunden_df[kunden_df["ID_Kunde"] == x]["Name"].iloc[0]
                    )

                # Mitarbeiter (aktuell angemeldeter Benutzer als Standard)
                mitarbeiter_id = st.session_state.user_id
                mitarbeiter_name = st.session_state.username
                st.write(f"Zuständiger Mitarbeiter: **{mitarbeiter_name}**")

                # Kategorien
                kategorien_df = pd.read_sql("SELECT ID_Kategorie, Name FROM kategorie", con=engine)
                kategorie_id = st.selectbox(
                    "Kategorie",
                    kategorien_df["ID_Kategorie"].tolist(),
                    format_func=lambda x: kategorien_df[kategorien_df["ID_Kategorie"] == x]["Name"].iloc[0]
                )

                submit_ticket = st.form_submit_button("Ticket erstellen")

            if submit_ticket:
                if not titel:
                    st.error("Bitte geben Sie einen Titel ein.")
                else:
                    try:
                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO ticket (Titel, Beschreibung, Priorität, ID_Status, ID_Kunde, ID_Mitarbeiter, Erstellt_am, Geändert_am)
                            VALUES (:titel, :beschreibung, :prioritaet, :status_id, :kunde_id, :mitarbeiter_id, NOW(), NOW())
                            """)
                            result = conn.execute(insert_query, {
                                "titel": titel,
                                "beschreibung": beschreibung,
                                "prioritaet": prioritaet,
                                "status_id": status_id,
                                "kunde_id": kunde_id,
                                "mitarbeiter_id": mitarbeiter_id
                            })

                            # ID des neuen Tickets abrufen
                            ticket_id = result.lastrowid

                            # Automatische Beziehungen erstellen
                            create_ticket_relations(ticket_id, mitarbeiter_id, kategorie_id)

                        st.success(f"Ticket #{ticket_id} erfolgreich erstellt!")
                        # Formular zurücksetzen
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Erstellen des Tickets: {str(e)}")

        # Tab: Statistiken
        with ticket_tabs[2]:
            st.header("Statistiken")

            try:
                # Tickets nach Status
                status_stats_query = """
                SELECT s.Name as Status, COUNT(t.ID_Ticket) as Anzahl
                FROM ticket t
                JOIN status s ON t.ID_Status = s.ID_Status
                GROUP BY s.Name
                ORDER BY Anzahl DESC
                """
                status_stats_df = pd.read_sql(status_stats_query, con=engine)

                # Tickets nach Priorität
                prio_stats_query = """
                SELECT Priorität, COUNT(ID_Ticket) as Anzahl
                FROM ticket
                GROUP BY Priorität
                ORDER BY FIELD(Priorität, 'hoch', 'mittel', 'niedrig')
                """
                prio_stats_df = pd.read_sql(prio_stats_query, con=engine)

                # Tickets nach Mitarbeiter
                mitarbeiter_stats_query = """
                SELECT m.Name as Mitarbeiter, COUNT(t.ID_Ticket) as Anzahl
                FROM ticket t
                JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
                GROUP BY m.Name
                ORDER BY Anzahl DESC
                LIMIT 10
                """
                mitarbeiter_stats_df = pd.read_sql(mitarbeiter_stats_query, con=engine)

                # Tickets nach Kunde
                kunden_stats_query = """
                SELECT k.Name as Kunde, COUNT(t.ID_Ticket) as Anzahl
                FROM ticket t
                JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
                GROUP BY k.Name
                ORDER BY Anzahl DESC
                LIMIT 10
                """
                kunden_stats_df = pd.read_sql(kunden_stats_query, con=engine)

                # Visualisierungen
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Tickets nach Status")
                    status_chart = alt.Chart(status_stats_df).mark_bar().encode(
                        x=alt.X('Status:N', sort='-y'),
                        y='Anzahl:Q',
                        color=alt.Color('Status:N', legend=None)
                    ).properties(height=300)
                    st.altair_chart(status_chart, use_container_width=True)

                    st.subheader("Top 10 Mitarbeiter nach Tickets")
                    mitarbeiter_chart = alt.Chart(mitarbeiter_stats_df).mark_bar().encode(
                        x=alt.X('Mitarbeiter:N', sort='-y'),
                        y='Anzahl:Q',
                        color=alt.Color('Mitarbeiter:N', legend=None)
                    ).properties(height=300)
                    st.altair_chart(mitarbeiter_chart, use_container_width=True)

                with col2:
                    st.subheader("Tickets nach Priorität")
                    prio_chart = alt.Chart(prio_stats_df).mark_bar().encode(
                        x=alt.X('Priorität:N', sort=['hoch', 'mittel', 'niedrig']),
                        y='Anzahl:Q',
                        color=alt.Color('Priorität:N', legend=None)
                    ).properties(height=300)
                    st.altair_chart(prio_chart, use_container_width=True)

                    st.subheader("Top 10 Kunden nach Tickets")
                    kunden_chart = alt.Chart(kunden_stats_df).mark_bar().encode(
                        x=alt.X('Kunde:N', sort='-y'),
                        y='Anzahl:Q',
                        color=alt.Color('Kunde:N', legend=None)
                    ).properties(height=300)
                    st.altair_chart(kunden_chart, use_container_width=True)

            except Exception as e:
                st.error(f"Fehler beim Laden der Statistiken: {str(e)}")

        # Tab: Einstellungen
        with ticket_tabs[3]:
            st.header("Einstellungen")

            settings_tabs = st.tabs(["Mitarbeiter", "Kunden", "Kategorien", "Status"])

            # Mitarbeiter-Einstellungen
            with settings_tabs[0]:
                st.subheader("Mitarbeiter verwalten")

                # Mitarbeiter anzeigen
                mitarbeiter_df = pd.read_sql("""
                SELECT m.ID_Mitarbeiter, m.Name, m.Email, r.Name as Rolle, m.Erstellt_am
                FROM mitarbeiter m
                LEFT JOIN rolle r ON m.ID_Rolle = r.ID_Rolle
                """, con=engine)

                st.dataframe(mitarbeiter_df, use_container_width=True)

                # Neuen Mitarbeiter hinzufügen
                with st.expander("Neuen Mitarbeiter hinzufügen"):
                    with st.form(key="add_mitarbeiter_form"):
                        name = st.text_input("Name")
                        email = st.text_input("E-Mail")

                        # Rollen laden
                        rollen_df = pd.read_sql("SELECT ID_Rolle, Name FROM rolle", con=engine)
                        rolle_id = st.selectbox(
                            "Rolle",
                            rollen_df["ID_Rolle"].tolist(),
                            format_func=lambda x: rollen_df[rollen_df["ID_Rolle"] == x]["Name"].iloc[0]
                        )

                        password = st.text_input("Passwort", type="password")
                        password_confirm = st.text_input("Passwort bestätigen", type="password")

                        submit_mitarbeiter = st.form_submit_button("Mitarbeiter hinzufügen")

                    if submit_mitarbeiter:
                        if not name or not email or not password:
                            st.error("Bitte füllen Sie alle Pflichtfelder aus.")
                        elif password != password_confirm:
                            st.error("Die Passwörter stimmen nicht überein.")
                        else:
                            try:
                                # Salt generieren und Passwort hashen
                                salt = generate_salt()
                                password_hash = hash_password(password, salt)

                                with engine.begin() as conn:
                                    insert_query = text("""
                                    INSERT INTO mitarbeiter (Name, Email, ID_Rolle, Password_hash, salt, Erstellt_am)
                                    VALUES (:name, :email, :rolle_id, :password_hash, :salt, NOW())
                                    """)
                                    conn.execute(insert_query, {
                                        "name": name,
                                        "email": email,
                                        "rolle_id": rolle_id,
                                        "password_hash": password_hash,
                                        "salt": salt
                                    })

                                st.success("Mitarbeiter erfolgreich hinzugefügt!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Hinzufügen des Mitarbeiters: {str(e)}")

            # Kunden-Einstellungen
            with settings_tabs[1]:
                st.subheader("Kunden verwalten")

                # Kunden anzeigen
                kunden_df = pd.read_sql("SELECT * FROM kunde", con=engine)
                st.dataframe(kunden_df, use_container_width=True)

                # Neuen Kunden hinzufügen
                with st.expander("Neuen Kunden hinzufügen"):
                    with st.form(key="add_kunde_form"):
                        name = st.text_input("Name")
                        kontaktperson = st.text_input("Kontaktperson")
                        email = st.text_input("E-Mail")
                        telefon = st.text_input("Telefon")

                        submit_kunde = st.form_submit_button("Kunden hinzufügen")

                    if submit_kunde:
                        if not name:
                            st.error("Bitte geben Sie einen Namen ein.")
                        else:
                            try:
                                with engine.begin() as conn:
                                    insert_query = text("""
                                    INSERT INTO kunde (Name, Kontaktperson, Email, Telefon)
                                    VALUES (:name, :kontaktperson, :email, :telefon)
                                    """)
                                    conn.execute(insert_query, {
                                        "name": name,
                                        "kontaktperson": kontaktperson,
                                        "email": email,
                                        "telefon": telefon
                                    })

                                st.success("Kunde erfolgreich hinzugefügt!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Hinzufügen des Kunden: {str(e)}")

            # Kategorien-Einstellungen
            with settings_tabs[2]:
                st.subheader("Kategorien verwalten")

                # Kategorien anzeigen
                kategorien_df = pd.read_sql("SELECT * FROM kategorie", con=engine)
                st.dataframe(kategorien_df, use_container_width=True)

                # Neue Kategorie hinzufügen
                with st.expander("Neue Kategorie hinzufügen"):
                    with st.form(key="add_kategorie_form"):
                        name = st.text_input("Name")
                        beschreibung = st.text_area("Beschreibung")

                        submit_kategorie = st.form_submit_button("Kategorie hinzufügen")

                    if submit_kategorie:
                        if not name:
                            st.error("Bitte geben Sie einen Namen ein.")
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

                                st.success("Kategorie erfolgreich hinzugefügt!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Hinzufügen der Kategorie: {str(e)}")

            # Status-Einstellungen
            with settings_tabs[3]:
                st.subheader("Status verwalten")

                # Status anzeigen
                status_df = pd.read_sql("SELECT * FROM status", con=engine)
                st.dataframe(status_df, use_container_width=True)

                # Neuen Status hinzufügen
                with st.expander("Neuen Status hinzufügen"):
                    with st.form(key="add_status_form"):
                        name = st.text_input("Name")
                        beschreibung = st.text_area("Beschreibung")

                        submit_status = st.form_submit_button("Status hinzufügen")

                    if submit_status:
                        if not name:
                            st.error("Bitte geben Sie einen Namen ein.")
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

                                st.success("Status erfolgreich hinzugefügt!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Hinzufügen des Status: {str(e)}")

    # Datenbankverwaltungs-Modus
    else:  # app_mode == "Datenbankverwaltung"
        st.title("🛠️ Datenbankverwaltung")

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Anzeigen", "✏️ Bearbeiten", "➕ Einfügen", "❌ Löschen"])

        # -----------------------------
        # 📋 Tab 1: Anzeigen
        # -----------------------------
        with tab1:

            st.subheader("Tabelle anzeigen")

            try:
                tabellen = inspector.get_table_names()
                table_choice = st.selectbox("Wähle eine Tabelle", tabellen, key="view_table")

                # Automatisch Daten laden, sobald eine Tabelle gewählt wird
                df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)
                st.dataframe(df, use_container_width=True)

                # Optional: In Session speichern für andere Tabs
                st.session_state["last_viewed_table"] = table_choice
                st.session_state["last_viewed_df"] = df.copy()

            except Exception as e:
                st.error("❌ Fehler beim Laden:")
                st.exception(e)

 ####################suchfunktion########################


        st.subheader("🔍 Daten suchen")
        search_col1, search_col2 = st.columns([3, 1])

    with search_col1:
        search_term = st.text_input("Suchbegriff eingeben (Titel, Beschreibung, Kunde, Mitarbeiter)", placeholder="z.B. Server, Netzwerk, Max Mustermann...")

    with search_col2:
        search_field = st.selectbox(
            "Suchfeld",
            ["Alle Felder", "Titel", "Beschreibung", "Kunde", "Mitarbeiter"]
        )
#############################################################

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




        ##########################################################################################################################
        # -----------------------------
        # ✏️ Tab 2: Bearbeiten
        # -----------------------------
        with tab2:
            st.subheader("Datensätze bearbeiten (interaktiv)")

            try:
                tabellen = inspector.get_table_names()
                table_choice_edit = st.selectbox("Tabelle wählen (Bearbeiten)", tabellen, key="edit_table_editor")
                spalten = get_columns(table_choice_edit)
                id_spalte = st.selectbox("Primärschlüsselspalte", spalten, key="primary_column_editor")

                if "original_df" not in st.session_state:
                    st.session_state.original_df = pd.DataFrame()
                if "edited_df" not in st.session_state:
                    st.session_state.edited_df = pd.DataFrame()

                if st.button("🔄 Daten laden (Editiermodus)"):
                    df = pd.read_sql(f"SELECT * FROM {table_choice_edit}", con=engine)
                    st.session_state.original_df = df.copy()
                    st.session_state.edited_df = df.copy()

                if not st.session_state.original_df.empty:
                    st.markdown("✏️ **Daten bearbeiten – Änderungen werden erst nach dem Speichern übernommen.**")
                    st.session_state.edited_df = st.data_editor(
                        st.session_state.edited_df,
                        use_container_width=True,
                        num_rows="fixed",
                        key="editable_df"
                    )

                    if st.button("💾 Änderungen speichern"):
                        df = st.session_state.original_df
                        edited_df = st.session_state.edited_df
                        delta = df.compare(edited_df, keep_shape=True, keep_equal=True)
                        rows_to_update = delta.dropna(how="all").index.tolist()

                        if not rows_to_update:
                            st.info("Keine Änderungen erkannt.")
                        else:
                            try:
                                with engine.begin() as conn:
                                    for idx in rows_to_update:
                                        row = edited_df.loc[idx]
                                        original_row = df.loc[idx]

                                        update_fields = {}
                                        for col in spalten:
                                            if row[col] != original_row[col]:
                                                update_fields[col] = row[col]

                                        if update_fields:
                                            set_clause = ", ".join([f"{col} = :{col}" for col in update_fields])
                                            query = text(
                                                f"UPDATE {table_choice_edit} SET {set_clause} WHERE {id_spalte} = :id_value"
                                            )
                                            update_fields["id_value"] = row[id_spalte]
                                            conn.execute(query, update_fields)

                                st.success("✅ Änderungen erfolgreich gespeichert.")
                                # Daten neu laden
                                df = pd.read_sql(f"SELECT * FROM {table_choice_edit}", con=engine)
                                st.session_state.original_df = df.copy()
                                st.session_state.edited_df = df.copy()
                                st.rerun()

                            except Exception as e:
                                st.error("❌ Fehler beim Speichern:")
                                st.exception(e)

            except Exception as e:
                st.error("❌ Fehler beim Bearbeiten der Daten:")
                st.exception(e)


        # -----------------------------
        # ➕ Tab 3: Einfügen
        # -----------------------------
        with tab3:
            st.subheader("Datensatz einfügen")

            # Tabs für einzelne und mehrfache Einfügung
            insert_tab1, insert_tab2 = st.tabs(["Einzelner Datensatz", "Mehrere Datensätze"])

            try:
                tabellen = inspector.get_table_names()
                table_choice = st.selectbox("Tabelle wählen (Einfügen)", tabellen, key="insert_table")
                spalten = get_columns(table_choice)
                spalten_typen = get_column_types(table_choice)

                # Tab für einzelnen Datensatz
                with insert_tab1:
                    with st.form(key="insert_form_single"):
                        st.subheader(f"Neuen Datensatz in '{table_choice}' einfügen")

                        inputs = {}
                        for spalte in spalten:
                            # Spezielle Behandlung für Datum/Zeit-Spalten
                            if 'date' in spalte.lower() or 'time' in spalte.lower() or 'erstellt' in spalte.lower():
                                # Aktuelles Datum als Standardwert für Datum/Zeit-Spalten
                                default_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                inputs[spalte] = st.text_input(f"{spalte}", value=default_value, key=f"insert_{spalte}")
                            # Spezielle Behandlung für Passwort-Spalten
                            elif 'password' in spalte.lower() and table_choice.lower() == 'mitarbeiter':
                                password = st.text_input(f"{spalte}", type="password", key=f"insert_{spalte}")
                                # Salt wird automatisch generiert und das Passwort gehasht
                                inputs[spalte] = password  # Wird später verarbeitet
                            else:
                                inputs[spalte] = st.text_input(f"{spalte}", key=f"insert_{spalte}")

                        submit_insert = st.form_submit_button("💾 Einfügen")

                    if submit_insert:
                        try:
                            # Spezielle Behandlung für Mitarbeiter-Tabelle mit Passwort-Hashing
                            if table_choice.lower() == 'mitarbeiter' and 'Password_hash' in spalten:
                                # Salt generieren und Passwort hashen
                                salt = generate_salt()
                                password = inputs.get('Password_hash', '')
                                password_hash = hash_password(password, salt)

                                # Werte aktualisieren
                                inputs['Password_hash'] = password_hash
                                inputs['salt'] = salt

                            with engine.begin() as conn:
                                # Nur Spalten einfügen, für die Werte vorhanden sind
                                valid_spalten = [col for col in spalten if inputs.get(col)]
                                placeholders = ", ".join([f":{col}" for col in valid_spalten])
                                query = text(f"INSERT INTO {table_choice} ({', '.join(valid_spalten)}) VALUES ({placeholders})")
                                result = conn.execute(query, {col: inputs[col] for col in valid_spalten})

                                # Wenn es sich um ein Ticket handelt, automatische Beziehungen erstellen
                                if table_choice == "ticket":
                                    ticket_id = result.lastrowid
                                    mitarbeiter_id = inputs.get("ID_Mitarbeiter")

                                    # Standard-Kategorie (ID 1) verwenden
                                    create_ticket_relations(ticket_id, mitarbeiter_id, 1)

                            st.success(f"✅ Datensatz in '{table_choice}' eingefügt!")
                        except Exception as e:
                            st.error("❌ Fehler beim Einfügen:")
                            st.exception(e)

                # Tab für mehrere Datensätze
                with insert_tab2:
                    st.subheader(f"Mehrere Datensätze in '{table_choice}' einfügen")

                    # Initialisiere leeren DataFrame für die Eingabe, wenn noch nicht vorhanden
                    if "multi_insert_df" not in st.session_state or st.session_state.get("last_multi_insert_table") != table_choice:
                        # Erstelle leeren DataFrame mit den Spalten der Tabelle
                        empty_df = pd.DataFrame(columns=spalten)

                        # Füge eine leere Zeile hinzu
                        empty_row = {col: "" for col in spalten}
                        # Spezielle Behandlung für Datum/Zeit-Spalten
                        for col in spalten:
                            if 'date' in col.lower() or 'time' in col.lower() or 'erstellt' in col.lower():
                                empty_row[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        empty_df = pd.concat([empty_df, pd.DataFrame([empty_row])], ignore_index=True)

                        st.session_state["multi_insert_df"] = empty_df
                        st.session_state["last_multi_insert_table"] = table_choice

                    # Zeige Hinweis
                    st.info("Fügen Sie Zeilen hinzu und bearbeiten Sie die Daten. Klicken Sie dann auf 'Speichern'.")

                    # Daten-Editor für mehrere Zeilen
                    edited_df = st.data_editor(
                        st.session_state["multi_insert_df"],
                        use_container_width=True,
                        num_rows="dynamic",
                        key="multi_insert_editor"
                    )

                    # Speichern-Button
                    if st.button("💾 Alle Datensätze einfügen"):
                        if edited_df.empty or edited_df.iloc[0].isnull().all():
                            st.warning("Keine Daten zum Einfügen vorhanden.")
                        else:
                            try:
                                success_count = 0
                                error_count = 0

                                with engine.begin() as conn:
                                    for _, row in edited_df.iterrows():
                                        # Leere Zeilen überspringen
                                        if row.isnull().all():
                                            continue

                                        # Daten für die Einfügung vorbereiten
                                        insert_data = {}
                                        for col in spalten:
                                            if col in row and not pd.isna(row[col]):
                                                # Spezielle Behandlung für Mitarbeiter-Tabelle mit Passwort-Hashing
                                                if table_choice.lower() == 'mitarbeiter' and col == 'Password_hash':
                                                    salt = generate_salt()
                                                    password = row[col]
                                                    insert_data[col] = hash_password(password, salt)
                                                    insert_data['salt'] = salt
                                                else:
                                                    insert_data[col] = row[col]
                                            else:
                                                insert_data[col] = None

                                        try:
                                            # Nur Spalten einfügen, für die Werte vorhanden sind
                                            valid_spalten = [col for col in insert_data.keys() if insert_data[col] is not None]
                                            placeholders = ", ".join([f":{col}" for col in valid_spalten])
                                            columns = ", ".join(valid_spalten)
                                            query = text(f"INSERT INTO {table_choice} ({columns}) VALUES ({placeholders})")
                                            result = conn.execute(query, {col: insert_data[col] for col in valid_spalten})

                                            # Wenn es sich um ein Ticket handelt, automatische Beziehungen erstellen
                                            if table_choice == "ticket":
                                                ticket_id = result.lastrowid
                                                mitarbeiter_id = insert_data.get("ID_Mitarbeiter")
                                                create_ticket_relations(ticket_id, mitarbeiter_id, 1)

                                            success_count += 1
                                        except Exception as e:
                                            error_count += 1
                                            st.error(f"Fehler beim Einfügen von Zeile {_+1}: {str(e)}")

                                if success_count > 0:
                                    st.success(f"✅ {success_count} Datensätze erfolgreich eingefügt!")
                                if error_count > 0:
                                    st.warning(f"⚠️ {error_count} Datensätze konnten nicht eingefügt werden.")

                                # Zurücksetzen des Editors
                                if success_count > 0:
                                    # Erstelle leeren DataFrame mit den Spalten der Tabelle
                                    empty_df = pd.DataFrame(columns=spalten)
                                    # Füge eine leere Zeile hinzu
                                    empty_row = {col: "" for col in spalten}
                                    # Spezielle Behandlung für Datum/Zeit-Spalten
                                    for col in spalten:
                                        if 'date' in col.lower() or 'time' in col.lower() or 'erstellt' in col.lower():
                                            empty_row[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    empty_df = pd.concat([empty_df, pd.DataFrame([empty_row])], ignore_index=True)
                                    st.session_state["multi_insert_df"] = empty_df
                                    st.rerun()

                            except Exception as e:
                                st.error(f"❌ Fehler beim Einfügen der Datensätze: {str(e)}")

            except Exception as e:
                st.error("❌ Fehler beim Verarbeiten:")
                st.exception(e)


        # -----------------------------
        # ❌ Tab 4: Löschen
        # -----------------------------
        with tab4:
            st.subheader("Datensätze löschen")

            try:
                tabellen = inspector.get_table_names()
                table_choice = st.selectbox("Tabelle wählen (Löschen)", tabellen, key="delete_table")

                # Primärschlüssel ermitteln
                primary_key = get_primary_key(table_choice)

                if not primary_key:
                    st.warning(f"Kein Primärschlüssel für Tabelle '{table_choice}' gefunden. Löschen nicht möglich.")
                else:
                    # Daten laden
                    df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)

                    if df.empty:
                        st.info(f"Tabelle '{table_choice}' enthält keine Datensätze.")
                    else:
                        st.write("Wählen Sie die zu löschenden Datensätze aus:")

                        # Multiselect für die zu löschenden Zeilen
                        selection = st.data_editor(
                            df,
                            use_container_width=True,
                            disabled=df.columns.tolist(),
                            hide_index=False,
                            selection_mode="multi-row",
                            key="delete_selection"
                        )

                        selected_rows = selection.get("selected_rows", [])

                        if st.button("🗑️ Ausgewählte Datensätze löschen", type="primary", disabled=len(selected_rows) == 0):
                            if not selected_rows:
                                st.info("Keine Zeilen zum Löschen ausgewählt.")
                            else:
                                try:
                                    with engine.begin() as conn:
                                        for row_idx in selected_rows:
                                            row = df.iloc[row_idx]
                                            pk_value = row[primary_key]

                                            query = text(f"DELETE FROM {table_choice} WHERE {primary_key} = :pk_value")
                                            conn.execute(query, {"pk_value": pk_value})

                                    st.success(f"✅ {len(selected_rows)} Datensätze erfolgreich gelöscht!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Fehler beim Löschen: {str(e)}")
                                    st.exception(e)

                        elif len(selected_rows) == 0:
                            st.info("Bitte markiere mindestens eine Zeile zum Löschen.")

            except Exception as e:
                st.error("❌ Fehler beim Verarbeiten:")
                st.exception(e)

# Anwendung starten
if __name__ == "__main__":
    main()
