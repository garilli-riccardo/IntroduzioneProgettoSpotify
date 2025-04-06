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

        utenti = db.get_Utente()  # Ora puoi usare db perché è stato importato
        user_data = next((u for u in utenti if u[0] == username), None)  # Cerca l'utente per nickname
        
        if user_data:
            stored_nickname, stored_password = user_data  # stored_password è la password memorizzata

            if stored_password == password:  # Confronta direttamente le password
                user = User(nickname=stored_nickname)  # Assumendo che User sia correttamente definito
                login_user(user)
                flash("Login effettuato!", "success")
                return redirect(url_for('home.homepage'))
        
        flash("Credenziali non valide.", "error")
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
        db.aggiungi_Utente(nickname, password)  # Salva la password in chiaro
        flash('Registrazione completata con successo!', 'success')
        return redirect(url_for('local_login.login_page'))

    return render_template('register.html')
