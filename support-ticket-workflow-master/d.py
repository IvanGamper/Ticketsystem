import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timedelta
##import traceback
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

#Hilfsfunktion Historie
def log_ticket_change(ticket_id, feldname, alter_wert, neuer_wert, mitarbeiter_id):
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

# Hilfsfunktion: Durchsuchbare Spalten einer Tabelle ermitteln
def get_searchable_columns(table):
    try:
        column_types = get_column_types(table)
        searchable_columns = []

        for col, type_str in column_types.items():
            # Spaltentypen, die für die Suche geeignet sind
            if any(text_type in type_str.lower() for text_type in ['char', 'text', 'varchar', 'enum']):
                searchable_columns.append(col)
            # Numerische Typen sind auch durchsuchbar
            elif any(num_type in type_str.lower() for num_type in ['int', 'decimal', 'float', 'double']):
                searchable_columns.append(col)
            # Datum/Zeit-Typen sind auch durchsuchbar
            elif any(date_type in type_str.lower() for date_type in ['date', 'time', 'datetime', 'timestamp']):
                searchable_columns.append(col)

        return searchable_columns
    except Exception as e:
        st.error(f"Fehler beim Ermitteln der durchsuchbaren Spalten: {str(e)}")
        return []

# Hilfsfunktion: Tabelle durchsuchen
def search_table(table_name, search_term, search_columns=None, exact_match=False, case_sensitive=False):
    try:
        if not search_term:
            return pd.DataFrame()

        # Durchsuchbare Spalten ermitteln
        if search_columns is None:
            search_columns = get_searchable_columns(table_name)

        if not search_columns:
            st.warning(f"Keine durchsuchbaren Spalten in der Tabelle '{table_name}' gefunden.")
            return pd.DataFrame()

        # SQL-Abfrage erstellen
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

                params[param_name] = search_term
            else:
                # Teilweise Übereinstimmung
                if case_sensitive:
                    conditions.append(f"{col} LIKE :{param_name}")
                else:
                    conditions.append(f"LOWER({col}) LIKE :{param_name}")
                    search_term = search_term.lower()

                params[param_name] = f"%{search_term}%"

        # WHERE-Klausel erstellen
        where_clause = " OR ".join(conditions)

        # SQL-Abfrage ausführen
        query = text(f"SELECT * FROM {table_name} WHERE {where_clause}")

        with engine.connect() as conn:
            result = conn.execute(query, params)
            columns = result.keys()
            data = result.fetchall()

        # DataFrame erstellen
        df = pd.DataFrame(data, columns=columns)
        return df

    except Exception as e:
        st.error(f"Fehler bei der Suche: {str(e)}")
        return pd.DataFrame()

# Hilfsfunktion: Automatische Einträge in ticket_mitarbeiter und ticket_kategorie
def create_ticket_relations(ticket_id, ID_Mitarbeiter, kategorie_id=1):
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

# Hauptfunktion
def main():
    # Seitenkonfiguration
    st.set_page_config(page_title="Ticketsystem mit Datenbankverwaltung", page_icon="🎫", layout="wide")

    # Sicherstellen, dass die erforderlichen Spalten existieren
    ensure_required_columns_exist()

    # Session-State initialisieren
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Anmeldestatus prüfen
    if not st.session_state.logged_in:
        # Passwort-Wiederherstellung anzeigen, falls angefordert
        if "show_password_reset" in st.session_state and st.session_state.show_password_reset:
            show_password_reset_page()
        else:
            # Ansonsten Login-Seite anzeigen
            show_login_page()
    else:
        # Passwortänderung anzeigen, falls erforderlich
        if "password_change_required" in st.session_state and st.session_state.password_change_required and not st.session_state.get("password_changed", False):
            show_password_change_page()
        else:
            # Hauptanwendung anzeigen
            show_main_application()

    # Sidebar für Navigation und Datenbankinfo
    with st.sidebar:
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

