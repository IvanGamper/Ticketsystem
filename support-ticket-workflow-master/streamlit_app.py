import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime
import traceback

# DB-Konfiguration
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystem02"

# SQLAlchemy Engine
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

inspector = inspect(engine)

st.title("🛠️ Datenbankverwaltung")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📋 Anzeigen", "✏️ Bearbeiten", "➕ Einfügen", "❌ Löschen"])

# Hilfsfunktion: Spaltennamen einer Tabelle
def get_columns(table):
    try:
        return [col["name"] for col in inspector.get_columns(table)]
    except:
        return []

# Hilfsfunktion: Spaltentypen einer Tabelle
def get_column_types(table):
    try:
        return {col["name"]: str(col["type"]) for col in inspector.get_columns(table)}
    except:
        return {}

# -----------------------------
# 📋 Tab 1: Anzeigen
# -----------------------------
with tab1:
    st.subheader("Tabelle anzeigen")
    try:
        tabellen = inspector.get_table_names()
        table_choice = st.selectbox("Wähle eine Tabelle", tabellen)
        if st.button("🔄 Daten laden"):
            df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)
            st.dataframe(df)
    except Exception as e:
        st.error("❌ Fehler beim Laden:")
        st.exception(e)

# -----------------------------
# ✏️ Tab 2: Bearbeiten (ohne Session State)
# -----------------------------
with tab2:
    st.subheader("Datensätze bearbeiten (interaktiv)")

    try:
        tabellen = inspector.get_table_names()
        table_choice_edit = st.selectbox("Tabelle wählen (Bearbeiten)", tabellen, key="edit_table_editor")
        spalten = get_columns(table_choice_edit)
        id_spalte = st.selectbox("Primärschlüsselspalte", spalten, key="primary_column_editor")

        if st.button("🔄 Daten laden (Editiermodus)"):
            df = pd.read_sql(f"SELECT * FROM {table_choice_edit}", con=engine)

            if df.empty:
                st.warning("Diese Tabelle enthält keine Datensätze.")
            else:
                st.markdown("✏️ **Daten bearbeiten – Änderungen werden erst nach dem Speichern übernommen.**")
                edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed", key="editable_df")

                if st.button("💾 Änderungen speichern"):
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
    try:
        tabellen = inspector.get_table_names()
        table_choice = st.selectbox("Tabelle wählen (Einfügen)", tabellen, key="insert_table")
        spalten = get_columns(table_choice)

        with st.form(key="insert_form"):
            st.subheader(f"Neuen Datensatz in '{table_choice}' einfügen")

            inputs = {}
            for spalte in spalten:
                # Spezielle Behandlung für Datum/Zeit-Spalten
                if 'date' in spalte.lower() or 'time' in spalte.lower() or 'erstellt' in spalte.lower():
                    # Aktuelles Datum als Standardwert für Datum/Zeit-Spalten
                    default_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    inputs[spalte] = st.text_input(f"{spalte}", value=default_value, key=f"insert_{spalte}")
                else:
                    inputs[spalte] = st.text_input(f"{spalte}", key=f"insert_{spalte}")

            submit_insert = st.form_submit_button("💾 Einfügen")

        if submit_insert:
            try:
                with engine.begin() as conn:
                    placeholders = ", ".join([f":{col}" for col in spalten])
                    query = text(f"INSERT INTO {table_choice} ({', '.join(spalten)}) VALUES ({placeholders})")
                    conn.execute(query, {col: inputs[col] for col in spalten})
                st.success(f"✅ Datensatz in '{table_choice}' eingefügt!")
            except Exception as e:
                st.error("❌ Fehler beim Einfügen:")
                st.exception(e)
    except Exception as e:
        st.error("❌ Fehler bei der Tabellenauswahl:")
        st.exception(e)

# -----------------------------
# ❌ Tab 4: Löschen (Korrigierte Version)
# -----------------------------
with tab4:
    st.subheader("Datensatz löschen")
    try:
        tabellen = inspector.get_table_names()
        table_choice = st.selectbox("Tabelle wählen (Löschen)", tabellen, key="delete_table")
        spalten = get_columns(table_choice)

        if not spalten:
            st.warning("Keine Spalten gefunden.")
        else:
            id_spalte = st.selectbox("Primärspalte wählen (z. B. ID)", spalten)
            df = pd.read_sql(f"SELECT * FROM {table_choice}", con=engine)
            df["Anzeigen"] = df[id_spalte].astype(str)
            selected_row = st.selectbox("Datensatz wählen", df["Anzeigen"])

            if st.button("🗑️ Löschen"):
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"DELETE FROM {table_choice} WHERE {id_spalte} = :value"),
                                     {"value": selected_row})
                    st.success(f"✅ Datensatz mit {id_spalte} = {selected_row} gelöscht.")
                except Exception as e:
                    st.error("❌ Fehler beim Löschen:")
                    st.exception(e)
    except Exception as e:
        st.error("❌ Fehler beim Laden:")
        st.exception(e)