from flask import Flask, redirect, request, url_for, render_template,session
import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIFY_CLIENT_ID = "870d4ed3b63d47e99031f27e9629b4cd"
SPOTIFY_CLIENT_SECRET = "97fb37e2c66a4629ae529ccbf5412ac0"
SPOTIFY_REDIRECT_URI = "https://5000-garilliricc-introduzion-j216zyof20h.ws-eu117.gitpod.io/callback" 

app = Flask(__name__)
app.secret_key = 'chiave_per_session' 

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-private user-library-read playlist-read-private",  
    show_dialog=True 
)

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()  
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')  
    token_info = sp_oauth.get_access_token(code)  
    session['token_info'] = token_info  
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()  
    return redirect(url_for('login'))

@app.route('/home')
def home():
    token_info = session.get('token_info', None)  # 
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token']) 
    user_info = sp.current_user()  

    playlists = sp.current_user_playlists()['items']

    return render_template('home.html', user_info=user_info, playlists=playlists)  

@app.route('/playlist/<playlist_id>')
def playlist_tracks(playlist_id):
    token_info = session.get('token_info', None)  
    sp = spotipy.Spotify(auth=token_info['access_token'])  

    results = sp.playlist_tracks(playlist_id)
    tracks = results['items'] 

    return render_template('playlist_tracks.html', tracks=tracks)  

if __name__ == '__main__':
    app.run(debug=True)