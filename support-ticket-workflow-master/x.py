import hashlib
import secrets
import time
from sqlalchemy import text
import string
import random
import streamlit as st



# Passwort-Hashing-Funktionen
def generate_salt():
    """Generiert einen zufälligen Salt für das Passwort-Hashing."""
    return secrets.token_hex(16)

def hash_password(password, salt):
    """Hasht ein Passwort mit dem angegebenen Salt."""
    salted_password = password + salt
    password_hash = hashlib.sha256(salted_password.encode()).hexdigest()
    return password_hash

def verify_password(password, stored_hash, salt):
    """Überprüft, ob das eingegebene Passwort korrekt ist."""
    calculated_hash = hash_password(password, salt)
    return calculated_hash == stored_hash

# Funktion zur Generierung eines temporären Passworts
def generate_temp_password(length=12):
    """Generiert ein zufälliges temporäres Passwort."""
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

# Authentifizierungsfunktion
def authenticate_user(username_or_email, password):
    from c import engine
    try:
        # Kleine Verzögerung als Schutz vor Brute-Force-Angriffen
        time.sleep(0.5)

        # Benutzer in der Datenbank suchen
        query = text("""
        SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required 
        FROM mitarbeiter 
        WHERE Name = :username OR Email = :email
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {"username": username_or_email, "email": username_or_email}).fetchone()

        if not result:
            return False, None, False

        user_id, name, stored_hash, salt, password_change_required = result

        # Falls kein Salt vorhanden ist (Altdaten), Passwort direkt vergleichen
        # und bei Erfolg ein Salt generieren und das Passwort hashen
        if not salt:
            if password == stored_hash:
                # Passwort ist korrekt, aber ungehasht - jetzt hashen und speichern
                new_salt = generate_salt()
                new_hash = hash_password(password, new_salt)

                # Datensatz aktualisieren
                update_query = text("""
                UPDATE mitarbeiter 
                SET Password_hash = :password_hash, salt = :salt 
                WHERE ID_Mitarbeiter = :user_id
                """)

                with engine.begin() as conn:
                    conn.execute(update_query, {
                        "password_hash": new_hash,
                        "salt": new_salt,
                        "user_id": user_id
                    })

                return True, user_id, password_change_required
            else:
                return False, None, False

        # Ansonsten mit Salt hashen und vergleichen
        if verify_password(password, stored_hash, salt):
            return True, user_id, password_change_required
        else:
            return False, None, False

    except Exception as e:
        st.error(f"Fehler bei der Authentifizierung: {str(e)}")
        return False, None, False
