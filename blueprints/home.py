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
 
@home_bp.route('/cerca', methods=['GET'])
def cerca():
    query = request.args.get('query', '')
    results = []
    tracks = []
    
    if query:
        try:
            # Ricerca delle playlist su Spotify
            results = sp_public.search(q=query, type='playlist', limit=10)['playlists']['items']
            
            # Se una playlist è selezionata, carica tutti i brani di quella playlist
            playlist_id = request.args.get('playlist_id')
            if playlist_id:
                # Recupera tutti i brani della playlist
                tracks_response = sp_public.playlist_tracks(playlist_id, limit=100)  # Modifica limit se necessario
                tracks = tracks_response['items']
            
        except Exception as e:
            flash('Errore nella ricerca delle playlist')
            print(e)

    return render_template('home.html', results=results, tracks=tracks, user_info=None, playlists=[])

 
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
     return redirect(url_for('home.homepage', playlist_id = playlist_id))
 
@home_bp.route('/remove_playlist', methods=['POST'])
def remove_playlist():
     if not current_user.is_authenticated:
         return redirect(url_for('login.html'))
 
     db.execute_query('DELETE FROM Playlist WHERE nickname = ?', (current_user.nickname,))
     flash('Tutte le playlist rimosse!')
     return redirect(url_for('home.homepage'))
 
@home_bp.route('/visualizza_brani/<playlist_id>', methods=['GET', 'POST'])
def visualizza_brani(playlist_id):
    token_info = session.get('token_info')
    
    query = request.args.get('query', '')  # Capture the search query from the URL
        
    if token_info:
        sp = get_spotify_object(token_info)
    else:
        sp = sp_public  # Usa l'accesso pubblico se non sei loggato 
    # Ottieni lo stato dell'offset dalla sessione
    # backend: ricevi l'offset dalla sessione o dalla query
    offset = session.get('offset', 0)  # recupera l'offset dalla sessione, o usa 0 se non è impostato
    limit = 100  # numero massimo di brani da caricare per richiesta

    response = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)


# aggiorna l'offset per la prossima richiesta
    if len(response['items']) == limit:
        session['offset'] = offset + limit
    else:
        session['offset'] = 0  # resetto quando non ci sono più brani


    
    try:
        # Otteniamo i dettagli della playlist
        playlist = sp.playlist(playlist_id)
        playlist_name = playlist['name']
        
        # Otteniamo l'immagine della playlist
        playlist_image = playlist['images'][0]['url'] if playlist['images'] else url_for('static', filename='img/default_playlist.png')

        # Carica i brani in base all'offset
        tracks = []
        response = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        tracks.extend(response['items'])

        # Se il numero di brani restituiti è inferiore al limite, significa che siamo all'ultima pagina
        has_more_tracks = len(response['items']) == limit

        # Salviamo il nuovo offset (per il prossimo caricamento)
        if has_more_tracks:
            session['offset'] = offset + limit
        else:
            session['offset'] = 0  # Reset offset se siamo alla fine

        return render_template('brani.html', 
                               tracks=tracks, 
                               playlist_name=playlist_name, 
                               playlist_image=playlist_image, 
                               query=query, 
                               has_more_tracks=has_more_tracks)
    
    except Exception as e:
        print(f"Errore nel caricamento della playlist: {e}")
        return render_template('error.html', error_message="Si è verificato un errore.")



 
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
 
@home_bp.route('/suggerimenti', methods=['GET', 'POST'])
def suggerimenti():
    token_info = session.get('token_info')
    if token_info:
        sp = get_spotify_object(token_info)
    else:
        sp = sp_public  # Usa l'accesso pubblico se non sei loggato

    query = request.args.get('query', '')  # Parametro di ricerca (può essere un artista, brano o genere)

    # Ottenere i suggerimenti basati sulla query (se è un artista, brano o genere)
    try:
        if query:
            response = sp.recommendations(seed_artists=[query], limit=10)  # 10 suggerimenti, puoi personalizzare

        else:
            # Usa un set predefinito di artisti, brani o generi se la query è vuota
            response = sp.recommendations(seed_artists=["3Nrfpe0tUJi4K4DXYWgMUX"], limit=10)  # Esempio con un artista

        suggestions = response['tracks']  # Lista dei brani suggeriti

        return render_template('suggerimenti.html', suggestions=suggestions)

    except Exception as e:
        print(f"Errore nel recupero dei suggerimenti: {e}")
        return render_template('error.html', error_message="Si è verificato un errore.")


@home_bp.route('/add_to_playlist', methods=['POST'])
def add_to_playlist():
    token_info = session.get('token_info')
    track_id = request.form.get('track_id')
    
    if token_info:
        sp = get_spotify_object(token_info)
    else:
        return redirect(url_for('auth.login'))  # Redirigi se l'utente non è loggato
    
    try:
        # Creiamo una playlist nuova o aggiungiamo a quella esistente
        user_id = sp.current_user()['id']
        playlist_id = session.get('playlist_id')  # Usa la playlist salvata nella sessione o creane una nuova

        # Se non c'è una playlist id, creiamo una nuova playlist
        if not playlist_id:
            playlist = sp.user_playlist_create(user_id, "Nuova Playlist")
            playlist_id = playlist['id']
            session['playlist_id'] = playlist_id  # Salva l'ID della nuova playlist nella sessione

        # Aggiungiamo il brano alla playlist
        sp.user_playlist_add_tracks(user_id, playlist_id, [track_id])

        return redirect(url_for('home.suggerimenti'))  # Torna alla pagina dei suggerimenti

    except Exception as e:
        print(f"Errore nell'aggiunta alla playlist: {e}")
        return render_template('error.html', error_message="Si è verificato un errore.")
