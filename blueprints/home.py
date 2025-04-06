from flask import Blueprint, render_template, session, redirect, url_for, request
from flask_login import login_required
import spotipy
from services.spotify_api import sp_public, get_spotify_object, sp_oauth, get_user_playlists
import requests
import pandas as pd
import plotly.express as px
import mypysql


home_bp = Blueprint('home', __name__)


@home_bp.route('/homepage')
def homepage():
    token_info = session.get('token_info', None)

    if token_info:
        sp = get_spotify_object(token_info)
        user_info = sp.current_user()
        playlists = sp.current_user_playlists()['items']
    else:
        user_info = None
        playlists = None

    return render_template('home.html', user_info=user_info, playlists=playlists)

def save_playlist(user_id, playlist_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('''INSERT INTO user_playlists (user_id, playlist_id) VALUES (%s, %s)''', (user_id, playlist_id))
        conn.commit()
    conn.close()

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

@home_bp.route('/visualizza_brani/<playlist_id>')
def visualizza_brani(playlist_id):
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Ottenere i dettagli della playlist per estrarre il nome
    playlist = sp.playlist(playlist_id)  
    tracks = playlist['tracks']['items']
    playlist_name = playlist['name']

    return render_template('brani.html', tracks=tracks, playlist_name=playlist_name)

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




def view_saved_playlists():
    sp = get_spotify_client()
    playlists = []
    message = ""

    if current_user.is_authenticated:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute('SELECT playlist_id FROM saved_playlists WHERE user_id = %s', (current_user.id,))
                rows = cursor.fetchall()
            conn.close()
            playlist_ids = [row['playlist_id'] for row in rows]
        except Exception as e:
            message = f"Errore nel recupero delle playlist salvate: {e}"
            playlist_ids = []
    else:
        playlist_ids = session.get('saved_playlists', [])

    # Recupera dettagli playlist da Spotify
    for pid in playlist_ids:
        try:
            playlists.append(sp.playlist(pid))
        except Exception as e:
            message = f"Errore nel recupero della playlist {pid}: {e}"

    return render_template('saved_playlists.html', playlists=playlists, message=message)


def playlist_analysis():
    message = ""
    user_id = current_user.id
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute('''SELECT p.id, p.name, p.image FROM playlists p
                          JOIN user_playlists up ON p.id = up.playlist_id
                          WHERE up.user_id = %s''', (user_id,))
        playlists = cursor.fetchall()
    
    if not playlists:
        message = "Non hai playlist salvate."
        return render_template('playlist_analysis.html', message=message)
    
    tracks_data = []
    for playlist in playlists:
        cursor.execute('''SELECT t.track_name, t.artist_name, t.album_name, t.genre FROM tracks t
                          JOIN playlist_tracks pt ON t.id = pt.track_id
                          WHERE pt.playlist_id = %s''', (playlist['id'],))
        tracks = cursor.fetchall()
        
        for track in tracks:
            tracks_data.append(track)
    
    conn.close()
    
    if not tracks_data:
        message = "Le playlist non contengono tracce."
        return render_template('playlist_analysis.html', message=message)
    
    df = pd.DataFrame(tracks_data)
    top_artists = df['artist_name'].value_counts().head(5)
    top_albums = df['album_name'].value_counts().head(5)
    genre_distribution = df['genre'].value_counts()
    
    artist_fig = px.bar(top_artists, x=top_artists.index, y=top_artists.values, labels={'x': 'Artista', 'y': 'Numero di brani'})
    album_fig = px.bar(top_albums, x=top_albums.index, y=top_albums.values, labels={'x': 'Album', 'y': 'Numero di brani'})
    genre_fig = px.pie(genre_distribution, names=genre_distribution.index, values=genre_distribution.values, title='Distribuzione dei generi musicali')
    
    return render_template('playlist_analysis.html', artist_fig=artist_fig.to_html(), album_fig=album_fig.to_html(), genre_fig=genre_fig.to_html(), message=message)





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