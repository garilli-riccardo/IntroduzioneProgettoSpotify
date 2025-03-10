import spotipy
from flask_login import LoginManager

from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

SPOTIFY_CLIENT_ID = "870d4ed3b63d47e99031f27e9629b4cd"
SPOTIFY_CLIENT_SECRET = "97fb37e2c66a4629ae529ccbf5412ac0"
SPOTIFY_REDIRECT_URI = "https://5000-garilliricc-introduzion-yma8atev1hy.ws-eu118.gitpod.io/callback" 
SPOTIFY_SCOPE = "user-read-private user-read-email playlist-read-private"

login_manager = LoginManager()
login_manager.init_app(app)

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope=SPOTIFY_SCOPE,
    show_dialog=True
)

sp_public = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID ,
    client_secret=SPOTIFY_CLIENT_SECRET
))

def get_spotify_object(token_info=None):
    if token_info:
        return spotipy.Spotify(auth=token_info['access_token'])
    return sp_public  

def get_user_playlists(token_info=None):
    return sp.get_spotify_object(token_info = None).current_user_playlists[items]