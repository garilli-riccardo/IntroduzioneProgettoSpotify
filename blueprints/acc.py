from flask import Blueprint, render_template, redirect, url_for, request, flash , session
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash 
from services.models import get_db_connection  
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


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    message = "" 
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
        conn.close()

        if user_data:
            if check_password_hash(user_data['password_hash'], password):
                user = User(user_data['id'], user_data['username'], user_data['email'])
                login_user(user)
                message = "Accesso effettuato con successo." 
                return redirect(url_for('home.homepage'))
            else:
                message = "Password errata. Controlla le tue credenziali e riprova." 
        else:
            message = "Utente non trovato. Verifica il tuo username." 

    return render_template('login.html', message=message)  




@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home.homepage'))