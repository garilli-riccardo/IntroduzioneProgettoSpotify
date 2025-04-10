from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.models import db, User
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user, LoginManager


acc_bp = Blueprint('local_login', __name__)

@acc_bp.route('/', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['nickname']
        password = request.form['password']

        utenti = db.get_Utente()
        user_data = next((u for u in utenti if u[0] == username), None)

        if user_data:
            stored_nickname, stored_password = user_data

            if stored_password == password:
                user = User(nickname=stored_nickname)
                login_user(user)
                flash("Login effettuato con successo!", "success")
                return redirect(url_for('home.homepage'))
            else:
                flash("Password errata.", "error")
        else:
            flash("Utente non trovato.", "error")

        return redirect(url_for('local_login.login_page'))

    return render_template('login.html')



@acc_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        nickname = request.form['nickname']
        password = request.form['password']

        # Controlliamo se l'utente esiste già
        utenti = db.get_Utente()  # Usa db per accedere agli utenti
        if any(u[0] == nickname for u in utenti):
            flash('Nome utente già esistente!', 'error')
            return redirect(url_for('local_login.register_page'))

        # Salviamo l'utente con password in chiaro
        db.aggiungi_Utente(nickname, password)   
        flash('Registrazione completata con successo!', 'success')
        return redirect(url_for('local_login.login_page'))

    return render_template('register.html')

from flask_login import logout_user

@acc_bp.route('/local_logout')
def local_logout():
    logout_user() 
    return redirect(url_for('local_login.login_page'))  



