import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from ticket_search import TicketSearch

# DB-Konfiguration
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystemabkoo"

# SQLAlchemy Engine
engine = create_engine(f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
inspector = inspect(engine)

# Seiteneinstellungen
st.set_page_config(page_title="Ticket-Suchfunktion Test", page_icon="🔍", layout="wide")
st.title("🔍 Test der Ticket-Suchfunktion")

# Simuliere angemeldeten Benutzer für Testzwecke
if "user_id" not in st.session_state:
    st.session_state.user_id = 1  # Beispiel-ID

if "username" not in st.session_state:
    st.session_state.username = "Test-Benutzer"  # Beispiel-Name

# Suchfunktion initialisieren
ticket_search = TicketSearch(engine, inspector)

# Suchfunktion ausführen
st.header("Ticketübersicht")
selected_ticket_id = ticket_search.run_search(
    user_id=st.session_state.user_id,
    username=st.session_state.username
)

# Feedback-Bereich
st.markdown("---")
st.subheader("Testfeedback")
st.info("""
Diese Seite demonstriert die extrahierte Suchfunktion als eigenständiges Modul.
Die Suchfunktion wurde vollständig aus dem Ticketsystem extrahiert und kann in beliebige Streamlit-Anwendungen integriert werden.

**Funktionen:**
- Suchfeld mit Dropdown zur Feldauswahl
- Filter für Status, Priorität und Mitarbeiter
- Anzeige der Suchergebnisse in einer Tabelle
- Detailansicht für ausgewählte Tickets
- Kommentarfunktion (wenn Benutzer-ID und Name übergeben werden)

**Hinweis:** Die Datenbankverbindung muss separat konfiguriert werden.
""")
