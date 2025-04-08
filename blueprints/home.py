

from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_login import login_required, current_user
import spotipy
import requests
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
import plotly.express as px
import mypysql
 
home_bp = Blueprint('home', __name__, template_folder='templates')
 
@home_bp.route('/homepage')
def homepage():
     token_info = session.get('token_info')
     user_sp = None
     user_info = None
     playlists = []
     saved_playlists = []
 
     if token_info and not current_user.is_authenticated:
         # Solo Spotify
         sp = get_spotify_object(token_info)
         user_sp = get_user_info(token_info)
         playlists = get_user_playlists(token_info)
         user_info = {'display_name': user_sp['display_name']}
 
     elif current_user.is_authenticated and not token_info:
         # Solo autenticato su Flask
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
                 # Evita duplicati (es. se la playlist è già tra quelle Spotify)
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

    if token_info:
        sp = get_spotify_object(token_info)
    else:
        sp = sp_public  # Accesso pubblico se non autenticato

    try:
        artist = sp.artist(artist_id)
        top_tracks = sp.artist_top_tracks(artist_id, country='IT')['tracks']
        albums = sp.artist_albums(artist_id, album_type='album', country='IT')['items']

        # Preparazione dei dati dell'artista
        artist_data = {
            "name": artist['name'],
            "genres": artist.get('genres', []),
            "image": artist['images'][0]['url'] if artist['images'] else None,
            "top_tracks": [{"name": track["name"], "preview_url": track["preview_url"]} for track in top_tracks], 
            "albums": [{"name": album["name"], "image": album["images"][0]['url']} for album in albums]  
        }

        return render_template('artistinfo.html', artist_data=artist_data)

    except Exception as e:
        print(f"Errore nel recupero delle info dell'artista {artist_id}: {e}")
        return redirect(url_for('home.homepage'))
 
 
 
@home_bp.route('/remove_single_playlist', methods=['POST'])
@login_required
def remove_single_playlist():
    playlist_id = request.form.get('playlist_id')
    if playlist_id:
        db.execute_query('DELETE FROM Playlist WHERE id_p = ? AND nickname = ?', (playlist_id, current_user.nickname))
        flash('Playlist rimossa con successo!')
    else:
        flash('Errore: Playlist non trovata.')
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
         user_info = sp.current_user()
         user_sp = sp.current_user()  # Dettagli utente Spotify
         playlists = sp.current_user_playlists()['items']
         user_info = None  # Non utilizzare user_info di Flask-Login se sei loggato su Spotify
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
 
 @home_bp.route('/playlist.html/<playlist_id>')
 # Visualizza brani della playlist
 @home_bp.route('/playlist_tracks/<playlist_id>')
 def playlist_tracks(playlist_id):
     Visualizza i brani di una playlist.
     token_info = session.get('token_info', None)
     
     session['current_playlist_id'] = playlist_id
     token_info = session.get('token_info',None)
     if not token_info:
         return redirect(url_for('auth.login'))  
         return redirect(url_for('auth.login'))  # Reindirizza se l'utente non è loggato
     
     sp = spotipy.Spotify(auth=token_info['access_token'])
     tracks = sp.playlist_tracks(playlist_id)['items']
     
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
 
 
     return render_template('playlist.html', tracks=tracks)
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
 @@ -146,7 +434,8 @@ def view_saved_playlists():
 
     return render_template('saved_playlists.html', playlists=playlists, message=message)
 
 
"""
"""
 def playlist_analysis():
     message = ""
     user_id = current_user.id
 @@ -188,7 +477,7 @@ def playlist_analysis():
     genre_fig = px.pie(genre_distribution, names=genre_distribution.index, values=genre_distribution.values, title='Distribuzione dei generi musicali')
     
     return render_template('playlist_analysis.html', artist_fig=artist_fig.to_html(), album_fig=album_fig.to_html(), genre_fig=genre_fig.to_html(), message=message)
"""