# Hauptanwendung anzeigen
def show_main_application():
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
            ["Ticketsystem", "Datenbankverwaltung"],
            key="app_mode_selector"
        )

    # Hauptinhalt basierend auf dem gewählten Modus
    if app_mode == "Ticketsystem":
        show_ticket_system()
    else:  # app_mode == "Datenbankverwaltung"
        show_database_management()

# Ticketsystem anzeigen
def show_ticket_system():
    st.title("🎫 Ticketsystem")

    # Tabs für verschiedene Funktionen
    ticket_tabs = st.tabs(["📋 Ticketübersicht", "✏️ Ticket bearbeiten", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"])

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

# Ticketübersicht anzeigen
def show_ticket_overview():
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

# Ticket-Statistiken anzeigen
def show_ticket_statistics():
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

# Datenbankverwaltung anzeigen
def show_database_management():
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

            # Suchfunktion für die ausgewählte Tabelle
            st.subheader("🔍 Tabellensuche")

            # Durchsuchbare Spalten ermitteln
            searchable_columns = get_searchable_columns(table_choice)

            # Suchoptionen
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                search_term = st.text_input("Suchbegriff eingeben", placeholder="Suchbegriff...", key=f"search_term_{table_choice}")

            with col2:
                # Mehrfachauswahl für Spalten
                selected_columns = st.multiselect(
                    "Zu durchsuchende Spalten (leer = alle)",
                    options=searchable_columns,
                    key=f"search_columns_{table_choice}"
                )

            with col3:
                # Erweiterte Suchoptionen
                exact_match = st.checkbox("Exakte Übereinstimmung", key=f"exact_match_{table_choice}")
                case_sensitive = st.checkbox("Groß-/Kleinschreibung beachten", key=f"case_sensitive_{table_choice}")

            # Suchbutton
            search_clicked = st.button("Suchen", key=f"search_button_{table_choice}")

            # Daten laden - entweder Suchergebnisse oder alle Daten
            if search_clicked and search_term:
                # Suche durchführen
                results = search_table(
                    table_name=table_choice,
                    search_term=search_term,
                    search_columns=selected_columns if selected_columns else None,
                    exact_match=exact_match,
                    case_sensitive=case_sensitive
                )

                # Ergebnisse anzeigen
                if results.empty:
                    st.warning(f"Keine Ergebnisse für '{search_term}' gefunden.")
                    # Alle Daten anzeigen als Fallback
                    df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)
                    st.write("Stattdessen werden alle Daten angezeigt:")
                else:
                    st.success(f"{len(results)} Ergebnisse gefunden.")
                    df = results
            else:
                # Alle Daten anzeigen
                df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)

            # Daten anzeigen
            st.dataframe(df, use_container_width=True)

            # Button zum Zurücksetzen der Suche
            if search_clicked and search_term:
                if st.button("Suche zurücksetzen", key=f"reset_search_{table_choice}"):
                    st.rerun()

            # Optional: In Session speichern für andere Tabs
            st.session_state["last_viewed_table"] = table_choice
            st.session_state["last_viewed_df"] = df.copy()

        except Exception as e:
            st.error("❌ Fehler beim Laden:")
            st.exception(e)

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
                                ID_Mitarbeiter = inputs.get("ID_Mitarbeiter")

                                # Standard-Kategorie (ID 1) verwenden
                                create_ticket_relations(ticket_id, ID_Mitarbeiter, 1)

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

                                    # Nur Spalten einfügen, für die Werte vorhanden sind
                                    valid_spalten = [col for col in spalten if pd.notna(row[col]) and row[col] != ""]
                                    if not valid_spalten:
                                        continue

                                    try:
                                        # Spezielle Behandlung für Mitarbeiter-Tabelle mit Passwort-Hashing
                                        values = {}
                                        for col in valid_spalten:
                                            values[col] = row[col]

                                        if table_choice.lower() == 'mitarbeiter' and 'Password_hash' in valid_spalten:
                                            # Salt generieren und Passwort hashen
                                            salt = generate_salt()
                                            password = values.get('Password_hash', '')
                                            password_hash = hash_password(password, salt)

                                            # Werte aktualisieren
                                            values['Password_hash'] = password_hash
                                            values['salt'] = salt
                                            if 'salt' not in valid_spalten:
                                                valid_spalten.append('salt')

                                        placeholders = ", ".join([f":{col}" for col in valid_spalten])
                                        query = text(f"INSERT INTO {table_choice} ({', '.join(valid_spalten)}) VALUES ({placeholders})")
                                        result = conn.execute(query, values)

                                        # Wenn es sich um ein Ticket handelt, automatische Beziehungen erstellen
                                        if table_choice == "ticket":
                                            ticket_id = result.lastrowid
                                            ID_Mitarbeiter = values.get("ID_Mitarbeiter")

                                            # Standard-Kategorie (ID 1) verwenden
                                            create_ticket_relations(ticket_id, ID_Mitarbeiter, 1)

                                        success_count += 1
                                    except Exception as e:
                                        error_count += 1
                                        st.error(f"Fehler beim Einfügen von Zeile {_+1}: {str(e)}")

                            if success_count > 0:
                                st.success(f"✅ {success_count} Datensätze erfolgreich eingefügt!")
                                # Leeren DataFrame für neue Eingaben erstellen
                                empty_df = pd.DataFrame(columns=spalten)
                                empty_row = {col: "" for col in spalten}
                                # Spezielle Behandlung für Datum/Zeit-Spalten
                                for col in spalten:
                                    if 'date' in col.lower() or 'time' in col.lower() or 'erstellt' in col.lower():
                                        empty_row[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                empty_df = pd.concat([empty_df, pd.DataFrame([empty_row])], ignore_index=True)
                                st.session_state["multi_insert_df"] = empty_df
                                st.rerun()

                            if error_count > 0:
                                st.warning(f"⚠️ {error_count} Datensätze konnten nicht eingefügt werden.")

                        except Exception as e:
                            st.error(f"❌ Fehler beim Einfügen der Datensätze: {str(e)}")

        except Exception as e:
            st.error("❌ Fehler beim Einfügen:")
            st.exception(e)

    # -----------------------------
    # ❌ Tab 4: Löschen
    # -----------------------------
    with tab4:
        st.subheader("Datensatz löschen")

        try:
            tabellen = inspector.get_table_names()
            table_choice_delete = st.selectbox("Tabelle wählen (Löschen)", tabellen, key="delete_table")
            spalten_delete = get_columns(table_choice_delete)
            id_spalte_delete = st.selectbox("Primärschlüsselspalte", spalten_delete, key="primary_column_delete")

            if st.button("🔄 Daten zum Löschen laden"):
                df_delete = pd.read_sql(f"SELECT * FROM {table_choice_delete}", con=engine)
                st.dataframe(df_delete, use_container_width=True)

                if not df_delete.empty:
                    selected_id_to_delete = st.selectbox(
                        f"Datensatz zum Löschen auswählen ({id_spalte_delete})",
                        df_delete[id_spalte_delete].tolist()
                    )

                    if st.button("🗑️ Datensatz löschen"):
                        try:
                            with engine.begin() as conn:
                                query = text(f"DELETE FROM {table_choice_delete} WHERE {id_spalte_delete} = :value")
                                result = conn.execute(query, {"value": selected_id_to_delete})

                                if result.rowcount > 0:
                                    st.success(f"✅ Datensatz mit {id_spalte_delete} = {selected_id_to_delete} gelöscht.")
                                else:
                                    st.warning(f"⚠️ Kein Datensatz gelöscht. Möglicherweise wurde er bereits entfernt.")

                            # Daten neu laden
                            df_delete = pd.read_sql(f"SELECT * FROM {table_choice_delete}", con=engine)
                            st.write("Aktualisierte Tabellendaten:")
                            st.dataframe(df_delete)

                        except Exception as e:
                            st.error("❌ Fehler beim Löschen:")
                            st.exception(e)
                else:
                    st.info(f"Keine Daten in der Tabelle {table_choice_delete}.")

        except Exception as e:
            st.error("❌ Fehler beim Laden der Daten zum Löschen:")
            st.exception(e)

# Hauptfunktion aufrufen
if __name__ == "__main__":
    main()