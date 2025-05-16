import streamlit as st
import pandas as pdg
from sqlalchemy import create_engine, text, inspect

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
tab1, tab2, tab3 = st.tabs(["📋 Anzeigen", "➕ Einfügen", "❌ Löschen"])

# Hilfsfunktion: Spaltennamen einer Tabelle
def get_columns(table):
    try:
        return [col["name"] for col in inspector.get_columns(table)]
    except:
        return []

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
# ➕ Tab 2: Einfügen
# -----------------------------
with tab2:
    st.subheader("Datensatz einfügen")
    try:
        tabellen = inspector.get_table_names()
        table_choice = st.selectbox("Tabelle wählen (Einfügen)", tabellen, key="insert_table")
        spalten = get_columns(table_choice)

        inputs = {}
        for spalte in spalten:
            inputs[spalte] = st.text_input(f"{spalte}", key=f"insert_{spalte}")

        if st.button("💾 Einfügen"):
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
# ❌ Tab 3: Löschen
# -----------------------------
with tab3:
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
