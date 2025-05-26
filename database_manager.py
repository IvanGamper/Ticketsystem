import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timedelta
import hashlib
import secrets
import time
import string
import random

class DatabaseManager:
    """
    Klasse für alle Datenbankoperationen und Authentifizierungsfunktionen.
    Enthält Methoden für Datenbankzugriff, Benutzerauthentifizierung und Datenmanipulation.
    """
    
    def __init__(self, db_user, db_password, db_host, db_port, db_name):
        """
        Initialisiert den DatabaseManager mit Datenbankverbindungsparametern.
        
        Args:
            db_user: Datenbankbenutzer
            db_password: Datenbankpasswort
            db_host: Datenbankhost
            db_port: Datenbankport
            db_name: Datenbankname
        """
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        
        # Verbindung zur Datenbank herstellen
        self.setup_database_connection()

    def get_status_options(self):
        query = "SELECT Name FROM status ORDER BY ID_Status"
        df = pd.read_sql(query, con=self.engine)
        return df["Name"].tolist()

    def get_mitarbeiter_options(self):
        query = "SELECT Name FROM mitarbeiter ORDER BY Name"
        df = pd.read_sql(query, con=self.engine)
        return df["Name"].tolist()

    def get_kunden_options(self):
        query = "SELECT Name FROM kunden ORDER BY Name"
        df = pd.read_sql(query, con=self.engine)
        return df["Name"].tolist()

    def get_kategorien_options(self):
        query = "SELECT Name FROM kategorien ORDER BY Name"
        df = pd.read_sql(query, con=self.engine)
        return df["Name"].tolist()

    def get_prioritaeten_options(self):
        query = "SELECT DISTINCT Priorität FROM tickets ORDER BY FIELD(Priorität, 'Hoch', 'Mittel', 'Niedrig')"
        df = pd.read_sql(query, con=self.engine)
        return df["Priorität"].dropna().tolist()


    def setup_database_connection(self):
        """
        Stellt die Verbindung zur Datenbank her und initialisiert den Inspector.
        """
        try:
            # Verbindungsstring erstellen
            connection_string = f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            
            # Engine erstellen
            self.engine = create_engine(connection_string)
            
            # Verbindung testen
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Inspector für Metadaten
            self.inspector = inspect(self.engine)
            
            return True
        except Exception as e:
            print(f"Fehler bei der Datenbankverbindung: {str(e)}")
            return False
    
    def get_columns(self, table):
        """
        Gibt die Spaltennamen einer Tabelle zurück.
        
        Args:
            table: Name der Tabelle
            
        Returns:
            list: Liste der Spaltennamen
        """
        try:
            return [col["name"] for col in self.inspector.get_columns(table)]
        except Exception as e:
            print(f"Fehler beim Abrufen der Spalten: {str(e)}")
            return []
    
    def get_primary_key(self, table):
        """
        Ermittelt den Primärschlüssel einer Tabelle.
        
        Args:
            table: Name der Tabelle
            
        Returns:
            str: Name der Primärschlüsselspalte oder None
        """
        try:
            pk = self.inspector.get_pk_constraint(table)
            if pk and 'constrained_columns' in pk and pk['constrained_columns']:
                return pk['constrained_columns'][0]
            
            # Fallback: Suche nach Spalten mit 'id' im Namen
            columns = self.get_columns(table)
            for col in columns:
                if col.lower() == 'id':
                    return col
            
            # Zweiter Fallback: Erste Spalte
            if columns:
                return columns[0]
            
            return None
        except Exception as e:
            print(f"Fehler beim Ermitteln des Primärschlüssels: {str(e)}")
            return None
    
    def get_column_types(self, table):
        """
        Gibt die Spaltentypen einer Tabelle zurück.
        
        Args:
            table: Name der Tabelle
            
        Returns:
            dict: Dictionary mit Spaltenname als Schlüssel und Spaltentyp als Wert
        """
        try:
            return {col["name"]: str(col["type"]) for col in self.inspector.get_columns(table)}
        except Exception as e:
            print(f"Fehler beim Abrufen der Spaltentypen: {str(e)}")
            return {}
    
    def get_table_names(self):
        """
        Gibt die Namen aller Tabellen in der Datenbank zurück.
        
        Returns:
            list: Liste der Tabellennamen
        """
        try:
            return self.inspector.get_table_names()
        except Exception as e:
            print(f"Fehler beim Abrufen der Tabellennamen: {str(e)}")
            return []
    
    def execute_query(self, query, params=None):
        """
        Führt eine SQL-Abfrage aus.
        
        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage (optional)
            
        Returns:
            bool: Erfolg
        """
        try:
            if params is None:
                params = {}
            
            with self.engine.begin() as conn:
                conn.execute(text(query), params)
            
            return True
        except Exception as e:
            print(f"Fehler bei der Datenbankabfrage: {str(e)}")
            return False
    
    def execute_query_to_df(self, query, params=None):
        """
        Führt eine SQL-Abfrage aus und gibt das Ergebnis als DataFrame zurück.
        
        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage (optional)
            
        Returns:
            pandas.DataFrame: Ergebnis der Abfrage
        """
        try:
            if params is None:
                params = {}
            
            return pd.read_sql(text(query), self.engine, params=params)
        except Exception as e:
            print(f"Fehler bei der Datenbankabfrage: {str(e)}")
            return pd.DataFrame()
    
    def execute_transaction(self, query, params=None):
        """
        Führt eine SQL-Transaktion aus.
        
        Args:
            query: SQL-Abfrage
            params: Parameter für die Abfrage (optional)
            
        Returns:
            bool: Erfolg
        """
        try:
            if params is None:
                params = {}
            
            with self.engine.begin() as conn:
                result = conn.execute(text(query), params)
                return result
        except Exception as e:
            print(f"Fehler bei der Datenbanktransaktion: {str(e)}")
            return None
    
    def create_ticket_relations(self, ticket_id, mitarbeiter_id, kategorie_id=1):
        """
        Erstellt automatisch Einträge in ticket_mitarbeiter und ticket_kategorie.
        
        Args:
            ticket_id: ID des Tickets
            mitarbeiter_id: ID des Mitarbeiters
            kategorie_id: ID der Kategorie (optional, Standard: 1)
            
        Returns:
            bool: Erfolg
        """
        try:
            with self.engine.begin() as conn:
                # Eintrag in ticket_mitarbeiter
                if mitarbeiter_id:
                    # Prüfen, ob der Eintrag bereits existiert
                    check_query = text("SELECT COUNT(*) FROM ticket_mitarbeiter WHERE ID_Ticket = :ticket_id AND ID_Mitarbeiter = :mitarbeiter_id")
                    result = conn.execute(check_query, {"ticket_id": ticket_id, "mitarbeiter_id": mitarbeiter_id}).scalar()
                    
                    if result == 0:  # Eintrag existiert noch nicht
                        insert_query = text("INSERT INTO ticket_mitarbeiter (ID_Ticket, ID_Mitarbeiter, Rolle_im_Ticket) VALUES (:ticket_id, :mitarbeiter_id, 'Hauptverantwortlicher')")
                        conn.execute(insert_query, {"ticket_id": ticket_id, "mitarbeiter_id": mitarbeiter_id})
                
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
            print(f"Fehler beim Erstellen der Ticket-Beziehungen: {str(e)}")
            return False
    
    # Authentifizierungsfunktionen
    
    def generate_salt(self):
        """
        Generiert einen zufälligen Salt für das Passwort-Hashing.
        
        Returns:
            str: Zufälliger Salt
        """
        return secrets.token_hex(16)
    
    def hash_password(self, password, salt):
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
    
    def verify_password(self, password, stored_hash, salt):
        """
        Überprüft, ob das eingegebene Passwort korrekt ist.
        
        Args:
            password: Passwort
            stored_hash: Gespeicherter Hash
            salt: Salt
            
        Returns:
            bool: Passwort korrekt
        """
        calculated_hash = self.hash_password(password, salt)
        return calculated_hash == stored_hash
    
    def generate_temp_password(self, length=12):
        """
        Generiert ein zufälliges temporäres Passwort.
        
        Args:
            length: Länge des Passworts (optional, Standard: 12)
            
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
    
    def authenticate_user(self, username_or_email, password):
        """
        Authentifiziert einen Benutzer anhand von Benutzername/E-Mail und Passwort.
        
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
            query = text("""
            SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required 
            FROM mitarbeiter 
            WHERE Name = :username OR Email = :email
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"username": username_or_email, "email": username_or_email}).fetchone()
            
            if not result:
                return False, None, False
            
            user_id, name, stored_hash, salt, password_change_required = result
            
            # Falls kein Salt vorhanden ist (Altdaten), Passwort direkt vergleichen
            # und bei Erfolg ein Salt generieren und das Passwort hashen
            if not salt:
                if password == stored_hash:
                    # Passwort ist korrekt, aber ungehasht - jetzt hashen und speichern
                    new_salt = self.generate_salt()
                    new_hash = self.hash_password(password, new_salt)
                    
                    # Datensatz aktualisieren
                    update_query = text("""
                    UPDATE mitarbeiter 
                    SET Password_hash = :password_hash, salt = :salt 
                    WHERE ID_Mitarbeiter = :user_id
                    """)
                    
                    with self.engine.begin() as conn:
                        conn.execute(update_query, {
                            "password_hash": new_hash,
                            "salt": new_salt,
                            "user_id": user_id
                        })
                    
                    return True, user_id, password_change_required
                else:
                    return False, None, False
            
            # Ansonsten mit Salt hashen und vergleichen
            if self.verify_password(password, stored_hash, salt):
                return True, user_id, password_change_required
            else:
                return False, None, False
        
        except Exception as e:
            print(f"Fehler bei der Authentifizierung: {str(e)}")
            return False, None, False
    
    def ensure_required_columns_exist(self):
        """
        Überprüft, ob die erforderlichen Spalten existieren, und fügt sie hinzu, falls nicht.
        
        Returns:
            bool: Erfolg
        """
        try:
            # Prüfen, ob die salt-Spalte bereits existiert
            mitarbeiter_columns = self.get_columns("mitarbeiter")
            
            # Salt-Spalte hinzufügen, falls nicht vorhanden
            if "salt" not in mitarbeiter_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN salt VARCHAR(64)"))
            
            # Reset-Token-Spalte hinzufügen, falls nicht vorhanden
            if "reset_token" not in mitarbeiter_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN reset_token VARCHAR(64)"))
            
            # Reset-Token-Expiry-Spalte hinzufügen, falls nicht vorhanden
            if "reset_token_expiry" not in mitarbeiter_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN reset_token_expiry DATETIME"))
            
            # Password-Change-Required-Spalte hinzufügen, falls nicht vorhanden
            if "password_change_required" not in mitarbeiter_columns:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE mitarbeiter ADD COLUMN password_change_required BOOLEAN DEFAULT FALSE"))
            
            return True
        except Exception as e:
            print(f"Fehler beim Überprüfen/Hinzufügen der erforderlichen Spalten: {str(e)}")
            return False
    
    def reset_password(self, email):
        """
        Setzt das Passwort eines Benutzers zurück und generiert ein temporäres Passwort.
        
        Args:
            email: E-Mail-Adresse des Benutzers
            
        Returns:
            tuple: (Erfolg, Name, Temporäres Passwort)
        """
        try:
            # Benutzer in der Datenbank suchen
            query = text("""
            SELECT ID_Mitarbeiter, Name, Email 
            FROM mitarbeiter 
            WHERE Email = :email
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"email": email}).fetchone()
            
            if not result:
                return False, None, None
            
            user_id, name, user_email = result
            
            # Temporäres Passwort generieren
            temp_password = self.generate_temp_password()
            
            # Salt generieren und temporäres Passwort hashen
            salt = self.generate_salt()
            password_hash = self.hash_password(temp_password, salt)
            
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
            
            with self.engine.begin() as conn:
                conn.execute(update_query, {
                    "password_hash": password_hash,
                    "salt": salt,
                    "reset_token": secrets.token_hex(16),  # Zusätzlicher Token für Sicherheit
                    "expiry": expiry,
                    "user_id": user_id
                })
            
            return True, name, temp_password
        
        except Exception as e:
            print(f"Fehler bei der Passwort-Wiederherstellung: {str(e)}")
            return False, None, None
    
    def change_password(self, user_id, new_password):
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
            salt = self.generate_salt()
            password_hash = self.hash_password(new_password, salt)
            
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
            
            with self.engine.begin() as conn:
                conn.execute(update_query, {
                    "password_hash": password_hash,
                    "salt": salt,
                    "user_id": user_id
                })
            
            return True
        
        except Exception as e:
            print(f"Fehler beim Ändern des Passworts: {str(e)}")
            return False
    
    def get_user_name(self, user_id):
        """
        Gibt den Namen eines Benutzers zurück.
        
        Args:
            user_id: Benutzer-ID
            
        Returns:
            str: Name des Benutzers
        """
        try:
            query = text("SELECT Name FROM mitarbeiter WHERE ID_Mitarbeiter = :user_id")
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"user_id": user_id}).fetchone()
            
            if result:
                return result[0]
            else:
                return None
        
        except Exception as e:
            print(f"Fehler beim Abrufen des Benutzernamens: {str(e)}")
            return None
    
    def get_searchable_columns(self, table_name):
        """
        Ermittelt die durchsuchbaren Spalten einer Tabelle.
        
        Args:
            table_name: Name der Tabelle
            
        Returns:
            list: Liste der Spaltennamen
        """
        try:
            columns = self.get_columns(table_name)
            column_types = self.get_column_types(table_name)
            
            # Nur Text- und Zahlenspalten sind sinnvoll durchsuchbar
            searchable_columns = []
            for col in columns:
                col_type = column_types.get(col, "").lower()
                if any(text_type in col_type for text_type in ["char", "text", "varchar"]) or \
                   any(num_type in col_type for num_type in ["int", "decimal", "float", "double"]):
                    searchable_columns.append(col)
            
            return searchable_columns
        except Exception as e:
            print(f"Fehler beim Ermitteln der durchsuchbaren Spalten: {str(e)}")
            return []
    
    def search_table(self, table_name, search_term, search_columns=None, exact_match=False, case_sensitive=False):
        """
        Durchsucht eine Tabelle nach einem Suchbegriff.
        
        Args:
            table_name: Name der Tabelle
            search_term: Suchbegriff
            search_columns: Liste der zu durchsuchenden Spalten (optional)
            exact_match: Ob exakte Übereinstimmung gefordert ist (optional)
            case_sensitive: Ob Groß-/Kleinschreibung beachtet werden soll (optional)
            
        Returns:
            pandas.DataFrame: Gefundene Datensätze
        """
        try:
            if not search_term:
                # Bei leerem Suchbegriff alle Datensätze zurückgeben
                query = f"SELECT * FROM {table_name}"
                return self.execute_query_to_df(query)
            
            # Wenn keine Spalten angegeben sind, alle durchsuchbaren Spalten verwenden
            if search_columns is None or len(search_columns) == 0:
                search_columns = self.get_searchable_columns(table_name)
            
            # Wenn keine durchsuchbaren Spalten gefunden wurden, leeren DataFrame zurückgeben
            if not search_columns:
                return pd.DataFrame()
            
            # SQL-Bedingungen für die Suche erstellen
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
                else:
                    # Teilweise Übereinstimmung (LIKE)
                    if case_sensitive:
                        conditions.append(f"{col} LIKE :{param_name}")
                        params[param_name] = f"%{search_term}%"
                    else:
                        conditions.append(f"LOWER({col}) LIKE :{param_name}")
                        params[param_name] = f"%{search_term.lower()}%"
                
                params[param_name] = f"%{search_term}%" if not exact_match else search_term
            
            # SQL-Query erstellen
            query = f"SELECT * FROM {table_name} WHERE {' OR '.join(conditions)}"
            
            # Query ausführen und Ergebnisse zurückgeben
            return self.execute_query_to_df(query, params)
        
        except Exception as e:
            print(f"Fehler bei der Tabellensuche: {str(e)}")
            return pd.DataFrame()
