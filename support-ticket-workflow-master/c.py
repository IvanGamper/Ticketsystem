import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timedelta
##import altair as alt
##import hashlib
import secrets
import time
##import string
##import random
##import smtplib
##from email.mime.text import MIMEText
##from email.mime.multipart import MIMEMultipart
from x import (
    generate_salt,
    hash_password,
    verify_password,
    generate_temp_password,
    authenticate_user
)


# DB-Konfiguration
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystemabkoo_copy"

# SQLAlchemy Engine
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

inspector = inspect(engine)



# Verbesserte Löschfunktion für die Datenbankverwaltung mit zusätzlichen Abhängigkeiten
def enhanced_delete_function(table_choice_delete, id_spalte_delete, selected_id_to_delete):
    """
    Verbesserte Löschfunktion, die Fremdschlüsselbeziehungen berücksichtigt
    und abhängige Datensätze in der richtigen Reihenfolge löscht.

    Args:
        table_choice_delete: Name der Tabelle
        id_spalte_delete: Name der ID-Spalte
        selected_id_to_delete: Wert der ID des zu löschenden Datensatzes
    """
    try:
        # Prüfen, ob es sich um eine Tabelle mit bekannten Abhängigkeiten handelt
        if table_choice_delete == "ticket":
            # Für Tickets müssen zuerst alle abhängigen Datensätze gelöscht werden
            with engine.begin() as conn:
                # 1. Ticket-Kommentare löschen
                delete_comments_query = text("""
                    DELETE FROM ticket_kommentar 
                    WHERE ID_Ticket = :ticket_id
                """)
                conn.execute(delete_comments_query, {"ticket_id": selected_id_to_delete})

                # 2. Ticket-Historie löschen
                delete_history_query = text("""
                    DELETE FROM ticket_historie 
                    WHERE ID_Ticket = :ticket_id
                """)
                conn.execute(delete_history_query, {"ticket_id": selected_id_to_delete})

                # 3. Ticket-Mitarbeiter-Zuordnungen löschen
                delete_mitarbeiter_query = text("""
                    DELETE FROM ticket_mitarbeiter 
                    WHERE ID_Ticket = :ticket_id
                """)
                conn.execute(delete_mitarbeiter_query, {"ticket_id": selected_id_to_delete})

                # 4. Ticket-Kategorie-Zuordnungen löschen
                delete_kategorie_query = text("""
                    DELETE FROM ticket_kategorie 
                    WHERE ID_Ticket = :ticket_id
                """)
                conn.execute(delete_kategorie_query, {"ticket_id": selected_id_to_delete})

                # 5. Schließlich das Ticket selbst löschen
                delete_ticket_query = text("""
                    DELETE FROM ticket 
                    WHERE ID_Ticket = :ticket_id
                """)
                conn.execute(delete_ticket_query, {"ticket_id": selected_id_to_delete})

                st.success(f"✅ Ticket #{selected_id_to_delete} wurde erfolgreich gelöscht!")

        elif table_choice_delete == "mitarbeiter":
            # Für Mitarbeiter müssen zuerst alle abhängigen Datensätze gelöscht werden
            with engine.begin() as conn:
                # 1. Ticket-Mitarbeiter-Zuordnungen löschen
                delete_ticket_mitarbeiter_query = text("""
                    DELETE FROM ticket_mitarbeiter 
                    WHERE ID_Mitarbeiter = :mitarbeiter_id
                """)
                conn.execute(delete_ticket_mitarbeiter_query, {"mitarbeiter_id": selected_id_to_delete})

                # 2. Ticket-Historie-Einträge aktualisieren (auf NULL setzen statt löschen)
                update_historie_query = text("""
                    UPDATE ticket_historie 
                    SET Geändert_von = NULL
                    WHERE Geändert_von = :mitarbeiter_id
                """)
                conn.execute(update_historie_query, {"mitarbeiter_id": selected_id_to_delete})

                # 3. Tickets aktualisieren (auf NULL setzen statt löschen)
                update_tickets_query = text("""
                    UPDATE ticket 
                    SET ID_Mitarbeiter = NULL
                    WHERE ID_Mitarbeiter = :mitarbeiter_id
                """)
                conn.execute(update_tickets_query, {"mitarbeiter_id": selected_id_to_delete})

                # 4. Kommentare aktualisieren (auf NULL setzen statt löschen)
                update_kommentare_query = text("""
                    UPDATE ticket_kommentar 
                    SET ID_Mitarbeiter = NULL
                    WHERE ID_Mitarbeiter = :mitarbeiter_id
                """)
                conn.execute(update_kommentare_query, {"mitarbeiter_id": selected_id_to_delete})

                # 5. Schließlich den Mitarbeiter selbst löschen
                delete_mitarbeiter_query = text("""
                    DELETE FROM mitarbeiter 
                    WHERE ID_Mitarbeiter = :mitarbeiter_id
                """)
                conn.execute(delete_mitarbeiter_query, {"mitarbeiter_id": selected_id_to_delete})

                st.success(f"✅ Mitarbeiter mit ID {selected_id_to_delete} wurde erfolgreich gelöscht!")

        elif table_choice_delete == "kunde":
            # Für Kunden müssen zuerst alle abhängigen Tickets aktualisiert werden
            with engine.begin() as conn:
                # 1. Tickets aktualisieren (auf NULL setzen statt löschen)
                update_tickets_query = text("""
                    UPDATE ticket 
                    SET ID_Kunde = NULL
                    WHERE ID_Kunde = :kunde_id
                """)
                conn.execute(update_tickets_query, {"kunde_id": selected_id_to_delete})

                # 2. Schließlich den Kunden selbst löschen
                delete_kunde_query = text("""
                    DELETE FROM kunde 
                    WHERE ID_Kunde = :kunde_id
                """)
                conn.execute(delete_kunde_query, {"kunde_id": selected_id_to_delete})

                st.success(f"✅ Kunde mit ID {selected_id_to_delete} wurde erfolgreich gelöscht!")

        elif table_choice_delete == "kategorie":
            # Für Kategorien müssen zuerst alle abhängigen Ticket-Kategorie-Zuordnungen gelöscht werden
            with engine.begin() as conn:
                # 1. Ticket-Kategorie-Zuordnungen löschen
                delete_ticket_kategorie_query = text("""
                    DELETE FROM ticket_kategorie 
                    WHERE ID_Kategorie = :kategorie_id
                """)
                conn.execute(delete_ticket_kategorie_query, {"kategorie_id": selected_id_to_delete})

                # 2. Schließlich die Kategorie selbst löschen
                delete_kategorie_query = text("""
                    DELETE FROM kategorie 
                    WHERE ID_Kategorie = :kategorie_id
                """)
                conn.execute(delete_kategorie_query, {"kategorie_id": selected_id_to_delete})

                st.success(f"✅ Kategorie mit ID {selected_id_to_delete} wurde erfolgreich gelöscht!")

        elif table_choice_delete == "status":
            # Für Status müssen zuerst alle abhängigen Tickets aktualisiert werden
            with engine.begin() as conn:
                # 1. Tickets aktualisieren (auf NULL setzen statt löschen)
                update_tickets_query = text("""
                    UPDATE ticket 
                    SET ID_Status = NULL
                    WHERE ID_Status = :status_id
                """)
                conn.execute(update_tickets_query, {"status_id": selected_id_to_delete})

                # 2. Schließlich den Status selbst löschen
                delete_status_query = text("""
                    DELETE FROM status 
                    WHERE ID_Status = :status_id
                """)
                conn.execute(delete_status_query, {"status_id": selected_id_to_delete})

                st.success(f"✅ Status mit ID {selected_id_to_delete} wurde erfolgreich gelöscht!")

        elif table_choice_delete == "rolle":
            # Für Rollen müssen zuerst alle abhängigen Mitarbeiter aktualisiert werden
            with engine.begin() as conn:
                # 1. Mitarbeiter aktualisieren (auf NULL setzen statt löschen)
                update_mitarbeiter_query = text("""
                    UPDATE mitarbeiter 
                    SET ID_Rolle = NULL
                    WHERE ID_Rolle = :rolle_id
                """)
                conn.execute(update_mitarbeiter_query, {"rolle_id": selected_id_to_delete})

                # 2. Schließlich die Rolle selbst löschen
                delete_rolle_query = text("""
                    DELETE FROM rolle 
                    WHERE ID_Rolle = :rolle_id
                """)
                conn.execute(delete_rolle_query, {"rolle_id": selected_id_to_delete})

                st.success(f"✅ Rolle mit ID {selected_id_to_delete} wurde erfolgreich gelöscht!")

        else:
            # Für andere Tabellen den normalen Löschvorgang durchführen
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

        return True

    except Exception as e:
        st.error("❌ Fehler beim Löschen:")
        st.exception(e)

        # Detaillierte Fehlermeldung für Fremdschlüsselprobleme
        error_str = str(e)
        if "foreign key constraint fails" in error_str.lower():
            st.error("""
            **Fremdschlüssel-Constraint-Fehler erkannt!**
            
            Der Datensatz kann nicht gelöscht werden, da er noch von anderen Tabellen referenziert wird.
            Bitte überprüfen Sie alle abhängigen Tabellen und aktualisieren Sie die enhanced_delete_function.
            """)

            # Versuche, die betroffene Tabelle zu identifizieren
            if "CONSTRAINT" in error_str and "FOREIGN KEY" in error_str:
                st.error(f"""
                Fehlerdetails: {error_str}
                
                Bitte fügen Sie eine spezielle Behandlung für diese Tabelle in der enhanced_delete_function hinzu.
                """)

        return False



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
    if app_mode == "Datenbankverwaltung":
        show_database_management()


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

                    # Löschoptionen
                    delete_option = st.radio(
                        "Löschmethode wählen:",
                        ["Standard-Löschung", "Erweiterte Löschung (mit Abhängigkeiten)"],
                        help="Standard-Löschung versucht nur den ausgewählten Datensatz zu löschen. Erweiterte Löschung löscht auch abhängige Datensätze."
                    )

                    # WICHTIG: Dieser Button muss AUSSERHALB der if-Bedingung für "Daten zum Löschen laden" sein
                    delete_button = st.button("🗑️ Datensatz löschen")

                    if delete_button:
                        if delete_option == "Standard-Löschung":
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

                                # Detaillierte Fehlermeldung für Fremdschlüsselprobleme
                                error_str = str(e)
                                if "foreign key constraint fails" in error_str.lower():
                                    st.error("""
                                    **Fremdschlüssel-Constraint-Fehler erkannt!**
                                    
                                    Der Datensatz kann nicht gelöscht werden, da er noch von anderen Tabellen referenziert wird.
                                    Bitte verwenden Sie die 'Erweiterte Löschung' Option oder löschen Sie zuerst alle abhängigen Datensätze.
                                    """)
                        else:
                            # Erweiterte Löschung mit Abhängigkeiten
                            enhanced_delete_function(table_choice_delete, id_spalte_delete, selected_id_to_delete)
                else:
                    st.info(f"Keine Daten in der Tabelle {table_choice_delete}.")

        except Exception as e:
            st.error("❌ Fehler beim Laden der Daten zum Löschen:")
            st.exception(e)






