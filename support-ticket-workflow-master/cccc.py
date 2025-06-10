import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect, pool
from datetime import datetime, timedelta
import altair as alt
import hashlib
import secrets
import time
import string
import random
import os
from functools import lru_cache
import logging
from simple_email_function import setup_email_system, send_ticket_notification


# Konfiguration für Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ticketsystem')

# DB-Konfiguration aus Umgebungsvariablen oder mit Fallback-Werten
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Xyz1343!!!")
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_NAME = os.environ.get("DB_NAME", "ticketsystemabkoo")

# SQLAlchemy Engine mit Connection-Pooling
engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Inspector für Datenbankmetadaten
inspector = inspect(engine)

# Klasse für Datenbankoperationen
class DatabaseManager:
    @staticmethod
    @lru_cache(maxsize=32)
    def get_columns(table):
        """Gibt die Spaltennamen einer Tabelle zurück (mit Caching)."""
        try:
            return [col["name"] for col in inspector.get_columns(table)]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spalten für Tabelle {table}: {str(e)}")
            return []

    @staticmethod
    @lru_cache(maxsize=32)
    def get_primary_key(table):
        """Ermittelt den Primärschlüssel einer Tabelle (mit Caching)."""
        try:
            pk = inspector.get_pk_constraint(table)
            if pk and 'constrained_columns' in pk and pk['constrained_columns']:
                return pk['constrained_columns'][0]

            # Fallback: Suche nach Spalten mit 'id' im Namen
            columns = DatabaseManager.get_columns(table)
            for col in columns:
                if col.lower() == 'id':
                    return col

            # Zweiter Fallback: Erste Spalte
            if columns:
                return columns[0]
            return None
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln des Primärschlüssels für Tabelle {table}: {str(e)}")
            return None

    @staticmethod
    @lru_cache(maxsize=32)
    def get_column_types(table):
        """Gibt die Spaltentypen einer Tabelle zurück (mit Caching)."""
        try:
            return {col["name"]: str(col["type"]) for col in inspector.get_columns(table)}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Spaltentypen für Tabelle {table}: {str(e)}")
            return {}

    @staticmethod
    @lru_cache(maxsize=32)
    def get_searchable_columns(table):
        """Ermittelt durchsuchbare Spalten einer Tabelle (mit Caching)."""
        try:
            column_types = DatabaseManager.get_column_types(table)
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
            logger.error(f"Fehler beim Ermitteln der durchsuchbaren Spalten für Tabelle {table}: {str(e)}")
            return []

    @staticmethod
    def execute_query(query, params=None, fetch_all=False, commit=False):
        """
        Führt eine SQL-Abfrage aus und gibt das Ergebnis zurück.

        Args:
            query: SQL-Abfrage als Text oder SQLAlchemy-Text-Objekt
            params: Parameter für die Abfrage (dict)
            fetch_all: Ob alle Ergebnisse abgerufen werden sollen (bool)
            commit: Ob ein Commit durchgeführt werden soll (bool)

        Returns:
            Bei fetch_all=True: Liste von Ergebnissen
            Bei fetch_all=False: Einzelnes Ergebnis oder None
            Bei Fehler: None
        """
        try:
            if isinstance(query, str):
                query = text(query)

            params = params or {}

            if commit:
                with engine.begin() as conn:
                    result = conn.execute(query, params)
                    return result
            else:
                with engine.connect() as conn:
                    result = conn.execute(query, params)
                    if fetch_all:
                        return result.fetchall()
                    else:
                        return result.fetchone()
        except Exception as e:
            logger.error(f"Datenbankfehler: {str(e)}")
            if "Lock wait timeout exceeded" in str(e):
                logger.warning("Lock-Timeout aufgetreten, Wiederholung könnte erforderlich sein")
            return None

    @staticmethod
    def execute_query_to_dataframe(query, params=None):
        """
        Führt eine SQL-Abfrage aus und gibt das Ergebnis als DataFrame zurück.

        Args:
            query: SQL-Abfrage als Text oder SQLAlchemy-Text-Objekt
            params: Parameter für die Abfrage (dict)

        Returns:
            pandas.DataFrame: Ergebnis der Abfrage
            Bei Fehler: Leerer DataFrame
        """
        try:
            if isinstance(query, str):
                query = text(query)

            params = params or {}

            with engine.connect() as conn:
                result = conn.execute(query, params)
                columns = result.keys()
                data = result.fetchall()

            return pd.DataFrame(data, columns=columns)
        except Exception as e:
            logger.error(f"Datenbankfehler bei DataFrame-Abfrage: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def search_table(table_name, search_term, search_columns=None, exact_match=False, case_sensitive=False):
        """
        Durchsucht eine Tabelle nach einem Suchbegriff.

        Args:
            table_name: Name der Tabelle
            search_term: Suchbegriff
            search_columns: Zu durchsuchende Spalten (Liste)
            exact_match: Ob exakte Übereinstimmung gefordert ist (bool)
            case_sensitive: Ob Groß-/Kleinschreibung beachtet werden soll (bool)

        Returns:
            pandas.DataFrame: Suchergebnisse
        """
        try:
            if not search_term:
                return pd.DataFrame()

            # Durchsuchbare Spalten ermitteln
            if search_columns is None:
                search_columns = DatabaseManager.get_searchable_columns(table_name)

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
            query = f"SELECT * FROM {table_name} WHERE {where_clause}"

            return DatabaseManager.execute_query_to_dataframe(query, params)

        except Exception as e:
            logger.error(f"Fehler bei der Suche in Tabelle {table_name}: {str(e)}")
            return pd.DataFrame()

    @staticmethod
    def ensure_required_columns_exist():
        """Überprüft, ob die erforderlichen Spalten existieren, und fügt sie hinzu, falls nicht."""
        try:
            # Prüfen, ob die salt-Spalte bereits existiert
            mitarbeiter_columns = DatabaseManager.get_columns("mitarbeiter")

            # Salt-Spalte hinzufügen, falls nicht vorhanden
            if "salt" not in mitarbeiter_columns:
                DatabaseManager.execute_query("ALTER TABLE mitarbeiter ADD COLUMN salt VARCHAR(64)", commit=True)
                # Cache für Spalten zurücksetzen
                DatabaseManager.get_columns.cache_clear()

            # Reset-Token-Spalte hinzufügen, falls nicht vorhanden
            if "reset_token" not in mitarbeiter_columns:
                DatabaseManager.execute_query("ALTER TABLE mitarbeiter ADD COLUMN reset_token VARCHAR(64)", commit=True)
                DatabaseManager.get_columns.cache_clear()

            # Reset-Token-Expiry-Spalte hinzufügen, falls nicht vorhanden
            if "reset_token_expiry" not in mitarbeiter_columns:
                DatabaseManager.execute_query("ALTER TABLE mitarbeiter ADD COLUMN reset_token_expiry DATETIME", commit=True)
                DatabaseManager.get_columns.cache_clear()

            # Password-Change-Required-Spalte hinzufügen, falls nicht vorhanden
            if "password_change_required" not in mitarbeiter_columns:
                DatabaseManager.execute_query("ALTER TABLE mitarbeiter ADD COLUMN password_change_required BOOLEAN DEFAULT FALSE", commit=True)
                DatabaseManager.get_columns.cache_clear()

            return True
        except Exception as e:
            logger.error(f"Fehler beim Überprüfen/Hinzufügen der erforderlichen Spalten: {str(e)}")
            st.error("Fehler beim Überprüfen der Datenbankstruktur. Details im Log.")
            return False

# Klasse für Ticket-Operationen
class TicketManager:
    @staticmethod
    def log_ticket_change(ticket_id, feldname, alter_wert, neuer_wert, mitarbeiter_id):
        """
        Protokolliert eine Änderung an einem Ticket in der Historie.

        Args:
            ticket_id: ID des Tickets
            feldname: Name des geänderten Feldes
            alter_wert: Alter Wert
            neuer_wert: Neuer Wert
            mitarbeiter_id: ID des Mitarbeiters, der die Änderung vorgenommen hat

        Returns:
            bool: Erfolg
        """
        # Typkonvertierung für den Vergleich
        alter_wert_str = str(alter_wert) if alter_wert is not None else ""
        neuer_wert_str = str(neuer_wert) if neuer_wert is not None else ""

        # Nur speichern, wenn sich die Werte tatsächlich unterscheiden
        if alter_wert_str.strip() == neuer_wert_str.strip():
            return True  # Keine Änderung, daher kein Eintrag nötig

        # Kürzere Transaktion mit Wiederholungslogik
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                insert_query = """
                    INSERT INTO ticket_historie (ID_Ticket, Feldname, Alter_Wert, Neuer_Wert, Geändert_von, Geändert_am)
                    VALUES (:ticket_id, :feldname, :alter_wert, :neuer_wert, :geändert_von, NOW())
                """

                DatabaseManager.execute_query(
                    insert_query,
                    {
                        "ticket_id": ticket_id,
                        "feldname": feldname,
                        "alter_wert": alter_wert_str,
                        "neuer_wert": neuer_wert_str,
                        "geändert_von": mitarbeiter_id
                    },
                    commit=True
                )

                # Wenn erfolgreich, Schleife beenden
                return True

            except Exception as e:
                # Nur bei Lock-Timeout-Fehlern wiederholen
                if "Lock wait timeout exceeded" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    time.sleep(0.5)  # Kurze Pause vor dem nächsten Versuch
                else:
                    # Bei anderen Fehlern oder zu vielen Versuchen, Fehler protokollieren
                    logger.error(f"Fehler beim Speichern des Historien-Eintrags: {str(e)}")
                    return False

    @staticmethod
    def create_ticket_relations(ticket_id, ID_Mitarbeiter, kategorie_id=1):
        """
        Erstellt automatische Einträge in ticket_mitarbeiter und ticket_kategorie.

        Args:
            ticket_id: ID des Tickets
            ID_Mitarbeiter: ID des Mitarbeiters
            kategorie_id: ID der Kategorie

        Returns:
            bool: Erfolg
        """
        try:
            # Eintrag in ticket_mitarbeiter
            if ID_Mitarbeiter:
                # Prüfen, ob der Eintrag bereits existiert
                check_query = "SELECT COUNT(*) FROM ticket_mitarbeiter WHERE ID_Ticket = :ticket_id AND ID_Mitarbeiter = :ID_Mitarbeiter"
                result = DatabaseManager.execute_query(check_query, {"ticket_id": ticket_id, "ID_Mitarbeiter": ID_Mitarbeiter})

                if result and result[0] == 0:  # Eintrag existiert noch nicht
                    insert_query = "INSERT INTO ticket_mitarbeiter (ID_Ticket, ID_Mitarbeiter, Rolle_im_Ticket) VALUES (:ticket_id, :ID_Mitarbeiter, 'Hauptverantwortlicher')"
                    DatabaseManager.execute_query(insert_query, {"ticket_id": ticket_id, "ID_Mitarbeiter": ID_Mitarbeiter}, commit=True)

            # Eintrag in ticket_kategorie
            if kategorie_id:
                # Prüfen, ob die Kategorie existiert
                check_kategorie = "SELECT COUNT(*) FROM kategorie WHERE ID_Kategorie = :kategorie_id"
                kategorie_result = DatabaseManager.execute_query(check_kategorie, {"kategorie_id": kategorie_id})

                if kategorie_result and kategorie_result[0] > 0:
                    # Prüfen, ob der Eintrag bereits existiert
                    check_query = "SELECT COUNT(*) FROM ticket_kategorie WHERE ID_Ticket = :ticket_id AND ID_Kategorie = :kategorie_id"
                    result = DatabaseManager.execute_query(check_query, {"ticket_id": ticket_id, "kategorie_id": kategorie_id})

                    if result and result[0] == 0:  # Eintrag existiert noch nicht
                        insert_query = "INSERT INTO ticket_kategorie (ID_Ticket, ID_Kategorie) VALUES (:ticket_id, :kategorie_id)"
                        DatabaseManager.execute_query(insert_query, {"ticket_id": ticket_id, "kategorie_id": kategorie_id}, commit=True)

            return True
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Ticket-Beziehungen: {str(e)}")
            return False

    @staticmethod
    def get_tickets(search_term=None, search_field=None, status_filter=None, priority_filter=None, mitarbeiter_filter=None):
        """
        Ruft Tickets basierend auf Suchkriterien ab.

        Args:
            search_term: Suchbegriff
            search_field: Suchfeld
            status_filter: Statusfilter
            priority_filter: Prioritätsfilter
            mitarbeiter_filter: Mitarbeiterfilter

        Returns:
            pandas.DataFrame: Gefilterte Tickets
        """
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
        if status_filter and status_filter != "Alle":
            query += " AND s.Name = :status"
            params["status"] = status_filter

        if priority_filter and priority_filter != "Alle":
            query += " AND t.Priorität = :priority"
            params["priority"] = priority_filter

        if mitarbeiter_filter and mitarbeiter_filter != "Alle":
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

        return DatabaseManager.execute_query_to_dataframe(query, params)

    @staticmethod
    def get_ticket_details(ticket_id):
        """
        Ruft die Details eines Tickets ab.

        Args:
            ticket_id: ID des Tickets

        Returns:
            dict: Ticket-Details oder None bei Fehler
        """
        query = """
        SELECT t.ID_Ticket, t.Titel, t.Beschreibung, t.Priorität, 
               s.Name as Status, s.ID_Status,
               m.Name as Mitarbeiter, m.ID_Mitarbeiter,
               k.Name as Kunde, k.ID_Kunde,
               t.Erstellt_am, t.Geändert_am
        FROM ticket t
        LEFT JOIN status s ON t.ID_Status = s.ID_Status
        LEFT JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
        LEFT JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
        WHERE t.ID_Ticket = :ticket_id
        """

        result = DatabaseManager.execute_query(query, {"ticket_id": ticket_id})

        if result:
            # Umwandlung in Dictionary für einfacheren Zugriff
            columns = result._fields
            return {columns[i]: value for i, value in enumerate(result)}

        return None

    @staticmethod
    def get_ticket_comments(ticket_id):
        """
        Ruft die Kommentare zu einem Ticket ab.

        Args:
            ticket_id: ID des Tickets

        Returns:
            pandas.DataFrame: Kommentare
        """
        query = """
        SELECT k.ID_Kommentar, k.Kommentar_Text AS Kommentar, m.Name as Mitarbeiter, k.Erstellt_am
        FROM ticket_kommentar k
        JOIN mitarbeiter m ON k.ID_Mitarbeiter = m.ID_Mitarbeiter
        WHERE k.ID_Ticket = :ID_Ticket
        ORDER BY k.Erstellt_am DESC
        """

        return DatabaseManager.execute_query_to_dataframe(query, {"ID_Ticket": ticket_id})

    @staticmethod
    def add_comment(ticket_id, user_id, comment_text):
        """
        Fügt einen Kommentar zu einem Ticket hinzu.

        Args:
            ticket_id: ID des Tickets
            user_id: ID des Mitarbeiters
            comment_text: Kommentartext

        Returns:
            bool: Erfolg
        """
        if not comment_text.strip():
            return False

        query = """
        INSERT INTO ticket_kommentar (ID_Ticket, ID_Mitarbeiter, Kommentar_Text, Erstellt_am)
        VALUES (:ID_Ticket, :ID_Mitarbeiter, :Kommentar_Text, NOW())
        """

        try:
            DatabaseManager.execute_query(
                query,
                {
                    "ID_Ticket": ticket_id,
                    "ID_Mitarbeiter": user_id,
                    "Kommentar_Text": comment_text
                },
                commit=True
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Kommentars: {str(e)}")
            return False

    @staticmethod
    def get_ticket_history(ticket_id):
        """
        Ruft die Änderungshistorie eines Tickets ab.

        Args:
            ticket_id: ID des Tickets

        Returns:
            pandas.DataFrame: Änderungshistorie
        """
        query = """
        SELECT th.Feldname, th.Alter_Wert, th.Neuer_Wert, m.Name AS Geändert_von, th.Geändert_am
        FROM ticket_historie th
        LEFT JOIN mitarbeiter m ON th.Geändert_von = m.ID_Mitarbeiter
        WHERE th.ID_Ticket = :ticket_id
        ORDER BY th.Geändert_am DESC
        """

        return DatabaseManager.execute_query_to_dataframe(query, {"ticket_id": ticket_id})

    @staticmethod
    def update_ticket(ticket_id, status_id, priority, mitarbeiter_id, user_id):
        """
        Aktualisiert ein Ticket und protokolliert die Änderungen.

        Args:
            ticket_id: ID des Tickets
            status_id: ID des Status
            priority: Priorität
            mitarbeiter_id: ID des zugewiesenen Mitarbeiters
            user_id: ID des Mitarbeiters, der die Änderung vornimmt

        Returns:
            bool: Erfolg
        """
        try:
            # Aktuelle Werte abrufen
            current_values = TicketManager.get_ticket_details(ticket_id)
            if not current_values:
                return False

            # Änderungen protokollieren
            if current_values["ID_Status"] != status_id:
                TicketManager.log_ticket_change(
                    ticket_id, "Status", current_values["Status"],
                    DatabaseManager.execute_query("SELECT Name FROM status WHERE ID_Status = :id", {"id": status_id})[0],
                    user_id
                )

            if current_values["Priorität"] != priority:
                TicketManager.log_ticket_change(
                    ticket_id, "Priorität", current_values["Priorität"], priority, user_id
                )

            if current_values["ID_Mitarbeiter"] != mitarbeiter_id:
                TicketManager.log_ticket_change(
                    ticket_id, "Mitarbeiter", current_values["Mitarbeiter"],
                    DatabaseManager.execute_query("SELECT Name FROM mitarbeiter WHERE ID_Mitarbeiter = :id", {"id": mitarbeiter_id})[0],
                    user_id
                )

            # Ticket aktualisieren
            query = """
            UPDATE ticket
            SET ID_Status = :status_id, Priorität = :priority, ID_Mitarbeiter = :mitarbeiter_id, Geändert_am = NOW()
            WHERE ID_Ticket = :ticket_id
            """

            DatabaseManager.execute_query(
                query,
                {
                    "status_id": status_id,
                    "priority": priority,
                    "mitarbeiter_id": mitarbeiter_id,
                    "ticket_id": ticket_id
                },
                commit=True
            )

            # Ticket-Beziehungen aktualisieren
            TicketManager.create_ticket_relations(ticket_id, mitarbeiter_id)

            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Tickets: {str(e)}")
            return False

    @staticmethod
    def create_ticket(titel, beschreibung, priorität, status_id, kunde_id, mitarbeiter_id, user_id):
        """
        Erstellt ein neues Ticket.

        Args:
            titel: Titel des Tickets
            beschreibung: Beschreibung
            priorität: Priorität
            status_id: ID des Status
            kunde_id: ID des Kunden
            mitarbeiter_id: ID des zugewiesenen Mitarbeiters
            user_id: ID des erstellenden Mitarbeiters

        Returns:
            int: ID des erstellten Tickets oder None bei Fehler
        """
        try:
            query = """
            INSERT INTO ticket (Titel, Beschreibung, Priorität, ID_Status, ID_Kunde, ID_Mitarbeiter, Erstellt_am, Geändert_am)
            VALUES (:titel, :beschreibung, :priorität, :status_id, :kunde_id, :mitarbeiter_id, NOW(), NOW())
            """

            result = DatabaseManager.execute_query(
                query,
                {
                    "titel": titel,
                    "beschreibung": beschreibung,
                    "priorität": priorität,
                    "status_id": status_id,
                    "kunde_id": kunde_id,
                    "mitarbeiter_id": mitarbeiter_id
                },
                commit=True
            )

            if result and result.lastrowid:
                ticket_id = result.lastrowid

                # Ticket-Beziehungen erstellen
                TicketManager.create_ticket_relations(ticket_id, mitarbeiter_id)

                # Erstellungs-Kommentar hinzufügen
                TicketManager.add_comment(
                    ticket_id,
                    user_id,
                    f"Ticket erstellt mit Priorität {priorität}."
                )

                return ticket_id

            return None
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            return None

    @staticmethod
    @lru_cache(maxsize=1)
    def get_ticket_statistics():
        """
        Ruft Statistiken zu Tickets ab (mit Caching).

        Returns:
            dict: Dictionary mit verschiedenen Statistik-DataFrames
        """
        try:
            # Tickets nach Status
            status_query = """
            SELECT s.Name as Status, COUNT(*) as Anzahl
            FROM ticket t
            JOIN status s ON t.ID_Status = s.ID_Status
            GROUP BY s.Name
            ORDER BY s.Name
            """

            # Tickets nach Priorität
            priority_query = """
            SELECT Priorität, COUNT(*) as Anzahl
            FROM ticket
            GROUP BY Priorität
            ORDER BY FIELD(Priorität, 'Hoch', 'Mittel', 'Niedrig')
            """

            # Tickets pro Mitarbeiter
            mitarbeiter_query = """
            SELECT m.Name as Mitarbeiter, COUNT(*) as Anzahl
            FROM ticket t
            JOIN mitarbeiter m ON t.ID_Mitarbeiter = m.ID_Mitarbeiter
            GROUP BY m.Name
            ORDER BY COUNT(*) DESC
            LIMIT 10
            """

            # Tickets pro Kunde
            kunden_query = """
            SELECT k.Name as Kunde, COUNT(*) as Anzahl
            FROM ticket t
            JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
            GROUP BY k.Name
            ORDER BY COUNT(*) DESC
            LIMIT 10
            """

            # Tickets pro Monat
            monat_query = """
            SELECT DATE_FORMAT(Erstellt_am, '%Y-%m') as Monat, COUNT(*) as Anzahl
            FROM ticket
            WHERE Erstellt_am >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(Erstellt_am, '%Y-%m')
            ORDER BY Monat
            """

            return {
                "status": DatabaseManager.execute_query_to_dataframe(status_query),
                "priority": DatabaseManager.execute_query_to_dataframe(priority_query),
                "mitarbeiter": DatabaseManager.execute_query_to_dataframe(mitarbeiter_query),
                "kunden": DatabaseManager.execute_query_to_dataframe(kunden_query),
                "monat": DatabaseManager.execute_query_to_dataframe(monat_query)
            }
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Ticket-Statistiken: {str(e)}")
            return {
                "status": pd.DataFrame(),
                "priority": pd.DataFrame(),
                "mitarbeiter": pd.DataFrame(),
                "kunden": pd.DataFrame(),
                "monat": pd.DataFrame()
            }

# Klasse für Authentifizierung und Benutzerverwaltung
class AuthManager:
    @staticmethod
    def generate_salt():
        """Generiert einen zufälligen Salt für das Passwort-Hashing."""
        return secrets.token_hex(16)

    @staticmethod
    def hash_password(password, salt):
        """
        Hasht ein Passwort mit dem angegebenen Salt.

        Args:
            password: Passwort
            salt: Salt

        Returns:
            str: Gehashtes Passwort
        """
        salted_password = password + salt
        password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
        return password_hash

    @staticmethod
    def verify_password(password, stored_hash, salt):
        """
        Überprüft, ob das eingegebene Passwort korrekt ist.

        Args:
            password: Passwort
            stored_hash: Gespeicherter Hash
            salt: Salt

        Returns:
            bool: Ob das Passwort korrekt ist
        """
        calculated_hash = AuthManager.hash_password(password, salt)
        return calculated_hash == stored_hash

    @staticmethod
    def generate_temp_password(length=12):
        """
        Generiert ein zufälliges temporäres Passwort.

        Args:
            length: Länge des Passworts

        Returns:
            str: Temporäres Passwort
        """
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

    @staticmethod
    def authenticate_user(username_or_email, password):
        """
        Authentifiziert einen Benutzer.

        Args:
            username_or_email: Benutzername oder E-Mail
            password: Passwort

        Returns:
            tuple: (Erfolg, Benutzer-ID, Passwortänderung erforderlich)
        """
        try:
            # Kleine Verzögerung als Schutz vor Brute-Force-Angriffen
            time.sleep(0.5)

            # Benutzer in der Datenbank suchen
            query = """
            SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required 
            FROM mitarbeiter 
            WHERE Name = :username OR Email = :email
            """

            result = DatabaseManager.execute_query(query, {"username": username_or_email, "email": username_or_email})

            if not result:
                return False, None, False

            user_id, name, stored_hash, salt, password_change_required = result

            # Falls kein Salt vorhanden ist (Altdaten), Passwort direkt vergleichen
            # und bei Erfolg ein Salt generieren und das Passwort hashen
            if not salt:
                if password == stored_hash:
                    # Passwort ist korrekt, aber ungehasht - jetzt hashen und speichern
                    new_salt = AuthManager.generate_salt()
                    new_hash = AuthManager.hash_password(password, new_salt)

                    # Datensatz aktualisieren
                    update_query = """
                    UPDATE mitarbeiter 
                    SET Password_hash = :password_hash, salt = :salt 
                    WHERE ID_Mitarbeiter = :user_id
                    """

                    DatabaseManager.execute_query(
                        update_query,
                        {
                            "password_hash": new_hash,
                            "salt": new_salt,
                            "user_id": user_id
                        },
                        commit=True
                    )

                    return True, user_id, password_change_required
                else:
                    return False, None, False

            # Ansonsten mit Salt hashen und vergleichen
            if AuthManager.verify_password(password, stored_hash, salt):
                return True, user_id, password_change_required
            else:
                return False, None, False

        except Exception as e:
            logger.error(f"Fehler bei der Authentifizierung: {str(e)}")
            return False, None, False

    @staticmethod
    def reset_password(email):
        """
        Setzt das Passwort eines Benutzers zurück.

        Args:
            email: E-Mail-Adresse

        Returns:
            tuple: (Erfolg, Name, temporäres Passwort)
        """
        try:
            # Benutzer in der Datenbank suchen
            query = """
            SELECT ID_Mitarbeiter, Name, Email 
            FROM mitarbeiter 
            WHERE Email = :email
            """

            result = DatabaseManager.execute_query(query, {"email": email})

            if not result:
                return False, None, None

            user_id, name, user_email = result

            # Temporäres Passwort generieren
            temp_password = AuthManager.generate_temp_password()

            # Salt generieren und temporäres Passwort hashen
            salt = AuthManager.generate_salt()
            password_hash = AuthManager.hash_password(temp_password, salt)

            # Ablaufdatum für das temporäre Passwort (24 Stunden)
            expiry = datetime.now() + timedelta(hours=24)

            # Datensatz aktualisieren
            update_query = """
            UPDATE mitarbeiter 
            SET Password_hash = :password_hash, 
                salt = :salt, 
                reset_token = :reset_token, 
                reset_token_expiry = :expiry, 
                password_change_required = TRUE 
            WHERE ID_Mitarbeiter = :user_id
            """

            DatabaseManager.execute_query(
                update_query,
                {
                    "password_hash": password_hash,
                    "salt": salt,
                    "reset_token": secrets.token_hex(16),  # Zusätzlicher Token für Sicherheit
                    "expiry": expiry,
                    "user_id": user_id
                },
                commit=True
            )

            return True, name, temp_password

        except Exception as e:
            logger.error(f"Fehler bei der Passwort-Wiederherstellung: {str(e)}")
            return False, None, None

    @staticmethod
    def change_password(user_id, new_password):
        """
        Ändert das Passwort eines Benutzers.

        Args:
            user_id: Benutzer-ID
            new_password: Neues Passwort

        Returns:
            bool: Erfolg
        """
        try:
            # Salt generieren und neues Passwort hashen
            salt = AuthManager.generate_salt()
            password_hash = AuthManager.hash_password(new_password, salt)

            # Datensatz aktualisieren
            update_query = """
            UPDATE mitarbeiter 
            SET Password_hash = :password_hash, 
                salt = :salt, 
                reset_token = NULL, 
                reset_token_expiry = NULL, 
                password_change_required = FALSE 
            WHERE ID_Mitarbeiter = :user_id
            """

            DatabaseManager.execute_query(
                update_query,
                {
                    "password_hash": password_hash,
                    "salt": salt,
                    "user_id": user_id
                },
                commit=True
            )

            return True

        except Exception as e:
            logger.error(f"Fehler beim Ändern des Passworts: {str(e)}")
            return False

    @staticmethod
    @lru_cache(maxsize=10)
    def get_user_info(user_id):
        """
        Ruft Informationen zu einem Benutzer ab (mit Caching).

        Args:
            user_id: Benutzer-ID

        Returns:
            dict: Benutzerinformationen oder None bei Fehler
        """
        try:
            query = """
            SELECT ID_Mitarbeiter, Name, Email, ID_Rolle, Erstellt_am
            FROM mitarbeiter
            WHERE ID_Mitarbeiter = :user_id
            """

            result = DatabaseManager.execute_query(query, {"user_id": user_id})

            if result:
                # Umwandlung in Dictionary für einfacheren Zugriff
                columns = result._fields
                return {columns[i]: value for i, value in enumerate(result)}

            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzerinformationen: {str(e)}")
            return None

# UI-Komponenten
class UIComponents:
    @staticmethod
    def show_password_reset_page():
        """Zeigt die Passwort-Wiederherstellungsseite an."""
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
                success, name, temp_password = AuthManager.reset_password(email)
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

    @staticmethod
    def show_password_change_page():
        """Zeigt die Passwortänderungsseite an."""
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
                success = AuthManager.change_password(st.session_state.user_id, new_password)
                if success:
                    st.success("Passwort erfolgreich geändert!")
                    st.session_state.password_changed = True
                    time.sleep(1)  # Kurze Verzögerung, damit die Erfolgsmeldung sichtbar ist
                    st.rerun()
                else:
                    st.error("Fehler beim Ändern des Passworts.")

    @staticmethod
    def show_login_page():
        """Zeigt die Login-Seite an."""
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
                success, user_id, password_change_required = AuthManager.authenticate_user(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.session_state.password_change_required = password_change_required

                    # Benutzername für die Anzeige speichern
                    user_info = AuthManager.get_user_info(user_id)
                    if user_info:
                        st.session_state.username = user_info["Name"]

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

    @staticmethod
    def show_ticket_overview():
        """Zeigt die Ticketübersicht an."""
        st.subheader("📋 Ticketübersicht")

        # Suchfunktion
        st.subheader("🔍 Ticket suchen")
        search_col1, search_col2 = st.columns([3, 1])

        with search_col1:
            search_term = st.text_input("Suchbegriff eingeben (Titel, Beschreibung, Kunde, Mitarbeiter)",
                                        placeholder="z.B. Server, Netzwerk, Max Mustermann...")

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
            status_df = DatabaseManager.execute_query_to_dataframe("SELECT Name FROM status ORDER BY Name")
            status_options = ["Alle"] + status_df["Name"].tolist()
            status_filter = st.selectbox("Status", status_options)

        with col2:
            priority_options = ["Alle", "Hoch", "Mittel", "Niedrig"]
            priority_filter = st.selectbox("Priorität", priority_options)

        with col3:
            # Mitarbeiter-Optionen abrufen
            mitarbeiter_df = DatabaseManager.execute_query_to_dataframe("SELECT Name FROM mitarbeiter ORDER BY Name")
            mitarbeiter_options = ["Alle"] + mitarbeiter_df["Name"].tolist()
            mitarbeiter_filter = st.selectbox("Mitarbeiter", mitarbeiter_options)

        # Tickets abrufen
        tickets_df = TicketManager.get_tickets(search_term, search_field, status_filter, priority_filter, mitarbeiter_filter)

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
                UIComponents.show_ticket_details(selected_ticket)

    @staticmethod
    def show_ticket_details(ticket_id):
        """
        Zeigt die Details eines Tickets an.

        Args:
            ticket_id: ID des Tickets
        """
        # Ticket-Details abrufen
        ticket = TicketManager.get_ticket_details(ticket_id)

        if not ticket:
            st.error("Ticket nicht gefunden.")
            return

        # Ticket-Details anzeigen
        st.subheader(f"Ticket #{ticket['ID_Ticket']}: {ticket['Titel']}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"**Status:** {ticket['Status']}")
            st.write(f"**Priorität:** {ticket['Priorität']}")

        with col2:
            st.write(f"**Mitarbeiter:** {ticket['Mitarbeiter']}")
            st.write(f"**Kunde:** {ticket['Kunde']}")

        with col3:
            st.write(f"**Erstellt am:** {ticket['Erstellt_am']}")
            st.write(f"**Geändert am:** {ticket['Geändert_am']}")

        st.markdown("---")
        st.write("**Beschreibung:**")
        st.write(ticket['Beschreibung'])

        # Kommentare abrufen
        st.markdown("---")
        st.subheader("Kommentare")

        kommentare_df = TicketManager.get_ticket_comments(ticket_id)

        if kommentare_df.empty:
            st.info("Keine Kommentare vorhanden.")
        else:
            for _, kommentar in kommentare_df.iterrows():
                st.markdown(f"""
                **{kommentar['Mitarbeiter']}** - {kommentar['Erstellt_am']}
                
                {kommentar['Kommentar']}
                
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
                success = TicketManager.add_comment(ticket_id, st.session_state.user_id, comment_text)
                if success:
                    st.success("Kommentar erfolgreich hinzugefügt!")
                    st.rerun()
                else:
                    st.error("Fehler beim Hinzufügen des Kommentars.")

        # --- Ticket-Historie anzeigen ---
        st.markdown("---")
        st.subheader("🕘 Änderungshistorie")

        historie_df = TicketManager.get_ticket_history(ticket_id)

        if historie_df.empty:
            st.info("Keine Änderungshistorie vorhanden.")
        else:
            st.dataframe(historie_df, use_container_width=True)

    @staticmethod
    def show_ticket_edit_tab():
        """Zeigt den Tab zum Bearbeiten eines Tickets an."""
        st.subheader("✏️ Ticket bearbeiten")

        if "selected_ticket_id" not in st.session_state or not st.session_state.selected_ticket_id:
            st.info("Bitte wählen Sie zuerst ein Ticket in der Ticketübersicht aus.")
            return

        ticket_id = st.session_state.selected_ticket_id
        ticket = TicketManager.get_ticket_details(ticket_id)

        if not ticket:
            st.error("Ticket nicht gefunden.")
            return

        st.subheader(f"Ticket #{ticket_id}: {ticket['Titel']}")

        # Status-Optionen abrufen
        status_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Status, Name FROM status ORDER BY Name")

        # Mitarbeiter-Optionen abrufen
        mitarbeiter_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Mitarbeiter, Name FROM mitarbeiter ORDER BY Name")

        # Formular zum Bearbeiten des Tickets
        with st.form("edit_ticket_form"):

            # Convert options to native Python int
            status_options = [int(x) for x in status_df["ID_Status"].tolist()]
            # Find the index of the current status
            current_status_index = 0
            if not status_df[status_df["Name"] == ticket["Status"]].empty:
                current_status = status_df[status_df["Name"] == ticket["Status"]]["ID_Status"].iloc[0]
                try:
                    current_status_index = status_options.index(int(current_status))
                except (ValueError, TypeError):
                    current_status_index = 0

                status_options = [int(x) for x in status_df["ID_Status"].tolist()]
            # Find the index of the current status
            current_status_index = 0
            if not status_df[status_df["Name"] == ticket["Status"]].empty:
                current_status = status_df[status_df["Name"] == ticket["Status"]]["ID_Status"].iloc[0]
                try:
                    current_status_index = status_options.index(int(current_status))
                except (ValueError, TypeError):
                    current_status_index = 0

            status_id = st.selectbox(
                "Status",
                options=status_options,
                format_func=lambda x: status_df[status_df["ID_Status"] == x]["Name"].iloc[0],
                index=current_status_index
            )

            # Priorität
            priority_options = ["Hoch", "Mittel", "Niedrig"]
            priority = st.selectbox(
                "Priorität",
                options=priority_options,
                index=priority_options.index(ticket["Priorität"]) if ticket["Priorität"] in priority_options else 0
            )

            mitarbeiter_options = [int(x) for x in mitarbeiter_df["ID_Mitarbeiter"].tolist()]
            # Find the index of the current mitarbeiter
            current_mitarbeiter_index = 0
            if not mitarbeiter_df[mitarbeiter_df["ID_Mitarbeiter"] == ticket["ID_Mitarbeiter"]].empty:
                current_mitarbeiter = ticket["ID_Mitarbeiter"]
                try:
                    current_mitarbeiter_index = mitarbeiter_options.index(int(current_mitarbeiter))
                except (ValueError, TypeError):
                    current_mitarbeiter_index = 0

            mitarbeiter_id = st.selectbox(
                "Zugewiesen an",
                options=mitarbeiter_options,
                format_func=lambda x: mitarbeiter_df[mitarbeiter_df["ID_Mitarbeiter"] == x]["Name"].iloc[0],
                index=current_mitarbeiter_index
            )

            submit = st.form_submit_button("Ticket aktualisieren")

        if submit:
            success = TicketManager.update_ticket(
                ticket_id,
                status_id,
                priority,
                mitarbeiter_id,
                st.session_state.user_id
            )

            if success:
                st.success("Ticket erfolgreich aktualisiert!")
                st.rerun()
            else:
                st.error("Fehler beim Aktualisieren des Tickets.")

    @staticmethod
    def show_new_ticket_form():
        """Zeigt das Formular zum Erstellen eines neuen Tickets an."""
        st.subheader("➕ Neues Ticket")

        # Status-Optionen abrufen
        status_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Status, Name FROM status ORDER BY Name")

        # Mitarbeiter-Optionen abrufen
        mitarbeiter_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Mitarbeiter, Name FROM mitarbeiter ORDER BY Name")

        # Kunden-Optionen abrufen
        kunden_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Kunde, Name FROM kunde ORDER BY Name")

        with st.form("new_ticket_form"):
            titel = st.text_input("Titel", placeholder="Kurzer, aussagekräftiger Titel")
            beschreibung = st.text_area("Beschreibung", placeholder="Detaillierte Beschreibung des Problems oder der Anfrage")

            col1, col2, col3 = st.columns(3)

            with col1:
                status_id = st.selectbox(
                    "Status",
                    options=status_df["ID_Status"].tolist(),
                    format_func=lambda x: status_df[status_df["ID_Status"] == x]["Name"].iloc[0]
                )

            with col2:
                priority_options = ["Hoch", "Mittel", "Niedrig"]
                priority = st.selectbox("Priorität", priority_options)

            with col3:
                mitarbeiter_id = st.selectbox(
                    "Zugewiesen an",
                    options=mitarbeiter_df["ID_Mitarbeiter"].tolist(),
                    format_func=lambda x: mitarbeiter_df[mitarbeiter_df["ID_Mitarbeiter"] == x]["Name"].iloc[0]
                )

            kunde_id = st.selectbox(
                "Kunde",
                options=kunden_df["ID_Kunde"].tolist(),
                format_func=lambda x: kunden_df[kunden_df["ID_Kunde"] == x]["Name"].iloc[0]
            )

            submit = st.form_submit_button("Ticket erstellen")

        if submit:
            if not titel or not beschreibung:
                st.error("Bitte füllen Sie alle Pflichtfelder aus.")
            else:
                ticket_id = TicketManager.create_ticket(
                    titel,
                    beschreibung,
                    priority,
                    status_id,
                    kunde_id,
                    mitarbeiter_id,
                    st.session_state.user_id
                )

                if ticket_id:
                    st.success(f"Ticket #{ticket_id} erfolgreich erstellt!")
                    # Ticket-ID für die Detailansicht speichern
                    st.session_state.selected_ticket_id = ticket_id
                    time.sleep(1)  # Kurze Verzögerung, damit die Erfolgsmeldung sichtbar ist
                    st.rerun()
                else:
                    st.error("Fehler beim Erstellen des Tickets.")

    @staticmethod
    def show_ticket_statistics():
        """Zeigt Statistiken zu Tickets an."""
        st.subheader("📊 Statistiken")

        # Statistiken abrufen (mit Caching)
        stats = TicketManager.get_ticket_statistics()

        # Statistiken anzeigen
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Tickets nach Status")
            if not stats["status"].empty:
                chart = alt.Chart(stats["status"]).mark_bar().encode(
                    x=alt.X("Status:N", title="Status"),
                    y=alt.Y("Anzahl:Q", title="Anzahl"),
                    color=alt.Color("Status:N", scale=alt.Scale(scheme="category10"))
                ).properties(width=400, height=300)

                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Keine Daten verfügbar.")

        with col2:
            st.subheader("Tickets nach Priorität")
            if not stats["priority"].empty:
                # Farbzuordnung für Prioritäten
                color_scale = alt.Scale(
                    domain=["Hoch", "Mittel", "Niedrig"],
                    range=["#FF0000", "#FFA500", "#00FF00"]
                )

                chart = alt.Chart(stats["priority"]).mark_bar().encode(
                    x=alt.X("Priorität:N", title="Priorität", sort=["Hoch", "Mittel", "Niedrig"]),
                    y=alt.Y("Anzahl:Q", title="Anzahl"),
                    color=alt.Color("Priorität:N", scale=color_scale)
                ).properties(width=400, height=300)

                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("Keine Daten verfügbar.")

        st.subheader("Tickets pro Mitarbeiter")
        if not stats["mitarbeiter"].empty:
            chart = alt.Chart(stats["mitarbeiter"]).mark_bar().encode(
                x=alt.X("Anzahl:Q", title="Anzahl"),
                y=alt.Y("Mitarbeiter:N", title="Mitarbeiter", sort="-x"),
                color=alt.Color("Mitarbeiter:N", scale=alt.Scale(scheme="category20"))
            ).properties(width=800, height=400)

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Keine Daten verfügbar.")

        st.subheader("Tickets pro Kunde")
        if not stats["kunden"].empty:
            chart = alt.Chart(stats["kunden"]).mark_bar().encode(
                x=alt.X("Anzahl:Q", title="Anzahl"),
                y=alt.Y("Kunde:N", title="Kunde", sort="-x"),
                color=alt.Color("Kunde:N", scale=alt.Scale(scheme="tableau10"))
            ).properties(width=800, height=400)

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Keine Daten verfügbar.")

        st.subheader("Tickets pro Monat")
        if not stats["monat"].empty:
            chart = alt.Chart(stats["monat"]).mark_line(point=True).encode(
                x=alt.X("Monat:T", title="Monat"),
                y=alt.Y("Anzahl:Q", title="Anzahl"),
                tooltip=["Monat:T", "Anzahl:Q"]
            ).properties(width=800, height=300)

            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Keine Daten verfügbar.")

    @staticmethod
    def show_settings():
        """Zeigt die Einstellungen an."""
        st.subheader("⚙️ Einstellungen")

        # Tabs für verschiedene Einstellungsbereiche
        settings_tabs = st.tabs(["👤 Benutzerprofil", "👥 Mitarbeiter", "🏢 Kunden", "🏷️ Kategorien", "📊 Status"])

        # Tab: Benutzerprofil
        with settings_tabs[0]:
            UIComponents.show_user_profile()

        # Tab: Mitarbeiter
        with settings_tabs[1]:
            UIComponents.show_employee_management()

        # Tab: Kunden
        with settings_tabs[2]:
            UIComponents.show_customer_management()

        # Tab: Kategorien
        with settings_tabs[3]:
            UIComponents.show_category_management()

        # Tab: Status
        with settings_tabs[4]:
            UIComponents.show_status_management()

    @staticmethod
    def show_user_profile():
        """Zeigt das Benutzerprofil an."""
        st.subheader("👤 Benutzerprofil")

        # Benutzerinformationen abrufen
        user_info = AuthManager.get_user_info(st.session_state.user_id)

        if not user_info:
            st.error("Fehler beim Abrufen der Benutzerinformationen.")
            return

        # Benutzerinformationen anzeigen
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Name:** {user_info['Name']}")
            st.write(f"**E-Mail:** {user_info['Email']}")

        with col2:
            # Rolle abrufen
            rolle_query = "SELECT Name FROM rollen WHERE ID_Rolle = :rolle_id"
            rolle_result = DatabaseManager.execute_query(rolle_query, {"rolle_id": user_info['ID_Rolle']})
            rolle_name = rolle_result[0] if rolle_result else "Unbekannt"

            st.write(f"**Rolle:** {rolle_name}")
            st.write(f"**Erstellt am:** {user_info['Erstellt_am']}")

        # Passwort ändern
        st.markdown("---")
        st.subheader("🔐 Passwort ändern")

        with st.form("change_password_form"):
            current_password = st.text_input("Aktuelles Passwort", type="password")
            new_password = st.text_input("Neues Passwort", type="password")
            confirm_password = st.text_input("Passwort bestätigen", type="password")
            submit = st.form_submit_button("Passwort ändern")

        if submit:
            if not current_password or not new_password or not confirm_password:
                st.error("Bitte füllen Sie alle Felder aus.")
            elif new_password != confirm_password:
                st.error("Die Passwörter stimmen nicht überein.")
            elif len(new_password) < 8:
                st.error("Das Passwort muss mindestens 8 Zeichen lang sein.")
            else:
                # Aktuelles Passwort überprüfen
                query = "SELECT Password_hash, salt FROM mitarbeiter WHERE ID_Mitarbeiter = :user_id"
                result = DatabaseManager.execute_query(query, {"user_id": st.session_state.user_id})

                if result and AuthManager.verify_password(current_password, result[0], result[1]):
                    success = AuthManager.change_password(st.session_state.user_id, new_password)
                    if success:
                        st.success("Passwort erfolgreich geändert!")
                    else:
                        st.error("Fehler beim Ändern des Passworts.")
                else:
                    st.error("Das aktuelle Passwort ist nicht korrekt.")

    @staticmethod
    def show_employee_management():
        """Zeigt die Mitarbeiterverwaltung an."""
        st.subheader("👥 Mitarbeiter")

        # Mitarbeiter abrufen
        query = """
        SELECT m.ID_Mitarbeiter, m.Name, m.Email, r.Name as Rolle, m.Erstellt_am
        FROM mitarbeiter m
        JOIN rollen r ON m.ID_Rolle = r.ID_Rolle
        ORDER BY m.Name
        """

        mitarbeiter_df = DatabaseManager.execute_query_to_dataframe(query)

        if mitarbeiter_df.empty:
            st.info("Keine Mitarbeiter gefunden.")
        else:
            st.dataframe(mitarbeiter_df, use_container_width=True)

        # Neuen Mitarbeiter hinzufügen
        st.markdown("---")
        st.subheader("➕ Neuen Mitarbeiter hinzufügen")

        # Rollen abrufen
        rollen_df = DatabaseManager.execute_query_to_dataframe("SELECT ID_Rolle, Name FROM rollen ORDER BY Name")

        with st.form("new_employee_form"):
            name = st.text_input("Name")
            email = st.text_input("E-Mail")
            password = st.text_input("Passwort", type="password")

            # Check if the column exists before accessing it
            if "ID_Rolle" in rollen_df.columns:
                rolle_options = [int(x) for x in rollen_df["ID_Rolle"].tolist()]
                rolle_id = st.selectbox(
                    "Rolle",
                    options=rolle_options,
                    format_func=lambda x: rollen_df[rollen_df["ID_Rolle"] == x]["Name"].iloc[0]
                )
            else:
                st.error("Fehler: Die Spalte 'ID_Rolle' wurde nicht gefunden. Bitte überprüfen Sie die Datenbankstruktur.")
                rolle_id = None


                submit = st.form_submit_button("Mitarbeiter hinzufügen")

        if submit:
            if not name or not email or not password:
                st.error("Bitte füllen Sie alle Pflichtfelder aus.")
            elif len(password) < 8:
                st.error("Das Passwort muss mindestens 8 Zeichen lang sein.")
            else:
                # E-Mail-Format überprüfen
                if "@" not in email or "." not in email:
                    st.error("Bitte geben Sie eine gültige E-Mail-Adresse ein.")
                    return

                # Überprüfen, ob die E-Mail bereits existiert
                check_query = "SELECT COUNT(*) FROM mitarbeiter WHERE Email = :email"
                result = DatabaseManager.execute_query(check_query, {"email": email})

                if result and result[0] > 0:
                    st.error("Diese E-Mail-Adresse wird bereits verwendet.")
                    return

                # Salt generieren und Passwort hashen
                salt = AuthManager.generate_salt()
                password_hash = AuthManager.hash_password(password, salt)

                # Mitarbeiter hinzufügen
                insert_query = """
                INSERT INTO mitarbeiter (Name, Email, Password_hash, salt, ID_Rolle, Erstellt_am)
                VALUES (:name, :email, :password_hash, :salt, :rolle_id, NOW())
                """

                try:
                    DatabaseManager.execute_query(
                        insert_query,
                        {
                            "name": name,
                            "email": email,
                            "password_hash": password_hash,
                            "salt": salt,
                            "rolle_id": rolle_id
                        },
                        commit=True
                    )

                    st.success("Mitarbeiter erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Fehler beim Hinzufügen des Mitarbeiters: {str(e)}")
                    st.error("Fehler beim Hinzufügen des Mitarbeiters.")

    @staticmethod
    def show_customer_management():
        """Zeigt die Kundenverwaltung an."""
        st.subheader("🏢 Kunden")

        # Kunden abrufen
        query = "SELECT * FROM kunde ORDER BY Name"
        kunden_df = DatabaseManager.execute_query_to_dataframe(query)

        if kunden_df.empty:
            st.info("Keine Kunden gefunden.")
        else:
            st.dataframe(kunden_df, use_container_width=True)

        # Neuen Kunden hinzufügen
        st.markdown("---")
        st.subheader("➕ Neuen Kunden hinzufügen")

        with st.form("new_customer_form"):
            name = st.text_input("Name")
            ansprechpartner = st.text_input("Ansprechpartner")
            email = st.text_input("E-Mail")
            telefon = st.text_input("Telefon")
            adresse = st.text_area("Adresse")

            submit = st.form_submit_button("Kunde hinzufügen")

        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen des Kunden ein.")
            else:
                # Überprüfen, ob der Kunde bereits existiert
                check_query = "SELECT COUNT(*) FROM kunde WHERE Name = :name"
                result = DatabaseManager.execute_query(check_query, {"name": name})

                if result and result[0] > 0:
                    st.error("Ein Kunde mit diesem Namen existiert bereits.")
                    return

                # Kunde hinzufügen
                insert_query = """
                INSERT INTO kunde (Name, Ansprechpartner, Email, Telefon, Adresse)
                VALUES (:name, :ansprechpartner, :email, :telefon, :adresse)
                """

                try:
                    DatabaseManager.execute_query(
                        insert_query,
                        {
                            "name": name,
                            "ansprechpartner": ansprechpartner,
                            "email": email,
                            "telefon": telefon,
                            "adresse": adresse
                        },
                        commit=True
                    )

                    st.success("Kunde erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Fehler beim Hinzufügen des Kunden: {str(e)}")
                    st.error("Fehler beim Hinzufügen des Kunden.")

    @staticmethod
    def show_category_management():
        """Zeigt die Kategorieverwaltung an."""
        st.subheader("🏷️ Kategorien")

        # Kategorien abrufen
        query = "SELECT * FROM kategorie ORDER BY Name"
        kategorien_df = DatabaseManager.execute_query_to_dataframe(query)

        if kategorien_df.empty:
            st.info("Keine Kategorien gefunden.")
        else:
            st.dataframe(kategorien_df, use_container_width=True)

        # Neue Kategorie hinzufügen
        st.markdown("---")
        st.subheader("➕ Neue Kategorie hinzufügen")

        with st.form("new_category_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")

            submit = st.form_submit_button("Kategorie hinzufügen")

        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen der Kategorie ein.")
            else:
                # Überprüfen, ob die Kategorie bereits existiert
                check_query = "SELECT COUNT(*) FROM kategorie WHERE Name = :name"
                result = DatabaseManager.execute_query(check_query, {"name": name})

                if result and result[0] > 0:
                    st.error("Eine Kategorie mit diesem Namen existiert bereits.")
                    return

                # Kategorie hinzufügen
                insert_query = """
                INSERT INTO kategorie (Name, Beschreibung)
                VALUES (:name, :beschreibung)
                """

                try:
                    DatabaseManager.execute_query(
                        insert_query,
                        {
                            "name": name,
                            "beschreibung": beschreibung
                        },
                        commit=True
                    )

                    st.success("Kategorie erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Fehler beim Hinzufügen der Kategorie: {str(e)}")
                    st.error("Fehler beim Hinzufügen der Kategorie.")

    @staticmethod
    def show_status_management():
        """Zeigt die Statusverwaltung an."""
        st.subheader("📊 Status")

        # Status abrufen
        query = "SELECT * FROM status ORDER BY Name"
        status_df = DatabaseManager.execute_query_to_dataframe(query)

        if status_df.empty:
            st.info("Keine Status gefunden.")
        else:
            st.dataframe(status_df, use_container_width=True)

        # Neuen Status hinzufügen
        st.markdown("---")
        st.subheader("➕ Neuen Status hinzufügen")

        with st.form("new_status_form"):
            name = st.text_input("Name")
            beschreibung = st.text_area("Beschreibung")
            farbe = st.color_picker("Farbe", "#00FF00")

            submit = st.form_submit_button("Status hinzufügen")

        if submit:
            if not name:
                st.error("Bitte geben Sie mindestens den Namen des Status ein.")
            else:
                # Überprüfen, ob der Status bereits existiert
                check_query = "SELECT COUNT(*) FROM status WHERE Name = :name"
                result = DatabaseManager.execute_query(check_query, {"name": name})

                if result and result[0] > 0:
                    st.error("Ein Status mit diesem Namen existiert bereits.")
                    return

                # Status hinzufügen
                insert_query = """
                INSERT INTO status (Name, Beschreibung, Farbe)
                VALUES (:name, :beschreibung, :farbe)
                """

                try:
                    DatabaseManager.execute_query(
                        insert_query,
                        {
                            "name": name,
                            "beschreibung": beschreibung,
                            "farbe": farbe
                        },
                        commit=True
                    )

                    st.success("Status erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Fehler beim Hinzufügen des Status: {str(e)}")
                    st.error("Fehler beim Hinzufügen des Status.")

    @staticmethod
    def show_database_management():
        """Zeigt die Datenbankverwaltung an."""
        st.title("🗃️ Datenbankverwaltung")

        # Tabellen abrufen
        tables = inspector.get_table_names()

        if not tables:
            st.warning("Keine Tabellen gefunden.")
            return

        # Tabs für die verschiedenen Tabellen
        tabs = st.tabs(tables)

        # Für jede Tabelle einen Tab anzeigen
        for i, tab in enumerate(tabs):
            with tab:
                UIComponents.show_table_management(tables[i])

    @staticmethod
    def show_table_management(table_name):
        """
        Zeigt die Verwaltung einer Tabelle an.

        Args:
            table_name: Name der Tabelle
        """
        st.subheader(f"Tabelle: {table_name}")

        # Suchfunktion für die Tabelle
        UIComponents.show_table_search(table_name)

        # Daten abrufen
        if "search_results" in st.session_state and table_name in st.session_state.search_results:
            # Suchergebnisse anzeigen
            data = st.session_state.search_results[table_name]
            st.success(f"{len(data)} Ergebnisse gefunden.")
        else:
            # Alle Daten anzeigen (mit Limit)
            query = f"SELECT * FROM {table_name} LIMIT 1000"
            data = DatabaseManager.execute_query_to_dataframe(query)

        if data.empty:
            st.info("Keine Daten gefunden.")
            return

        # Daten anzeigen
        st.dataframe(data, use_container_width=True)

        # Datensatz bearbeiten
        st.subheader("Datensatz bearbeiten")

        # Primärschlüssel abrufen
        primary_key = DatabaseManager.get_primary_key(table_name)

        if primary_key:
            # Datensatz-ID eingeben
            record_id = st.number_input(f"{primary_key}-Wert", min_value=1, step=1, key=f"record_id_input_{table_name}")


            if st.button("Datensatz laden", key=f"load_record_{table_name}"):
                # Datensatz abrufen
                query = f"SELECT * FROM {table_name} WHERE {primary_key} = :record_id"
                record_df = DatabaseManager.execute_query_to_dataframe(query, {"record_id": record_id})

                if not record_df.empty:
                    record = record_df.iloc[0]

                    # Formular für die Bearbeitung anzeigen
                    with st.form("edit_record_form"):
                        # Felder dynamisch erstellen
                        updated_values = {}

                        for column in record.index:
                            if column != primary_key:  # Primärschlüssel nicht bearbeiten
                                value = record[column]

                                if pd.isna(value):
                                    value = ""

                                # Feldtyp bestimmen
                                if isinstance(value, (int, float)):
                                    updated_values[column] = st.number_input(column, value=value, key=f"edit_{table_name}_{column}")
                                elif isinstance(value, datetime):
                                    updated_values[column] = st.date_input(column, value=value)
                                else:
                                    updated_values[column] = st.text_input(column, value=str(value))

                        submit = st.form_submit_button("Datensatz aktualisieren")

                    if submit:
                        # Update-Query erstellen
                        set_clause = ", ".join([f"{column} = :{column}" for column in updated_values.keys()])
                        query = f"UPDATE {table_name} SET {set_clause} WHERE {primary_key} = :record_id"

                        # Parameter erstellen
                        params = {**updated_values, "record_id": record_id}

                        try:
                            DatabaseManager.execute_query(query, params, commit=True)
                            st.success("Datensatz erfolgreich aktualisiert!")
                            st.rerun()
                        except Exception as e:
                            logger.error(f"Fehler beim Aktualisieren des Datensatzes: {str(e)}")
                            st.error("Fehler beim Aktualisieren des Datensatzes.")
                else:
                    st.error("Datensatz nicht gefunden.")
        else:
            st.error("Kein Primärschlüssel gefunden.")

        # Neuen Datensatz hinzufügen
        st.subheader("Neuen Datensatz hinzufügen")

        # Spalten abrufen
        columns = inspector.get_columns(table_name)

        if columns:
            with st.form(f"new_record_form_{table_name}"):

                # Felder dynamisch erstellen
                new_values = {}

                for column in columns:
                    column_name = column["name"]
                    column_type = str(column["type"])

                    # Primärschlüssel überspringen, wenn er automatisch generiert wird

                    default_value = column.get("default", "")
                    default_value = column.get("default", "")
                    if column_name == primary_key and default_value is not None and "autoincrement" in default_value:

                        continue

                    # Feldtyp bestimmen
                    if "int" in column_type:
                        new_values[column_name] = st.number_input(column_name, value=0, key=f"new_{table_name}_{column_name}")
                    elif "float" in column_type or "double" in column_type or "decimal" in column_type:
                        new_values[column_name] = st.number_input(column_name, value=0.0, format="%.2f", key=f"new_float_{table_name}_{column_name}")
                    elif "date" in column_type:
                        new_values[column_name] = st.date_input(column_name)
                    elif "time" in column_type:
                        new_values[column_name] = st.time_input(column_name)
                    else:
                        new_values[column_name] = st.text_input(column_name)

                submit = st.form_submit_button("Datensatz hinzufügen")

            if submit:
                # Insert-Query erstellen
                columns_str = ", ".join(new_values.keys())
                placeholders = ", ".join([f":{column}" for column in new_values.keys()])
                query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"

                try:
                    DatabaseManager.execute_query(query, new_values, commit=True)
                    st.success("Datensatz erfolgreich hinzugefügt!")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Fehler beim Hinzufügen des Datensatzes: {str(e)}")
                    st.error("Fehler beim Hinzufügen des Datensatzes.")
        else:
            st.error("Keine Spalten gefunden.")

    @staticmethod
    def show_table_search(table_name):
        """
        Zeigt die Suchfunktion für eine Tabelle an.

        Args:
            table_name: Name der Tabelle
        """
        st.subheader("🔍 Suche")

        # Spalten abrufen
        columns = DatabaseManager.get_searchable_columns(table_name)

        # Suchformular
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            search_term = st.text_input("Suchbegriff", key=f"search_term_{table_name}")

        with col2:
            search_columns = st.multiselect(
                "Spalten",
                columns,
                default=columns[:1] if columns else [],
                key=f"search_columns_{table_name}"
            )

        with col3:
            exact_match = st.checkbox("Exakte Übereinstimmung", key=f"exact_match_{table_name}")

        with col4:
            case_sensitive = st.checkbox("Groß-/Kleinschreibung beachten", key=f"case_sensitive_{table_name}")

        # Suchbutton
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Suchen", key=f"search_button_{table_name}"):
                if search_term and search_columns:
                    results = DatabaseManager.search_table(table_name, search_term, search_columns, exact_match, case_sensitive)

                    if "search_results" not in st.session_state:
                        st.session_state.search_results = {}

                    st.session_state.search_results[table_name] = results
                    st.rerun()
                else:
                    st.error("Bitte geben Sie einen Suchbegriff ein und wählen Sie mindestens eine Spalte aus.")

        with col2:
            if st.button("Zurücksetzen", key=f"reset_button_{table_name}"):
                if "search_results" in st.session_state and table_name in st.session_state.search_results:
                    del st.session_state.search_results[table_name]
                    st.rerun()

# Hauptfunktion
def main():
    # Seitenkonfiguration
    st.set_page_config(page_title="Ticketsystem mit Datenbankverwaltung", page_icon="🎫", layout="wide")

    # Sicherstellen, dass die erforderlichen Spalten existieren
    DatabaseManager.ensure_required_columns_exist()

    # Session-State initialisieren
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    # Anmeldestatus prüfen
    if not st.session_state.logged_in:
        # Passwort-Wiederherstellung anzeigen, falls angefordert
        if "show_password_reset" in st.session_state and st.session_state.show_password_reset:
            UIComponents.show_password_reset_page()
        else:
            # Ansonsten Login-Seite anzeigen
            UIComponents.show_login_page()
    else:
        # Passwortänderung anzeigen, falls erforderlich
        if "password_change_required" in st.session_state and st.session_state.password_change_required and not st.session_state.get("password_changed", False):
            UIComponents.show_password_change_page()
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
        UIComponents.show_database_management()

# Ticketsystem anzeigen
def show_ticket_system():
    st.title("🎫 Ticketsystem")

    # Tabs für verschiedene Funktionen
    ticket_tabs = st.tabs(["📋 Ticketübersicht", "✏️ Ticket bearbeiten", "➕ Neues Ticket", "📊 Statistiken", "⚙️ Einstellungen"])

    # Tab: Ticketübersicht
    with ticket_tabs[0]:
        UIComponents.show_ticket_overview()

    # Tab: Ticket bearbeiten
    with ticket_tabs[1]:
        UIComponents.show_ticket_edit_tab()

    # Tab: Neues Ticket
    with ticket_tabs[2]:
        UIComponents.show_new_ticket_form()

    # Tab: Statistiken
    with ticket_tabs[3]:
        UIComponents.show_ticket_statistics()

    # Tab: Einstellungen
    with ticket_tabs[4]:
        UIComponents.show_settings()

# Anwendung starten
if __name__ == "__main__":
    main()