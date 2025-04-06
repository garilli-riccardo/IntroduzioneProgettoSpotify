from flask import Blueprint, render_template
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import plotly.express as px
from services.models import db

analysis_bp = Blueprint('analysis', __name__)

# Inizializzare Spotipy con le credenziali
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id='TUO_CLIENT_ID', client_secret='TUO_CLIENT_SECRET'))

# Funzione per ottenere i dettagli della traccia (ad esempio artisti, album, generi)
def get_track_details(track_id):
    track = sp.track(track_id)
    artist_ids = [artist['id'] for artist in track['artists']]
    artists_data = sp.artists(artist_ids)['artists']
    genres = {genre for artist in artists_data for genre in artist['genres']}
    
    return {
        'track_name': track['name'],
        'artists': [artist['name'] for artist in track['artists']],
        'album': track['album']['name'],
        'genres': list(genres)
    }

# Route per l'analisi dei dati
@analysis_bp.route('/playlist_analysis')
def playlist_analysis():
    # Recuperiamo le tracce salvate nel database
    saved_playlists = db.fetch_query('SELECT id_p FROM Playlist')  # Solo id_p per ora
    
    track_details = []

    # Recuperiamo i dettagli per ogni traccia nelle playlist salvate
    for saved in saved_playlists:
        playlist_id = saved[0]
        try:
            # Ottieni la playlist usando l'API di Spotify
            playlist = sp.playlist_tracks(playlist_id)  # Recupera le tracce dalla playlist
            for track in playlist['items']:
                track_id = track['track']['id']
                track_details.append(get_track_details(track_id))
        except Exception as e:
            print(f"Errore nel recupero delle tracce dalla playlist {playlist_id}: {e}")
    
    # Creiamo un DataFrame con le informazioni sulle tracce
    df = pd.DataFrame(track_details)

    # Analisi: Top 5 artisti più presenti
    artist_count = df.explode('artists')['artists'].value_counts().head(5).reset_index()
    artist_count.columns = ['Artist', 'Count']

    # Analisi: Top 5 album più presenti
    album_count = df['album'].value_counts().head(5).reset_index()
    album_count.columns = ['Album', 'Count']

    # Analisi: Distribuzione dei generi musicali
    genre_count = df.explode('genres')['genres'].value_counts().head(5).reset_index()
    genre_count.columns = ['Genre', 'Count']

    # Creiamo i grafici
    artist_graph = px.bar(artist_count, x='Artist', y='Count', title='Top 5 Artisti Più Presenti')
    album_graph = px.bar(album_count, x='Album', y='Count', title='Top 5 Album Più Presenti')
    genre_graph = px.pie(genre_count, names='Genre', values='Count', title='Distribuzione dei 5 Generi Musicali più ascoltati')

    # Convertiamo i grafici in HTML
    artist_graph_html = artist_graph.to_html(full_html=False)
    album_graph_html = album_graph.to_html(full_html=False)
    genre_graph_html = genre_graph.to_html(full_html=False)

    # Passiamo i grafici alla pagina HTML
    return render_template(
        'analysis.html',
        artist_graph=artist_graph_html,
        album_graph=album_graph_html,
        genre_graph=genre_graph_html
    )
