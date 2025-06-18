# Refaktorisierter Code zur Reduktion von Codezeilen und besserer Wartbarkeit

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timedelta
import hashlib, secrets, time, string, random

# -----------------------------
# Konfiguration & DB-Verbindung
# -----------------------------
DB_CONFIG = dict(user="root", password="Xyz1343!!!", host="127.0.0.1", port="3306", db="ticketsystemabkoo")
engine = create_engine(f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['db']}")
inspector = inspect(engine)

# -----------------------------
# Hilfsfunktionen für die DB
# -----------------------------
def get_columns(table):
    try: return [col["name"] for col in inspector.get_columns(table)]
    except: return []

def get_primary_key(table):
    try:
        pk = inspector.get_pk_constraint(table)
        if pk.get('constrained_columns'): return pk['constrained_columns'][0]
        cols = get_columns(table)
        return cols[0] if cols else None
    except: return None

def get_column_types(table):
    try: return {col["name"]: str(col["type"]) for col in inspector.get_columns(table)}
    except: return {}

# -----------------------------
# Passwort & Authentifizierung
# -----------------------------
def generate_salt(): return secrets.token_hex(16)

def hash_password(pw, salt): return hashlib.sha256((pw + salt).encode()).hexdigest()

def verify_password(pw, stored_hash, salt): return hash_password(pw, salt) == stored_hash

def generate_temp_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    base = [random.choice(set) for set in [string.ascii_lowercase, string.ascii_uppercase, string.digits, "!@#$%^&*"]]
    base += random.choices(chars, k=length-4)
    random.shuffle(base)
    return ''.join(base)

# -----------------------------
# Allgemeine DB-Funktionen
# -----------------------------
def add_entity(table, fields):
    with engine.begin() as conn:
        cols = ', '.join(fields)
        vals = ', '.join([f":{k}" for k in fields])
        conn.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"), fields)

# -----------------------------
# Benutzerbezogene Funktionen
# -----------------------------
def authenticate_user(username_or_email, password):
    try:
        time.sleep(0.5)
        user = engine.execute(text("""
            SELECT ID_Mitarbeiter, Name, Password_hash, salt, password_change_required 
            FROM mitarbeiter 
            WHERE Name = :user OR Email = :user
        """), {"user": username_or_email}).fetchone()
        if not user: return False, None, False

        user_id, _, stored_hash, salt, change_required = user
        if not salt and password == stored_hash:
            salt = generate_salt()
            hashed = hash_password(password, salt)
            engine.execute(text("""
                UPDATE mitarbeiter SET Password_hash = :h, salt = :s WHERE ID_Mitarbeiter = :id
            """), {"h": hashed, "s": salt, "id": user_id})
            return True, user_id, change_required

        if verify_password(password, stored_hash, salt):
            return True, user_id, change_required
        return False, None, False
    except Exception as e:
        st.error(f"Login-Fehler: {e}")
        return False, None, False

def reset_password(email):
    try:
        user = engine.execute(text("SELECT ID_Mitarbeiter, Name FROM mitarbeiter WHERE Email = :email"), {"email": email}).fetchone()
        if not user: return False, None, None
        pw = generate_temp_password()
        salt = generate_salt()
        pw_hash = hash_password(pw, salt)
        expiry = datetime.now() + timedelta(hours=24)
        engine.execute(text("""
            UPDATE mitarbeiter SET Password_hash = :pw_hash, salt = :salt,
            reset_token = :token, reset_token_expiry = :expiry, password_change_required = TRUE
            WHERE ID_Mitarbeiter = :id"""),
                       {"pw_hash": pw_hash, "salt": salt, "token": secrets.token_hex(16), "expiry": expiry, "id": user[0]})
        return True, user[1], pw
    except Exception as e:
        st.error(f"Fehler beim Passwort-Reset: {str(e)}")
        return False, None, None

def change_password(user_id, new_pw):
    try:
        salt = generate_salt()
        pw_hash = hash_password(new_pw, salt)
        engine.execute(text("""
            UPDATE mitarbeiter SET Password_hash = :pw_hash, salt = :salt,
            reset_token = NULL, reset_token_expiry = NULL, password_change_required = FALSE
            WHERE ID_Mitarbeiter = :id
        """), {"pw_hash": pw_hash, "salt": salt, "id": user_id})
        return True
    except Exception as e:
        st.error(f"Fehler beim Passwortwechsel: {e}")
        return False

# -----------------------------
# UI: Login + Passwort-Reset
# -----------------------------
def show_login():
    st.title("🔐 Login")
    with st.form("login_form"):
        user = st.text_input("Benutzername oder E-Mail")
        pw = st.text_input("Passwort", type="password")
        if st.form_submit_button("Anmelden"):
            if not user or not pw:
                st.error("Bitte alle Felder ausfüllen.")
            else:
                success, user_id, change_pw = authenticate_user(user, pw)
                if success:
                    st.session_state.update({"logged_in": True, "user_id": user_id, "password_change_required": change_pw})
                    st.success("Login erfolgreich")
                    st.rerun()
                else:
                    st.error("Login fehlgeschlagen.")

    if st.button("Passwort vergessen?"):
        st.session_state.show_reset = True
        st.rerun()

def show_reset():
    st.title("🔑 Passwort zurücksetzen")
    with st.form("reset_form"):
        email = st.text_input("E-Mail")
        if st.form_submit_button("Zurücksetzen"):
            ok, name, pw = reset_password(email)
            if ok:
                st.success("Temporäres Passwort generiert.")
                st.info(f"{name}, dein temporäres Passwort lautet: {pw}")
            else:
                st.error("E-Mail nicht gefunden.")
    if st.button("Zurück zum Login"):
        st.session_state.show_reset = False
        st.rerun()

# -----------------------------
# App Startpunkt
# -----------------------------
def main():
    st.set_page_config("Ticketsystem", "🎫", layout="wide")
    for key in ["logged_in", "show_reset", "password_change_required"]:
        st.session_state.setdefault(key, False)

    if st.session_state.show_reset:
        show_reset()
    elif not st.session_state.logged_in:
        show_login()
    elif st.session_state.password_change_required:
        st.warning("Bitte Passwort ändern (nicht implementiert in Kurzfassung).")
    else:
        st.success("Erfolgreich eingeloggt.")

if __name__ == "__main__":
    main()
