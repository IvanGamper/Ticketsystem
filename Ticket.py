import streamlit as st
from sqlalchemy import text
import time

def create_ticket_relations(ticket_id, ID_Mitarbeiter, kategorie_id=1):
    from Main import engine
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

# Diese Funktion fügt einen Lösch-Button zum Ticket-Details-Bereich hinzu
def add_ticket_delete_button(ticket_id):

    from Main import engine

    """
    Fügt einen Lösch-Button für ein Ticket hinzu und implementiert die Löschlogik.

    Args:
        ticket_id: Die ID des zu löschenden Tickets
    """
    # Lösch-Button mit Warnfarbe
    col1, col2 = st.columns([3, 1])
    with col2:
        delete_button = st.button("🗑️ Ticket löschen", type="primary", use_container_width=True, key=f"delete_ticket_{ticket_id}")

    # if delete_button:
        # Store information in session state to trigger step-by-step deletion
        st.session_state.delete_state = "step_by_step"  # Indicate that step-by-step deletion should start
        st.session_state.delete_table = "ticket"
        st.session_state.delete_id_column = "ID_Ticket"
        st.session_state.delete_id_value = ticket_id
        st.session_state.delete_step = 0  # Reset step for new process
        st.rerun()

    # Helper function to execute SQL queries
def _execute_sql_query(conn, query_str, params=None):
    """
    Executes a given SQL query with optional parameters.
    Args:
        conn: The SQLAlchemy connection object.
        query_str: The SQL query string.
        params: A dictionary of parameters for the query.
    Returns:
        The result of the execution.
    """
    return conn.execute(text(query_str), params or {})

