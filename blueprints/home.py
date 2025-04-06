from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_login import login_required, current_user
import spotipy
from services.spotify_api import (
    sp_public,
    get_spotify_object,
    get_user_info,
    get_user_playlists,
    get_playlist_tracks,
    get_track_details,
    sp_oauth
)
from services.models import db
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd

home_bp = Blueprint('home', __name__, template_folder='templates')

@home_bp.route('/homepage')
def homepage():
    token_info = session.get('token_info')
    user_sp = None
    user_info = None
    playlists = []
    saved_playlists = []

    if token_info and not current_user.is_authenticated:
        sp = get_spotify_object(token_info)
        user_sp = get_user_info(token_info)
        playlists = get_user_playlists(token_info)
        user_info = {'display_name': user_sp['display_name']}

    elif current_user.is_authenticated and not token_info:
        user_info = {'display_name': current_user.nickname}
        saved_playlists = db.fetch_query('SELECT * FROM Playlist WHERE nickname = ?', (current_user.nickname,))
        for saved in saved_playlists:
            playlist_id = saved[0]
            try:
                playlists.append(sp_public.playlist(playlist_id))
            except Exception as e:
                print(f"Errore nel recupero della playlist {playlist_id}: {e}")

    elif token_info and current_user.is_authenticated:
        # Entrambi: Spotify + Flask
        sp = get_spotify_object(token_info)
        user_sp = get_user_info(token_info)
        playlists = get_user_playlists(token_info)
        user_info = {'display_name': user_sp['display_name']}
        
        saved_playlists = db.fetch_query('SELECT * FROM Playlist WHERE nickname = ?', (current_user.nickname,))
        for saved in saved_playlists:
            playlist_id = saved[0]
            try:
                playlist_data = sp_public.playlist(playlist_id)
                if not any(pl['id'] == playlist_data['id'] for pl in playlists):
                    playlists.append(playlist_data)
            except Exception as e:
                print(f"Errore nel recupero della playlist {playlist_id}: {e}")

    return render_template('home.html', user_sp=user_sp, user_info=user_info, playlists=playlists)

@home_bp.route('/cerca')
def cerca():
    query = request.args.get('query', '')
    results = []
    if query:
        try:
            results = sp_public.search(q=query, type='playlist', limit=10)['playlists']['items']
        except Exception as e:
            flash('Errore nella ricerca delle playlist')
            print(e)
    return render_template('home.html', results=results, user_info=None, playlists=[])

@home_bp.route('/saved_playlist', methods=['POST'])
def saved_playlist():
    if not current_user.is_authenticated:
        return redirect(url_for('login.html'))

    playlist_id = request.form.get('playlist_id')
    playlist_name = request.form.get('playlist_name')

    existing = db.fetch_query('SELECT * FROM Playlist WHERE id_p = ? AND nickname = ?', (playlist_id, current_user.nickname))
    if not existing:
        db.execute_query('INSERT INTO Playlist (id_p, nickname) VALUES (?, ?)',
                         (playlist_id,  current_user.nickname))
        flash('Playlist salvata con successo!')
    else:
        flash('Hai già salvato questa playlist.')
    return redirect(url_for('home.homepage'))

@home_bp.route('/remove_playlist', methods=['POST'])
def remove_playlist():
    if not current_user.is_authenticated:
        return redirect(url_for('login.html'))

    db.execute_query('DELETE FROM Playlist WHERE nickname = ?', (current_user.nickname,))
    flash('Tutte le playlist rimosse!')
    return redirect(url_for('home.homepage'))

@home_bp.route('/visualizza_brani/<playlist_id>')
def visualizza_brani(playlist_id):
    token_info = session.get('token_info')
    
    if token_info:
        sp = get_spotify_object(token_info)
    else:
        sp = sp_public  # Usa accesso pubblico se l'utente non ha fatto login a Spotify

    try:
        playlist = sp.playlist(playlist_id)
        tracks = playlist['tracks']['items']
        playlist_name = playlist['name']
        return render_template('brani.html', tracks=tracks, playlist_name=playlist_name)
    except Exception as e:
        print(f"Errore nel caricamento della playlist {playlist_id}: {e}")
        return redirect(url_for('home.homepage'))  # Fallback in caso di errore


@home_bp.route('/albuminfo/<album_id>')
def albuminfo(album_id):
    token_info = session.get('token_info')

    if token_info:
        sp = get_spotify_object(token_info)
    else:
        sp = sp_public  # Accesso pubblico se non autenticato

    try:
        album = sp.album(album_id)

        album_data = {
            "name": album['name'],
            "release_date": album['release_date'],
            "total_tracks": album['total_tracks'],
            "image": album['images'][0]['url'] if album['images'] else None,
            "artists": [{"name": artist["name"], "id": artist["id"]} for artist in album["artists"]],
            "tracks": [{"name": track["name"], "duration_ms": track["duration_ms"]} for track in album["tracks"]["items"]]
        }

        return render_template('albuminfo.html', album_data=album_data)

    except Exception as e:
        print(f"Errore nel caricamento dell'album {album_id}: {e}")
        return redirect(url_for('home.homepage'))  # Torna alla home in caso di errore

