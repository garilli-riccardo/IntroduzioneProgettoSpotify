from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
import re
from flask_login import login_user, LoginManager

acc_bp = Blueprint('local_login', __name__)

@acc_bp.route('/', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['nickname']
        password = request.form['password']

        utenti = db.get_Utente()
        user_data = next((u for u in utenti if u[0] == username), None)

        if not user_data or user_data is None:
            flash("Utente non trovato. Registrati prima!", "error")
            return redirect(url_for('local_login.login_page'))

        stored_nickname, stored_password_hash = user_data

        if check_password_hash(stored_password_hash, password):
            user = User(nickname=stored_nickname)
            login_user(user)
            return redirect(url_for('home.homepage'))
        else:
            flash("Password errata.", "error")

        return redirect(url_for('local_login.login_page'))
        
    return render_template('login.html')

@acc_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']

        # Controllo se l'utente esiste già
        utenti = db.get_Utente()
        if any(u[0] == nickname for u in utenti):
            flash('Nome utente già esistente, scegli un altro nickname.', 'error')
            return redirect(url_for('local_login.register_page'))

        # Validazione password
        if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[^A-Za-z0-9]', password):
            flash('La password deve essere di almeno 6 caratteri, contenere una lettera maiuscola e un carattere speciale.', 'error')
            return redirect(url_for('local_login.register_page'))

        # Cripta la password
        password_hash = generate_password_hash(password)
        db.aggiungi_Utente(nickname, password_hash)

        flash('Registrazione completata con successo! Ora puoi accedere.', 'success')
        return redirect(url_for('local_login.login_page'))

    return render_template('register.html')



from flask_login import logout_user

@acc_bp.route('/local_logout')
def local_logout():
    logout_user() 
    return redirect(url_for('local_login.login_page'))  



