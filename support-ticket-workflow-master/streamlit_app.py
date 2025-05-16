import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

# DB-Zugangsdaten anpassen
DB_USER = "root"
DB_PASSWORD = "Xyz1343!!!"
DB_HOST = "127.0.0.1"
DB_PORT = "3306"
DB_NAME = "ticketsystem02"

# Engine richtig erstellen
engine = create_engine(
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

st.set_page_config(page_title='Support-Ticket-Workflow', page_icon='🎫')
st.title('🎫 Support-Ticket-Workflow')
st.info('Um ein Ticket zu schreiben, fülle das untenstehende Formular aus.')

# Funktion zum Laden der Tickets aus DB
@st.cache_data(ttl=60)
def lade_tickets():
    query = "SELECT * FROM tickets"
    return pd.read_sql(query, engine)

# Daten nur aus DB laden
if 'df' not in st.session_state:
    st.session_state.df = lade_tickets()

tabs = st.tabs(['📨 Ticket schreiben', '📊 Ticketstatus & Auswertungen', 'Datenbank verwalten'])

with tabs[0]:
    with st.form('ticket_formular'):
        sachverhalt = st.text_area('Beschreibung des Problems')
        priorität = st.selectbox('Priorität', ['Hoch', 'Mittel', 'Gering'])
        absenden = st.form_submit_button('Absenden')

    if absenden:
        heutedatum = datetime.now().strftime('%Y-%m-%d')

        # ID generieren: z.B. max ID +1 (angenommen ID ist integer)
        max_id = st.session_state.df['ID'].max() if not st.session_state.df.empty else 0
        neues_ticket = pd.DataFrame([{
            'ID': max_id + 1,
            'Sachverhalt': sachverhalt,
            'Status': 'Offen',
            'Priorität': priorität,
            'Erstellt_am': heutedatum
        }])

        # Speichern in DB
        neues_ticket.to_sql('tickets', con=engine, if_exists='append', index=False)

        st.success('🎉 Ticket erfolgreich gespeichert!')
        st.dataframe(neues_ticket, use_container_width=True, hide_index=True)
        st.session_state.df = lade_tickets()

# Rest deiner Tabs wie gehabt, alle arbeiten mit st.session_state.df
