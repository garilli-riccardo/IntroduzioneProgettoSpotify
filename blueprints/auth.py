from flask import Blueprint, redirect, request, url_for, session
from services.spotify_api import sp_oauth
import spotipy
from spotipy.oauth2 import SpotifyOAuth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@auth_bp.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('home.homepage'))

@auth_bp.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('home.homepage')) 
