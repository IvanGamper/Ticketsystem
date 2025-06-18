"""
Einfache E-Mail-Funktion für das Ticketsystem:
- Senden von E-Mail-Benachrichtigungen
- Empfangen von E-Mails und Erstellen von Tickets
"""

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import re
from datetime import datetime
import threading
import time
from sqlalchemy import text

# E-Mail-Konfiguration
EMAIL_CONFIG = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "imap_host": "imap.example.com",
    "imap_port": 993,
    "username": "tickets@example.com",
    "password": "YourSecurePassword",
    "check_interval": 5  # Minuten
}

def setup_email_system(engine):
    """
    Einrichtung des E-Mail-Systems: Sendet und empfängt E-Mails für das Ticketsystem.
    
    Args:
        engine: SQLAlchemy-Engine für Datenbankzugriff
        
    Returns:
        thread: Der gestartete Hintergrund-Thread für E-Mail-Empfang
    """
    # Thread für E-Mail-Empfang starten
    def email_receiver_thread():
        while True:
            try:
                # Verbindung zum IMAP-Server herstellen
                mail = imaplib.IMAP4_SSL(EMAIL_CONFIG["imap_host"], EMAIL_CONFIG["imap_port"])
                mail.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
                mail.select("INBOX")
                
                # Nach ungelesenen E-Mails suchen
                status, messages = mail.search(None, "UNSEEN")
                if status == "OK" and messages[0]:
                    message_ids = messages[0].split()
                    print(f"{len(message_ids)} neue E-Mails gefunden.")
                    
                    for msg_id in message_ids:
                        # E-Mail abrufen und verarbeiten
                        status, msg_data = mail.fetch(msg_id, "(RFC822)")
                        if status == "OK":
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            
                            # E-Mail-Daten extrahieren
                            subject = msg.get("Subject", "")
                            if subject:
                                decoded = decode_header(subject)
                                if decoded[0][1]:
                                    subject = decoded[0][0].decode(decoded[0][1])
                                else:
                                    subject = decoded[0][0]
                                    if isinstance(subject, bytes):
                                        subject = subject.decode()
                            
                            sender = msg.get("From", "")
                            sender_email = re.search(r'<([^>]+)>', sender)
                            if sender_email:
                                sender_email = sender_email.group(1)
                            else:
                                sender_email = sender
                            
                            # E-Mail-Inhalt extrahieren
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    if content_type == "text/plain":
                                        try:
                                            body = part.get_payload(decode=True).decode()
                                            break
                                        except:
                                            pass
                            else:
                                try:
                                    body = msg.get_payload(decode=True).decode()
                                except:
                                    body = "Inhalt konnte nicht dekodiert werden."
                            
                            # Ticket erstellen
                            create_ticket_from_email(engine, subject, body, sender_email)
                            
                            # E-Mail als gelesen markieren
                            mail.store(msg_id, "+FLAGS", "\\Seen")
                
                # Verbindung schließen
                mail.logout()
                
            except Exception as e:
                print(f"Fehler beim E-Mail-Empfang: {str(e)}")
            
            # Warten bis zum nächsten Check
            time.sleep(EMAIL_CONFIG["check_interval"] * 60)
    
    # Thread starten
    thread = threading.Thread(target=email_receiver_thread, daemon=True)
    thread.start()
    print(f"E-Mail-System gestartet. Prüft alle {EMAIL_CONFIG['check_interval']} Minuten auf neue E-Mails.")
    
    return thread

