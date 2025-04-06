import spotipy
from flask_login import LoginManager

from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials

SPOTIFY_CLIENT_ID = "4acc6335a0c14f53839704d9454494de"
SPOTIFY_CLIENT_SECRET = "8af9e9866d40447c8cf7081a2748adb4"
SPOTIFY_REDIRECT_URI = "https://5000-garilliricc-introduzion-7gmx3duads9.ws-eu118.gitpod.io/callback" 
SPOTIFY_SCOPE = "user-read-private user-read-email playlist-read-private"

""" login_manager = LoginManager()
login_manager.init_app(app) """

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
    return spotipy.Spotify(auth=token_info['access_token']) if token_info else sp_public


def get_user_info(token_info):
    return get_spotify_object(token_info).current_user()

def get_user_playlists(token_info):
    return get_spotify_object(token_info).current_user_playlists()['items']

def get_playlist_tracks(token_info, playlist_id):
    try:
        response = get_spotify_object(token_info).playlist_tracks(playlist_id)
        return response.get('items', []) if response else [] 
    except Exception as e:
        print(f"Errore nel recupero dei brani della playlist {playlist_id}: {e}")
        return [] 

def get_track_details(token_info, track_id):
    sp = get_spotify_object(token_info)
    track = sp.track(track_id)
    artist_details = sp.artist(track['artists'][0]['id'])
    
    genres = artist_details.get('genres', [])
    if genres:
        genre = genres[0]
    else:
        genre = 'Genere sconosciuto'

    return track, genre

def get_all_tracks(token_info):
    sp = get_spotify_object(token_info)
    playlists = get_user_playlists(token_info)
    tracks_data = []
    
    for playlist in playlists:
        playlist_id = playlist['id']
        tracks = get_playlist_tracks(token_info, playlist_id)
        
        for track in tracks:
            track_info = track['track']
            tracks_data.append({
                'track_name': track_info['name'],
                'artist': track_info['artists'][0]['name'],
                'album': track_info['album']['name'],
                'genre': track_info['album'].get('genres', ['Sconosciuto'])[0]
            })
    
    return pd.DataFrame(tracks_data)