@home_bp.route('/artistinfo/<artist_id>')
def artistinfo(artist_id):
    token_info = session.get('token_info')

    # Se loggato usa get_spotify_object, altrimenti sp_public
    sp = get_spotify_object(token_info) if token_info else sp_public

    try:
        artist = sp.artist(artist_id)
        top_tracks = sp.artist_top_tracks(artist_id, country='IT')['tracks']
        albums = sp.artist_albums(artist_id, album_type='album', country='IT')['items']

        artist_data = {
            "name": artist['name'],
            "genres": artist.get('genres', []),
            "image": artist['images'][0]['url'] if artist['images'] else None,
            "top_tracks": [{"name": track["name"], "preview_url": track["preview_url"]} for track in top_tracks[:5]],
            "albums": [{"name": album["name"], "image": album["images"][0]['url']} for album in albums[:3]]
        }

        return render_template('artistinfo.html', artist_data=artist_data)

    except Exception as e:
        print(f"Errore nel recupero delle info dell'artista {artist_id}: {e}")
        return redirect(url_for('home.homepage'))



























"""

def tokenpubblico():
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
    ))

home_bp = Blueprint('home', __name__)



@home_bp.route('/remove_playlist', methods=['POST'])
def remove_playlist():
    if not current_user.is_authenticated:
        return redirect(url_for('home.homepage'))
     
     # Rimuovi la playlist dal database
    db.svuota_Playlist
     
    return redirect(url_for('home.homepage'))



# Home page con gestione del token pubblico
@home_bp.route('/homepage')
def homepage():
    token_info = session.get('token_info', None)
    
    if token_info:
        sp = get_spotify_object(token_info)
        user_sp = sp.current_user()  # Dettagli utente Spotify
        playlists = sp.current_user_playlists()['items']
        user_info = None  # Non utilizzare user_info di Flask-Login se sei loggato su Spotify
    else:
        # Usa il client pubblico di Spotify
        sp = tokenpubblico()  
        user_sp = None  # Nessuna informazione di Spotify
        user_info = {'display_name': current_user.nickname} if current_user.is_authenticated else None
        
        # Recupera le playlist salvate nel database per l'utente loggato tramite Flask-Login
        saved_playlists = db.fetch_query('SELECT * FROM Playlist WHERE nickname = ?', (current_user.nickname,))
        playlists = []
        for saved_playlist in saved_playlists:
            playlist_id = saved_playlist[0]  # id_p della playlist salvata
            # Recupera i dettagli della playlist tramite il client pubblico
            playlist_details = sp.playlist(playlist_id)  # Usa un client pubblico se non è autenticato con Spotify
            playlists.append(playlist_details)
    
    return render_template('home.html', user_sp=user_sp, user_info=user_info, playlists=playlists)

# Visualizza brani della playlist
@home_bp.route('/playlist_tracks/<playlist_id>')
def playlist_tracks(playlist_id):
    Visualizza i brani di una playlist.
    token_info = session.get('token_info', None)
    
    if not token_info:
        return redirect(url_for('auth.login'))  # Reindirizza se l'utente non è loggato
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    try:
        # Ottenere i dettagli della playlist
        playlist = sp.playlist(playlist_id)
        tracks = playlist['tracks']['items']
        playlist_name = playlist['name']
    except Exception as e:
        flash(f"Errore nel recupero dei brani della playlist: {e}", "danger")
        return redirect(url_for('home.homepage'))
    
    return render_template('brani.html', tracks=tracks, playlist_name=playlist_name)


# Salva playlist tra i preferiti
@home_bp.route('/saved_playlist', methods=['POST'])
@login_required
def saved_playlist():
    Salva una playlist tra i preferiti nel DB SQLite per l'utente loggato.
    
    playlist_id = request.form.get('playlist_id')
    
    if not playlist_id:
        flash("Errore: Playlist ID non trovato", "danger")
        return redirect(url_for('home.homepage'))

    # Prendi il nickname dell'utente loggato
    nickname = current_user.get_id()

    # Usa l'API di Spotify per ottenere i dettagli della playlist
    sp = spotipy.Spotify(auth=session.get('token_info')['access_token'])
    try:
        playlist = sp.playlist(playlist_id)  # Ottieni la playlist da Spotify
    except Exception as e:
        flash(f"Errore nel recupero della playlist: {e}", "danger")
        return redirect(url_for('home.homepage'))

    playlist_name = playlist['name']  # Nome della playlist

    # Verifica se la combinazione playlist_id e nickname esiste già nel DB
    existing = db.fetch_query(
        'SELECT * FROM Playlist WHERE id_p = ? AND nickname = ?',
        (playlist_id, nickname)
    )

    if not existing:  # Se la combinazione non esiste, aggiungi la playlist
        db.aggiungi_Playlist(playlist_id, nickname)
        flash(f"La playlist '{playlist_name}' è stata aggiunta ai preferiti!", "success")
    else:
        flash(f"La playlist '{playlist_name}' è già nei tuoi preferiti.", "info")

    # Redirect alla homepage dopo l'aggiunta
    return redirect(url_for('home.homepage'))


@home_bp.route('/cerca', methods=['GET'])
def cerca():

    query = request.args.get('query')
    token_info = session.get('token_info', None)

    if not query:
        return render_template('search.html', results=None)

    # Usa il client pubblico se non è loggato
    if token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        playlists = sp.current_user_playlists()['items']
    else:
        sp = tokenpubblico()  # Usa il client pubblico
        user_info = None
        playlists = sp.search(q=query, type='playlist', limit=10)['playlists']['items']
    
    return render_template('home.html', query=query, results=playlists)


    
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

"""
"""
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
"""




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