def create_ticket_from_email(engine, subject, body, sender_email):
    """
    Erstellt ein Ticket aus einer empfangenen E-Mail.
    
    Args:
        engine: SQLAlchemy-Engine
        subject: Betreff der E-Mail
        body: Inhalt der E-Mail
        sender_email: Absender-E-Mail
        
    Returns:
        int: Ticket-ID oder None bei Fehler
    """
    try:
        # Standardwerte für neue Tickets
        status_id = 1  # Annahme: 1 = Neu/Offen
        prioritaet = "Mittel"
        
        # Kunde anhand der E-Mail-Adresse suchen oder Standard-Kunde verwenden
        kunde_id = 1  # Standard-Kunde-ID
        query = text("SELECT ID_Kunde FROM kunde WHERE Email = :email LIMIT 1")
        
        with engine.connect() as conn:
            result = conn.execute(query, {"email": sender_email}).fetchone()
            if result:
                kunde_id = result[0]
        
        # Ticket in die Datenbank einfügen
        insert_query = text("""
            INSERT INTO ticket 
            (Titel, Beschreibung, Status_ID, Prioritaet, ID_Kunde, Erstellt_am) 
            VALUES 
            (:titel, :beschreibung, :status_id, :prioritaet, :kunde_id, :erstellt_am)
        """)
        
        with engine.begin() as conn:
            result = conn.execute(insert_query, {
                "titel": subject or "E-Mail-Ticket",
                "beschreibung": body or "Keine Beschreibung",
                "status_id": status_id,
                "prioritaet": prioritaet,
                "kunde_id": kunde_id,
                "erstellt_am": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            ticket_id = result.lastrowid
            
            # Bestätigungs-E-Mail senden
            send_email(
                sender_email,
                f"Ticket #{ticket_id} wurde erstellt",
                f"Ihr Ticket mit dem Betreff '{subject}' wurde erfolgreich erstellt.\n\n" +
                f"Ticket-ID: {ticket_id}\n" +
                f"Status: Neu\n" +
                f"Priorität: {prioritaet}\n\n" +
                f"Wir werden uns so schnell wie möglich um Ihr Anliegen kümmern.\n\n" +
                f"Mit freundlichen Grüßen,\nIhr Ticketsystem"
            )
            
            print(f"Ticket aus E-Mail erstellt: ID {ticket_id}, Titel: {subject}")
            return ticket_id
            
    except Exception as e:
        print(f"Fehler beim Erstellen des Tickets aus E-Mail: {str(e)}")
        return None

def send_email(recipient, subject, body, is_html=False):
    """
    Sendet eine E-Mail.
    
    Args:
        recipient: Empfänger-E-Mail-Adresse
        subject: Betreff
        body: Inhalt (Text oder HTML)
        is_html: Ob der Inhalt HTML ist
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # E-Mail erstellen
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG["username"]
        msg['To'] = recipient
        msg['Subject'] = subject
        
        # Inhalt hinzufügen
        content_type = 'html' if is_html else 'plain'
        msg.attach(MIMEText(body, content_type))
        
        # Verbindung zum SMTP-Server herstellen
        server = smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(EMAIL_CONFIG["username"], EMAIL_CONFIG["password"])
        
        # E-Mail senden
        server.send_message(msg)
        server.quit()
        
        print(f"E-Mail an {recipient} gesendet: {subject}")
        return True
        
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {str(e)}")
        return False

def send_ticket_notification(engine, ticket_id, notification_type):
    """
    Sendet eine Benachrichtigung über ein Ticket.
    
    Args:
        engine: SQLAlchemy-Engine
        ticket_id: ID des Tickets
        notification_type: Art der Benachrichtigung ('created', 'updated', 'comment')
        
    Returns:
        bool: True bei Erfolg, False bei Fehler
    """
    try:
        # Ticket-Daten abrufen
        query = text("""
            SELECT t.Titel, t.Beschreibung, t.Prioritaet, s.Name as Status, 
                   k.Name as Kunde, k.Email as KundenEmail
            FROM ticket t
            JOIN status s ON t.Status_ID = s.ID_Status
            JOIN kunde k ON t.ID_Kunde = k.ID_Kunde
            WHERE t.ID_Ticket = :ticket_id
        """)
        
        with engine.connect() as conn:
            ticket = conn.execute(query, {"ticket_id": ticket_id}).fetchone()
            
            if not ticket:
                print(f"Ticket mit ID {ticket_id} nicht gefunden.")
                return False
            
            # Betreff und Inhalt basierend auf Benachrichtigungstyp
            if notification_type == "created":
                subject = f"Neues Ticket #{ticket_id}: {ticket.Titel}"
                body = f"Ein neues Ticket wurde erstellt:\n\n" + \
                       f"Ticket-ID: {ticket_id}\n" + \
                       f"Titel: {ticket.Titel}\n" + \
                       f"Status: {ticket.Status}\n" + \
                       f"Priorität: {ticket.Prioritaet}\n" + \
                       f"Kunde: {ticket.Kunde}\n\n" + \
                       f"Beschreibung:\n{ticket.Beschreibung}"
            
            elif notification_type == "updated":
                subject = f"Ticket #{ticket_id} wurde aktualisiert: {ticket.Titel}"
                body = f"Das Ticket wurde aktualisiert:\n\n" + \
                       f"Ticket-ID: {ticket_id}\n" + \
                       f"Titel: {ticket.Titel}\n" + \
                       f"Status: {ticket.Status}\n" + \
                       f"Priorität: {ticket.Prioritaet}\n" + \
                       f"Kunde: {ticket.Kunde}"
            
            elif notification_type == "comment":
                subject = f"Neuer Kommentar zu Ticket #{ticket_id}: {ticket.Titel}"
                body = f"Ein neuer Kommentar wurde zum Ticket hinzugefügt:\n\n" + \
                       f"Ticket-ID: {ticket_id}\n" + \
                       f"Titel: {ticket.Titel}\n" + \
                       f"Status: {ticket.Status}\n" + \
                       f"Priorität: {ticket.Prioritaet}\n" + \
                       f"Kunde: {ticket.Kunde}"
            
            else:
                print(f"Unbekannter Benachrichtigungstyp: {notification_type}")
                return False
            
            # Zuständige Mitarbeiter finden
            mitarbeiter_query = text("""
                SELECT m.Name, m.Email
                FROM ticket_mitarbeiter tm
                JOIN mitarbeiter m ON tm.ID_Mitarbeiter = m.ID_Mitarbeiter
                WHERE tm.ID_Ticket = :ticket_id
            """)
            
            mitarbeiter = conn.execute(mitarbeiter_query, {"ticket_id": ticket_id}).fetchall()
            
            # E-Mails senden
            success = True
            
            # An Mitarbeiter senden
            for m in mitarbeiter:
                if m.Email:
                    if not send_email(m.Email, subject, body):
                        success = False
            
            # An Kunden senden (optional)
            if ticket.KundenEmail and notification_type in ["created", "updated"]:
                kunde_subject = f"Ihr Ticket #{ticket_id}: {ticket.Titel}"
                kunde_body = f"Sehr geehrte(r) {ticket.Kunde},\n\n" + \
                             f"Ihr Ticket mit der ID {ticket_id} wurde {'erstellt' if notification_type == 'created' else 'aktualisiert'}.\n\n" + \
                             f"Titel: {ticket.Titel}\n" + \
                             f"Status: {ticket.Status}\n" + \
                             f"Priorität: {ticket.Prioritaet}\n\n" + \
                             f"Wir werden uns so schnell wie möglich um Ihr Anliegen kümmern.\n\n" + \
                             f"Mit freundlichen Grüßen,\nIhr Ticketsystem"
                
                if not send_email(ticket.KundenEmail, kunde_subject, kunde_body):
                    success = False
            
            return success
            
    except Exception as e:
        print(f"Fehler beim Senden der Ticket-Benachrichtigung: {str(e)}")
        return False

# Beispiel für die Integration in das Hauptprogramm:
"""
# Am Anfang des Programms:
from simple_email_function import setup_email_system, send_ticket_notification

# E-Mail-System starten
email_thread = setup_email_system(engine)

# Bei Ticket-Erstellung:
def create_ticket(...):
    # ... bestehender Code ...
    
    # Benachrichtigung senden
    send_ticket_notification(engine, ticket_id, "created")
    
    # ... Rest des Codes ...

# Bei Ticket-Aktualisierung:
def update_ticket(...):
    # ... bestehender Code ...
    
    # Benachrichtigung senden
    send_ticket_notification(engine, ticket_id, "updated")
    
    # ... Rest des Codes ...
"""
