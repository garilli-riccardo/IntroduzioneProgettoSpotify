import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

SPOTIFY_CLIENT_ID = "4acc6335a0c14f53839704d9454494de"
SPOTIFY_CLIENT_SECRET = "8af9e9866d40447c8cf7081a2748adb4"
SPOTIFY_REDIRECT_URI = "https://5000-garilliricc-introduzion-1cs02dvmh22.ws-eu118.gitpod.io/callback" 
SPOTIFY_SCOPE = "user-read-private user-read-email playlist-read-private"

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