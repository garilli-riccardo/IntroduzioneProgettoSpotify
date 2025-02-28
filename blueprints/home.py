from flask import Blueprint, render_template, session, redirect, url_for, request
import spotipy
from services.spotify_oauth import sp_public, get_spotify_object, sp_oauth
import requests

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def homepage():
    token_info = session.get('token_info', None)
    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        playlists = sp.current_user_playlists()['items']
    else:
        user_info = None 
        playlists = None 

    return render_template('home.html', user_info=user_info, playlists=playlists)

@home_bp.route('/playlist.html/<playlist_id>')
def playlist_tracks(playlist_id):
    session['current_playlist_id'] = playlist_id
    token_info = session.get('token_info',None)
    if not token_info:
        return redirect(url_for('auth.login'))  
    sp = spotipy.Spotify(auth=token_info['access_token'])
    tracks = sp.playlist_tracks(playlist_id)['items']

    return render_template('playlist.html', tracks=tracks)
@home_bp.route('/cerca', methods=['GET'])
def cerca():

    query = request.args.get('query')
    token_info = session.get('token_info', None)
    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        playlists = sp.current_user_playlists()['items']
    else:
        sp = sp_public  
        sp = get_spotify_object(token_info)
        playlists = sp.current_user_playlists()['items'] 
        user_info = None  

    if not query:
        return render_template('search.html', results=None)

    results = sp.search(q=query, type='playlist', limit=50)
    playlists = results['playlists']['items']
    return render_template('home.html', user_info=user_info, results=playlists)


@home_bp.route('/albuminfo/<album_id>', methods=['GET'])
def albuminfo(album_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('auth.login'))
    sp = spotipy.Spotify(auth=token_info['access_token'])
    album_info = sp.album(album_id)
    album_data = {
        "name": album_info['name'],
        "release_date": album_info['release_date'],
        "total_tracks": album_info['total_tracks'],
        "image": album_info['images'][0]['url'] if album_info['images'] else None,
        "artists": [{"name": artist["name"], "id": artist["id"]} for artist in album_info["artists"]],
        "tracks": [{"name": track["name"], "duration_ms": track["duration_ms"]} for track in album_info["tracks"]["items"]]
    }
    return render_template('albuminfo.html', album_data=album_data)

@home_bp.route('/artistinfo/<artist_id>', methods=['GET'])
def artistinfo(artist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('auth.login'))
    sp = spotipy.Spotify(auth=token_info['access_token'])
    artist_info = sp.artist(artist_id)
    top_tracks = sp.artist_top_tracks(artist_id, country="IT")['tracks']
    albums = sp.artist_albums(artist_id, album_type='album', country="IT")['items']
    artist_data = {
        "name": artist_info['name'],
        "genres": artist_info['genres'],
        "image": artist_info['images'][0]['url'] if artist_info['images'] else None,
        "top_tracks": [{"name": track["name"], "preview_url": track["preview_url"]} for track in top_tracks[:5]],
        "albums": [{"name": album["name"], "image": album["images"][0]['url']} for album in albums[:3]],
    }
    return render_template('artistinfo.html', artist_data=artist_data)
'''
def get_related_artists(artist_id):
    
    # Endpoint dell'API
    token_info = session.get('token_info', None)

    if not token_info:
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    url = f"https://api.spotify.com/v1/artists/{artist_id}/related-artists"

    # Intestazione della richiesta
    headers = {
        "Authorization": f"Bearer {sp}"
    }

    # Fai la richiesta GET
    response = requests.get(url, headers=headers)

    # Controlla se la richiesta è andata a buon fine
    if response.status_code == 200:
        # Estrai i dati degli artisti correlati
        related_artists = response.json()["artists"]
        return related_artists
    else:
        # Stampa l'errore se la richiesta non è andata a buon fine
        print(f"Errore: {response.status_code}")
        return None
        '''