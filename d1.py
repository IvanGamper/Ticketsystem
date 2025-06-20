import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, inspect, text
from datetime import datetime
from a import (generate_salt, hash_password, get_searchable_columns, search_table, get_column_types)
from t import (create_ticket_relations, get_columns)


# Verbesserte Löschfunktion für die Datenbankverwaltung mit zusätzlichen Abhängigkeiten
def enhanced_delete_function(table_choice_delete, id_spalte_delete, selected_id_to_delete):
    from d import engine

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

# Datenbankverwaltung anzeigen
def show_database_management():
    from d import engine, inspector
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

        # Session-State für den Löschvorgang initialisieren
        if "delete_state" not in st.session_state:
            st.session_state.delete_state = "initial"  # Mögliche Zustände: initial, confirm, executing

        if "delete_table" not in st.session_state:
            st.session_state.delete_table = None

        if "delete_id_column" not in st.session_state:
            st.session_state.delete_id_column = None

        if "delete_id_value" not in st.session_state:
            st.session_state.delete_id_value = None

        if "delete_df" not in st.session_state:
            st.session_state.delete_df = pd.DataFrame()

        if "delete_option" not in st.session_state:
            st.session_state.delete_option = "Standard-Löschung"

        try:
            tabellen = inspector.get_table_names()
            table_choice_delete = st.selectbox("Tabelle wählen (Löschen)", tabellen, key="delete_table_select")
            spalten_delete = get_columns(table_choice_delete)
            id_spalte_delete = st.selectbox("Primärschlüsselspalte", spalten_delete, key="primary_column_delete_select")

            # Daten laden Button
            if st.button("🔄 Daten zum Löschen laden", key="load_delete_data"):
                df_delete = pd.read_sql(f"SELECT * FROM {table_choice_delete}", con=engine)
                st.session_state.delete_df = df_delete
                st.session_state.delete_table = table_choice_delete
                st.session_state.delete_id_column = id_spalte_delete
                st.session_state.delete_state = "initial"
                st.rerun()  # Wichtig: Seite neu laden, um UI-Elemente korrekt anzuzeigen

            # Wenn Daten geladen wurden, zeige sie an
            if not st.session_state.delete_df.empty:
                st.dataframe(st.session_state.delete_df, use_container_width=True)

                # Nur wenn wir nicht im Bestätigungsmodus sind, zeige die Auswahlfelder
                if st.session_state.delete_state == "initial":
                    # ID zum Löschen auswählen
                    selected_id_to_delete = st.selectbox(
                        f"Datensatz zum Löschen auswählen ({st.session_state.delete_id_column})",
                        st.session_state.delete_df[st.session_state.delete_id_column].tolist(),
                        key="delete_id_select"
                    )

                    # Löschoptionen
                    delete_option = st.radio(
                        "Löschmethode wählen:",
                        ["Standard-Löschung", "Erweiterte Löschung (mit Abhängigkeiten)"],
                        key="delete_option_radio",
                        help="Standard-Löschung versucht nur den ausgewählten Datensatz zu löschen. Erweiterte Löschung löscht auch abhängige Datensätze."
                    )

                    # Lösch-Button
                    if st.button("🗑️ Datensatz löschen", key="delete_record_button"):
                        # Werte speichern und in den Bestätigungsmodus wechseln
                        st.session_state.delete_id_value = selected_id_to_delete
                        st.session_state.delete_option = delete_option
                        st.session_state.delete_state = "confirm"
                        st.rerun()  # Wichtig: Seite neu laden, um Bestätigungsdialog anzuzeigen

                # Bestätigungsdialog anzeigen
                elif st.session_state.delete_state == "confirm":
                    st.warning(f"⚠️ Sind Sie sicher, dass Sie den Datensatz mit {st.session_state.delete_id_column} = {st.session_state.delete_id_value} löschen möchten?")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Ja, löschen", key="confirm_delete_button"):
                            st.session_state.delete_state = "executing"
                            st.rerun()  # Wichtig: Seite neu laden, um Löschvorgang auszuführen
                    with col2:
                        if st.button("❌ Abbrechen", key="cancel_delete_button"):
                            st.session_state.delete_state = "initial"
                            st.rerun()  # Zurück zum Ausgangszustand

                # Löschvorgang ausführen
                elif st.session_state.delete_state == "executing":
                    if st.session_state.delete_option == "Standard-Löschung":
                        try:
                            with engine.begin() as conn:
                                query = text(f"DELETE FROM {st.session_state.delete_table} WHERE {st.session_state.delete_id_column} = :value")
                                result = conn.execute(query, {"value": st.session_state.delete_id_value})

                                if result.rowcount > 0:
                                    st.success(f"✅ Datensatz mit {st.session_state.delete_id_column} = {st.session_state.delete_id_value} gelöscht.")
                                    # Daten neu laden
                                    df_delete = pd.read_sql(f"SELECT * FROM {st.session_state.delete_table}", con=engine)
                                    st.session_state.delete_df = df_delete
                                    st.write("Aktualisierte Tabellendaten:")
                                    st.dataframe(df_delete)
                                    # Zurück zum Ausgangszustand
                                    st.session_state.delete_state = "initial"
                                else:
                                    st.warning(f"⚠️ Kein Datensatz gelöscht. Möglicherweise wurde er bereits entfernt.")
                                    st.session_state.delete_state = "initial"

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

                            # Zurück zum Ausgangszustand nach Fehler
                            st.session_state.delete_state = "initial"
                    else:
                        # Erweiterte Löschung mit Abhängigkeiten
                        success = enhanced_delete_function(
                            st.session_state.delete_table,
                            st.session_state.delete_id_column,
                            st.session_state.delete_id_value
                        )

                        if success:
                            # Daten neu laden
                            df_delete = pd.read_sql(f"SELECT * FROM {st.session_state.delete_table}", con=engine)
                            st.session_state.delete_df = df_delete
                            st.write("Aktualisierte Tabellendaten:")
                            st.dataframe(df_delete)

                        # Zurück zum Ausgangszustand
                        st.session_state.delete_state = "initial"
            else:
                st.info("Bitte laden Sie zuerst Daten zum Löschen.")

        except Exception as e:
            st.error("❌ Fehler beim Laden der Daten zum Löschen:")
            st.exception(e)
            # Zurück zum Ausgangszustand nach Fehler
            st.session_state.delete_state = "initial"
