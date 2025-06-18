# Ticketsystem anzeigen
def show_ticket_system():
    st.title("🎫 Ticketsystem")

    # Tabs für verschiedene Funktionen
    ticket_tabs = st.tabs(["📋 Ticketübersicht", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"])

    # Tab: Ticketübersicht
    with ticket_tabs[0]:
        show_ticket_overview()

    # Tab: Neues Ticket
    with ticket_tabs[1]:
        show_new_ticket_form()

    # Tab: Statistiken
    with ticket_tabs[2]:
        show_ticket_statistics()

    # Tab: Einstellungen
    with ticket_tabs[3]:
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
                🧑‍💼 Durch: *{eintrag.Geaendert_von}* am *{eintrag.Geaendert_am}*
                """)
def show_edit_ticket_form(ticket_id):
    st.subheader("✏️ Ticket bearbeiten")

    # Aktuelle Daten laden
    query = """
    SELECT * FROM ticket WHERE ID_Ticket = :ticket_id
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), {"ticket_id": ticket_id})
            ticket = result.fetchone()
    except Exception as e:
        st.error(f"Fehler beim Abrufen des Tickets: {str(e)}")
        return

    if not ticket:
        st.warning("Ticket nicht gefunden.")
        return

    # Auswahloptionen laden
    status_df = pd.read_sql("SELECT ID_Status, Name FROM status", con=engine)
    kunde_df = pd.read_sql("SELECT ID_Kunde, Name FROM kunde", con=engine)
    mitarbeiter_df = pd.read_sql("SELECT ID_Mitarbeiter, Name FROM mitarbeiter", con=engine)

    # Formular anzeigen
    with st.form(f"edit_ticket_form_{ticket_id}"):
        titel = st.text_input("Titel", value=ticket.Titel)
        beschreibung = st.text_area("Beschreibung", value=ticket.Beschreibung)
        prioritaet = st.selectbox("Priorität", ["Hoch", "Mittel", "Niedrig"], index=["Hoch", "Mittel", "Niedrig"].index(ticket.Priorität))

        status = st.selectbox("Status", status_df["Name"].tolist(), index=status_df["ID_Status"].tolist().index(ticket.ID_Status))
        kunde = st.selectbox("Kunde", kunde_df["Name"].tolist(), index=kunde_df["ID_Kunde"].tolist().index(ticket.ID_Kunde))
        mitarbeiter = st.selectbox("Mitarbeiter", mitarbeiter_df["Name"].tolist(), index=mitarbeiter_df["ID_Mitarbeiter"].tolist().index(ticket.ID_Mitarbeiter))

        submit = st.form_submit_button("Änderungen speichern")

    if submit:
        try:
            ID_Status = status_df[status_df["Name"] == status]["ID_Status"].values[0]
            ID_Kunde = kunde_df[kunde_df["Name"] == kunde]["ID_Kunde"].values[0]
            ID_Mitarbeiter = mitarbeiter_df[mitarbeiter_df["Name"] == mitarbeiter]["ID_Mitarbeiter"].values[0]

            changes = []

            def check_change(field_name, old, new):
                if old != new:
                    changes.append({
                        "Feldname": field_name,
                        "Alter_Wert": str(old),
                        "Neuer_Wert": str(new)
                    })

            # Änderungen vergleichen
            check_change("Titel", ticket.Titel, titel)
            check_change("Beschreibung", ticket.Beschreibung, beschreibung)
            check_change("Priorität", ticket.Priorität, prioritaet)
            check_change("ID_Status", ticket.ID_Status, ID_Status)
            check_change("ID_Kunde", ticket.ID_Kunde, ID_Kunde)
            check_change("ID_Mitarbeiter", ticket.ID_Mitarbeiter, ID_Mitarbeiter)

            if changes:
                with engine.begin() as conn:
                    update_query = text("""
                        UPDATE ticket
                        SET Titel = :titel,
                            Beschreibung = :beschreibung,
                            Priorität = :prioritaet,
                            ID_Status = :status,
                            ID_Kunde = :kunde,
                            ID_Mitarbeiter = :mitarbeiter,
                            Geändert_am = NOW()
                        WHERE ID_Ticket = :ticket_id
                    """)
                    conn.execute(update_query, {
                        "titel": titel,
                        "beschreibung": beschreibung,
                        "prioritaet": prioritaet,
                        "status": ID_Status,
                        "kunde": ID_Kunde,
                        "mitarbeiter": ID_Mitarbeiter,
                        "ticket_id": ticket_id
                    })

                    # Historie loggen
                    for change in changes:
                        insert_log = text("""
                            INSERT INTO ticket_historie (ID_Ticket, Feldname, Alter_Wert, Neuer_Wert, Geaendert_von, Geaendert_am)
                            VALUES (:ticket_id, :feld, :alt, :neu, :bearbeiter, NOW())
                        """)
                        conn.execute(insert_log, {
                            "ticket_id": ticket_id,
                            "feld": change["Feldname"],
                            "alt": change["Alter_Wert"],
                            "neu": change["Neuer_Wert"],
                            "bearbeiter": st.session_state.user_id
                        })

                st.success("Änderungen erfolgreich gespeichert.")
                st.rerun()
            else:
                st.info("Keine Änderungen erkannt.")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {str(e)}")


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
                            VALUES (:name, :email, :password_hash, :salt, 0)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "email": email,
                                "password_hash": password_hash,
                                "salt": salt
                            })

                        st.success("Mitarbeiter erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Mitarbeiters: {str(e)}")

    # Tab: Kunden
    with settings_tabs[1]:
        st.subheader("Kunden verwalten")

        # Kunden anzeigen
        kunde_df = pd.read_sql("SELECT * FROM kunde ORDER BY Name", con=engine)
        st.dataframe(kunde_df, use_container_width=True)

        # Neuen Kunden hinzufügen
        with st.expander("Neuen Kunden hinzufügen"):
            with st.form(key="add_kunde_form"):
                name = st.text_input("Name")
                kontaktperson = st.text_input("Kontaktperson")
                email = st.text_input("E-Mail")
                telefon = st.text_input("Telefon")

                submit_kunde = st.form_submit_button("Kunde hinzufügen")

            if submit_kunde:
                if not name:
                    st.error("Bitte geben Sie einen Namen ein.")
                else:
                    try:
                        with engine.begin() as conn:
                            insert_query = text("""
                            INSERT INTO kunde (Name, Email, Kontaktperson, Telefon)
                            VALUES (:name, :email, :kontaktperson, :telefon)
                            """)
                            conn.execute(insert_query, {
                                "name": name,
                                "email": email,
                                "kontaktperson": kontaktperson,
                                "telefon": telefon
                            })

                        st.success("Kunde erfolgreich hinzugefügt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Hinzufügen des Kunden: {str(e)}")

    # Tab: Kategorien
    with settings_tabs[2]:
        st.subheader("Kategorien verwalten")

        # Kategorien anzeigen
        kategorien_df = pd.read_sql("SELECT * FROM kategorie ORDER BY Name", con=engine)
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

    # Tab: Status
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