def execute_delete_step(table_choice_delete, id_spalte_delete,
                        selected_id_to_delete, step):
    """
    Executes a single deletion step based on the table and step number.
    Args:
        table_choice_delete: Name of the table.
        id_spalte_delete: Name of the ID column.
        selected_id_to_delete: Value of the ID of the record to be deleted.
        step: Current step in the deletion process.
    Returns:
        bool: True on success, False on error.
    """
    from Main import engine  # Import engine here to ensure it's available
    try:
        with engine.begin() as conn:
            query_map = {
                "ticket": {
                    0: ("DELETE FROM ticket_kommentar WHERE ID_Ticket = :ticket_id",
                        {"ticket_id": selected_id_to_delete}),
                    1: ("DELETE FROM ticket_historie WHERE ID_Ticket = :ticket_id",
                        {"ticket_id": selected_id_to_delete}),
                    2: ("DELETE FROM ticket_mitarbeiter WHERE ID_Ticket = :ticket_id",
                        {"ticket_id": selected_id_to_delete}),
                    3: ("DELETE FROM ticket_kategorie WHERE ID_Ticket = :ticket_id",
                        {"ticket_id": selected_id_to_delete}),
                    4: ("DELETE FROM ticket WHERE ID_Ticket = :ticket_id",
                        {"ticket_id": selected_id_to_delete}),
                },
                "mitarbeiter": {
                    0: ("DELETE FROM ticket_mitarbeiter WHERE ID_Mitarbeiter "
                        "= :mitarbeiter_id", {"mitarbeiter_id": selected_id_to_delete}),
                    1: ("UPDATE ticket_historie SET Geändert_von = NULL WHERE "
                        "Geändert_von = :mitarbeiter_id", {"mitarbeiter_id": selected_id_to_delete}),
                    2: ("UPDATE ticket SET ID_Mitarbeiter = NULL WHERE ID_Mitarbeiter "
                        "= :mitarbeiter_id", {"mitarbeiter_id": selected_id_to_delete}),
                    3: ("UPDATE ticket_kommentar SET ID_Mitarbeiter = NULL WHERE "
                        "ID_Mitarbeiter = :mitarbeiter_id", {"mitarbeiter_id": selected_id_to_delete}),
                    4: ("DELETE FROM mitarbeiter WHERE ID_Mitarbeiter = :mitarbeiter_id",
                        {"mitarbeiter_id": selected_id_to_delete}),
                },
                "kunde": {
                    0: ("UPDATE ticket SET ID_Kunde = NULL WHERE ID_Kunde = :kunde_id",
                        {"kunde_id": selected_id_to_delete}),
                    1: ("DELETE FROM kunde WHERE ID_Kunde = :kunde_id",
                        {"kunde_id": selected_id_to_delete}),
                },
                "kategorie": {
                    0: ("DELETE FROM ticket_kategorie WHERE ID_Kategorie "
                        "= :kategorie_id", {"kategorie_id": selected_id_to_delete}),
                    1: ("DELETE FROM kategorie WHERE ID_Kategorie = :kategorie_id",
                        {"kategorie_id": selected_id_to_delete}),
                },
                "status": {
                    0: ("UPDATE ticket SET ID_Status = NULL WHERE ID_Status = :status_id",
                        {"status_id": selected_id_to_delete}),
                    1: ("DELETE FROM status WHERE ID_Status = :status_id",
                        {"status_id": selected_id_to_delete}),
                },
                "rolle": {
                    0: ("UPDATE mitarbeiter SET ID_Rolle = NULL WHERE ID_Rolle "
                        "= :rolle_id", {"rolle_id": selected_id_to_delete}),
                    1: ("DELETE FROM rolle WHERE ID_Rolle = :rolle_id",
                        {"rolle_id": selected_id_to_delete}),
                },
            }

            if table_choice_delete in query_map and step in \
                    query_map[table_choice_delete]:
                query_str, params = query_map[table_choice_delete][step]
                _execute_sql_query(conn, query_str, params)
            else:
                # Default case for other tables
                query_str = f"DELETE FROM {table_choice_delete} WHERE " \
                            f"{id_spalte_delete} = :value"
                _execute_sql_query(conn, query_str, {"value": selected_id_to_delete})

            return True
    except Exception as e:
        st.error(f" Fehler beim Ausführen des Schritts: {str(e)}")
        # Detaillierte Fehlermeldung für Fremdschlüsselprobleme
        error_str = str(e)
        if "foreign key constraint fails" in error_str.lower():
            st.error("""
**Fremdschlüssel-Constraint-Fehler erkannt!**
Der Datensatz kann nicht gelöscht werden, da er noch von anderen Tabellen
referenziert wird.
Bitte überprüfen Sie alle abhängigen Tabellen.
""")
            if "CONSTRAINT" in error_str and "FOREIGN KEY" in error_str:
                st.error(f"""
Fehlerdetails: {error_str}
""")
        return False

    # Initialisierung der Session-State-Variablen für den schrittweisen Löschvorgang
    if "delete_step" not in st.session_state:
        st.session_state.delete_step = 0

    if "delete_steps_total" not in st.session_state:
        st.session_state.delete_steps_total = 1  # Standardwert, wird später aktualisiert

    if "delete_steps_info" not in st.session_state:
        st.session_state.delete_steps_info = []  # Liste mit Informationen zu jedem Schritt

    # Bestimme die Anzahl und Art der Löschschritte basierend auf der Tabelle
    if st.session_state.delete_step == 0:
        # Define deletion steps for each table in a structured way
        deletion_configs = {
            "ticket": {
                "total": 5,
                "info": [
                    {"name": "Ticket-Kommentare", "description": "Löscht alle Kommentare "
                                                                 "zu diesem Ticket"},
                    {"name": "Ticket-Historie", "description": "Löscht alle Historieneinträge "
                                                               "zu diesem Ticket"},
                    {"name": "Ticket-Mitarbeiter-Zuordnungen", "description": "Löscht alle "
                                                                              "Mitarbeiterzuordnungen zu diesem Ticket"},
                    {"name": "Ticket-Kategorie-Zuordnungen", "description": "Löscht alle "
                                                                            "Kategoriezuordnungen zu diesem Ticket"},
                    {"name": "Ticket", "description": "Löscht das Ticket selbst"}
                ]
            },
            "mitarbeiter": {
                "total": 5,
                "info": [
                    {"name": "Ticket-Mitarbeiter-Zuordnungen", "description": "Löscht alle "
                                                                              "Zuordnungen dieses Mitarbeiters zu Tickets"},
                    {"name": "Ticket-Historie-Einträge", "description": "Setzt Mitarbeiter-"
                                                                        "Referenzen in der Historie auf NULL"},
                    {"name": "Tickets", "description": "Setzt Mitarbeiter-Referenzen in "
                                                       "Tickets auf NULL"},
                    {"name": "Kommentare", "description": "Setzt Mitarbeiter-Referenzen in "
                                                          "Kommentaren auf NULL"},
                    {"name": "Mitarbeiter", "description": "Löscht den Mitarbeiter selbst"}
                ]
            },
            "kunde": {
                "total": 2,
                "info": [
                    {"name": "Tickets", "description": "Setzt Kunden-Referenzen in Tickets "
                                                       "auf NULL"},
                    {"name": "Kunde", "description": "Löscht den Kunden selbst"}
                ]
            },
            "kategorie": {
                "total": 2,
                "info": [
                    {"name": "Ticket-Kategorie-Zuordnungen", "description": "Löscht alle "
                                                                            "Zuordnungen dieser Kategorie zu Tickets"},
                    {"name": "Kategorie", "description": "Löscht die Kategorie selbst"}
                ]
            },
            "status": {
                "total": 2,
                "info": [
                    {"name": "Tickets", "description": "Setzt Status-Referenzen in Tickets auf "
                                                       "NULL"},
                    {"name": "Status", "description": "Löscht den Status selbst"}
                ]
            },
            "rolle": {
                "total": 2,
                "info": [
                    {"name": "Mitarbeiter", "description": "Setzt Rollen-Referenzen bei "
                                                           "Mitarbeitern auf NULL"},
                    {"name": "Rolle", "description": "Löscht die Rolle selbst"}
                ]
            },
        }
        config = deletion_configs.get(table_choice_delete, {
            "total": 1,
            "info": [{
                "name": table_choice_delete,
                "description": f"Löscht den Datensatz aus {table_choice_delete}"
            }]
        })
        st.session_state.delete_steps_total = config["total"]
        st.session_state.delete_steps_info = config["info"]

    # Fortschrittsanzeige
    progress_percentage = (st.session_state.delete_step /
                           st.session_state.delete_steps_total) * 100
    st.progress(progress_percentage / 100)
    st.write(f"Schritt {st.session_state.delete_step + 1} von "
             f"{st.session_state.delete_steps_total}")

    # Wenn alle Schritte abgeschlossen sind, zurücksetzen und Erfolg melden
    if st.session_state.delete_step >= st.session_state.delete_steps_total:
        st.success(f" Alle Löschschritte für {table_choice_delete} mit ID "
                   f"{selected_id_to_delete} wurden erfolgreich abgeschlossen!")

        # Daten neu laden
        df_delete = pd.read_sql(f"SELECT * FROM {table_choice_delete}", con=engine)
        st.write("Aktualisierte Tabellendaten:")
        st.dataframe(df_delete)

        # Session-State zurücksetzen
        st.session_state.delete_step = 0
        return True

    # Aktuellen Schritt anzeigen
    current_step_info = \
        st.session_state.delete_steps_info[st.session_state.delete_step]
    st.subheader(f"Schritt {st.session_state.delete_step + 1}: "
                 f"{current_step_info["name"]}")
    st.info(current_step_info["description"])

    # Bestätigungsdialog für den aktuellen Schritt
    st.warning(f"▲ Möchten Sie diesen Schritt ausführen? Diese Aktion kann nicht "
               f"rückgängig gemacht werden!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(" Ja, ausführen",
                     key=f"confirm_step_{st.session_state.delete_step}"):
            # Führe den aktuellen Löschschritt aus
            success = execute_delete_step(
                table_choice_delete,
                id_spalte_delete,
                selected_id_to_delete,
                st.session_state.delete_step
            )
            if success:
                st.success(f" Schritt {st.session_state.delete_step + 1} erfolgreich "
                           f"ausgeführt!")
                # Zum nächsten Schritt
                st.session_state.delete_step += 1
                st.rerun()
            else:
                st.error(" Fehler beim Ausführen des Schritts!")
                # Schritt nicht erhöhen, damit der Benutzer es erneut versuchen kann
    with col2:
        if st.button(" Überspringen", key=f"skip_step_{st.session_state.delete_step}"):
            st.info(f"Schritt {st.session_state.delete_step + 1} übersprungen.")
            # Zum nächsten Schritt ohne Ausführung
            st.session_state.delete_step += 1
            st.rerun()

    # Option zum Abbrechen des gesamten Löschvorgangs
    if st.button(" Gesamten Löschvorgang abbrechen", key="cancel_all_delete"):
        st.warning("Löschvorgang abgebrochen.")
        # Session-State zurücksetzen
        st.session_state.delete_step = 0
        return False

    return None  # Noch nicht abgeschlossen

# Hilfsfunktion: Spaltennamen einer Tabelle
def get_columns(table):

    from Main import engine, inspector

    try:
        return [col["name"] for col in inspector.get_columns(table)]
    except:
        return []

#Hilfsfunktion Historie
def log_ticket_change(ticket_id, feldname, alter_wert, neuer_wert, mitarbeiter_id):

    from Main import engine

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
