from flask import Blueprint, render_template, redirect, url_for, request, flash , session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash 
from services.db import get_db_connection  
from models.user import User




acc_bp = Blueprint('acc_bp', __name__)


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        conn = get_db_connection()
        with conn.cursor() as cursor:
            try:
                cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    message = "Il nome utente è già in uso. Scegli un altro nome utente."
                else:
                    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password_hash))
                    conn.commit()
                    return redirect(url_for("login"))
            except Exception as e:
                conn.rollback()
                message = "Si è verificato un errore durante la registrazione: " + str(e)
        conn.close()

    return render_template("register.html", message=message)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.homepage'))