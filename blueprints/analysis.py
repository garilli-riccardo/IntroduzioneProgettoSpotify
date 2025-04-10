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
from spotipy.oauth2 import SpotifyClientCredentials 
import pandas as pd
import plotly.express as px
from services.models import db

analysis_bp = Blueprint('analysis', __name__)

sp = sp_public


def get_track_details(track_id):
    playlists = []

    # Controllo se l'utente è autenticato
    if current_user.is_authenticated:
        user_info = current_user.nickname
        # Recupero le playlist salvate dall'utente
        saved_playlists = db.fetch_query(
            'SELECT * FROM Playlist WHERE nickname = ?', 
            (current_user.nickname,)
        )

        for saved in saved_playlists:
            playlist_id = saved[0]
            try:
                # Recupero i dati della playlist
                playlist_data = sp_public.playlist(playlist_id)
                playlists.append(playlist_data)
            except Exception as e:
                print(f"Errore nel recupero della playlist {playlist_id}: {e}")
    else:
        print("Utente non autenticato.")

    try:
        # Recupero i dettagli della traccia
        track = sp.track(track_id)
        
        # Estrazione degli ID degli artisti dalla traccia
        artist_ids = [artist['id'] for artist in track['artists'] if artist.get('id')]
        
        # Recupero dei dati degli artisti
        artists_data = sp.artists(artist_ids)['artists'] if artist_ids else []
        
        # Recupero dei generi musicali degli artisti
        genres = {genre for artist in artists_data for genre in artist.get('genres', [])}

        # Costruzione del dizionario con i dettagli della traccia
        return {
            'track_id': track_id,
            'track_name': track.get('name', 'Traccia sconosciuta'),
            'artists': [a.get('name', 'Sconosciuto') for a in track.get('artists', [])],
            'album': track.get('album', {}).get('name', 'Album sconosciuto'),
            'genres': list(genres),
            'popularity': track.get('popularity', 0),
            'release_year': track.get('album', {}).get('release_date', '1900')[:4],
            'user_playlists': playlists  # Lista delle playlist dell'utente
        }
    except Exception as e:
        print(f"Errore recuperando dettagli per {track_id}: {e}")
        return {}


@analysis_bp.route('/playlist_analysis')
@login_required
def playlist_analysis():
    # Recupera le playlist dell'utente
    playlists = db.fetch_query('SELECT id_p FROM Playlist WHERE nickname = ?', (current_user.nickname,))


    if len(playlists) < 2:
        return "Sono necessarie almeno due playlist per effettuare l'analisi."

    playlist_data = {}
    playlist_names = []

    for i, playlist in enumerate(playlists[:2]):  # Analizza solo le prime due playlist
        playlist_id = playlist[0]
        track_info = []
        try:
            playlist_metadata = sp.playlist(playlist_id)  # Recupere le informazioni della playlist
            playlist_name = playlist_metadata.get('name', f'Playlist {i+1}')
            playlist_names.append(playlist_name)

            tracks = playlist_metadata['tracks']['items']
            for item in tracks:
                track = item.get('track')
                if track and track.get('id'):
                    details = get_track_details(track['id'])  # Dettagli della traccia
                    if details:
                        track_info.append(details)
        except Exception as e:
            print(f"Errore con playlist {playlist_id}: {e}")
            playlist_names.append(f'Playlist {i+1}')

        playlist_data[f'playlist_{i+1}'] = pd.DataFrame(track_info)

    # Converte i dati in DataFrame
    df1, df2 = playlist_data['playlist_1'], playlist_data['playlist_2']

    # Calcolare i brani in comune e la similarità
    common_tracks = set(df1['track_name']) & set(df2['track_name'])
    similarity = len(common_tracks) / min(len(df1), len(df2)) * 100 if min(len(df1), len(df2)) > 0 else 0
    similarity_df = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1], 'Comuni'],
        'Numero Brani': [len(df1), len(df2), len(common_tracks)]
    })
    similarity_chart = px.bar(similarity_df, x='Playlist', y='Numero Brani',
                              title=f'Brani in comune (Somiglianza: {similarity:.2f}%)')

    # Artisti in comune e frequenza
    a1 = df1.explode('artists')['artists']
    a2 = df2.explode('artists')['artists']
    common_artists = set(a1) & set(a2)
    artist_freq = pd.DataFrame({
        'Artista': list(common_artists),
        f'Frequenza {playlist_names[0]}': [a1.tolist().count(a) for a in common_artists],
        f'Frequenza {playlist_names[1]}': [a2.tolist().count(a) for a in common_artists]
    })
    artist_chart = px.bar(artist_freq.melt(id_vars='Artista', var_name='Playlist', value_name='Frequenza'),
                          x='Artista', y='Frequenza', color='Playlist', barmode='group',
                          title='Artisti in comune e frequenze')

    # Confronto della popolarità media
    pop_data = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1]],
        'Popolarità Media': [df1['popularity'].mean(), df2['popularity'].mean()]
    })
    pop_chart = px.bar(pop_data, x='Playlist', y='Popolarità Media', title='Confronto Popolarità Media')

    # Confronto dei generi musicali
    g1 = df1.explode('genres')['genres']
    g2 = df2.explode('genres')['genres']
    genre_freq = pd.DataFrame({
        'Genere': list(set(g1) | set(g2)),
        playlist_names[0]: [g1.tolist().count(g) for g in set(g1) | set(g2)],
        playlist_names[1]: [g2.tolist().count(g) for g in set(g1) | set(g2)]
    })
    genre_chart = px.bar(genre_freq.melt(id_vars='Genere', var_name='Playlist', value_name='Frequenza'),
                         x='Genere', y='Frequenza', color='Playlist', barmode='group',
                         title='Confronto dei Generi Musicali')

    # Distribuzione temporale dei brani
    df1['release_year'] = pd.to_numeric(df1['release_year'], errors='coerce')
    df2['release_year'] = pd.to_numeric(df2['release_year'], errors='coerce')
    year_df = pd.concat([
        df1[['release_year']].assign(Playlist=playlist_names[0]),
        df2[['release_year']].assign(Playlist=playlist_names[1])
    ])
    time_chart = px.histogram(year_df, x='release_year', color='Playlist', barmode='overlay',
                              title='Distribuzione Temporale dei Brani')

    # Analisi generali (Top Artisti, Album, Generi)
    combined_df = pd.concat([df1, df2])

    # Top 5 artisti
    top_artists = combined_df.explode('artists')['artists'].value_counts().head(5).reset_index()
    top_artists.columns = ['Artista', 'Occorrenze']
    top_artists_chart = px.bar(top_artists, x='Artista', y='Occorrenze', title='Top 5 Artisti Più Presenti')

    # Top 5 album
    top_albums = combined_df['album'].value_counts().head(5).reset_index()
    top_albums.columns = ['Album', 'Occorrenze']
    top_albums_chart = px.bar(top_albums, x='Album', y='Occorrenze', title='Top 5 Album Più Presenti')

    # Distribuzione generi
    top_genres = combined_df.explode('genres')['genres'].value_counts().head(5).reset_index()
    top_genres.columns = ['Genere', 'Occorrenze']
    top_genres_chart = px.pie(top_genres, names='Genere', values='Occorrenze', title='Top 5 Generi Musicali')

    # Ritorna il template passando tutti i grafici al template
    return render_template(
        'analysis.html',
        similarity_chart=similarity_chart.to_html(full_html=False),
        artist_chart=artist_chart.to_html(full_html=False),
        pop_chart=pop_chart.to_html(full_html=False),
        genre_chart=genre_chart.to_html(full_html=False),
        time_chart=time_chart.to_html(full_html=False),
        top_artists_chart=top_artists_chart.to_html(full_html=False),
        top_albums_chart=top_albums_chart.to_html(full_html=False),
        top_genres_chart=top_genres_chart.to_html(full_html=False),
        playlist_names=playlist_names  
    )



"""
    try:
        track = sp.track(track_id)
        artist_ids = [artist['id'] for artist in track['artists'] if artist.get('id')]
        artists_data = sp.artists(artist_ids)['artists'] if artist_ids else []
        genres = {genre for artist in artists_data for genre in artist.get('genres', [])}

        return {
            'track_id': track_id,
            'track_name': track.get('name', 'Traccia sconosciuta'),
            'artists': [a.get('name', 'Sconosciuto') for a in track.get('artists', [])],
            'album': track.get('album', {}).get('name', 'Album sconosciuto'),
            'genres': list(genres),
            'popularity': track.get('popularity', 0),
            'release_year': track.get('album', {}).get('release_date', '1900')[:4]
        }
    except Exception as e:
        print(f"Errore recuperando dettagli per {track_id}: {e}")
        return {}

@analysis_bp.route('/playlist_analysis')
def playlist_analysis():
    playlists = db.fetch_query('SELECT id_p FROM Playlist')
    if len(playlists) < 2:
        return "Sono necessarie almeno due playlist."

    playlist_data = {}
    playlist_names = []

    for i, playlist in enumerate(playlists[:2]):
        playlist_id = playlist[0]
        track_info = []
        try:
            playlist_metadata = sp.playlist(playlist_id)
            playlist_name = playlist_metadata.get('name', f'Playlist {i+1}')
            playlist_names.append(playlist_name)

            tracks = playlist_metadata['tracks']['items']
            for item in tracks:
                track = item.get('track')
                if track and track.get('id'):
                    details = get_track_details(track['id'])
                    if details:
                        track_info.append(details)
        except Exception as e:
            print(f"Errore con playlist {playlist_id}: {e}")
            playlist_names.append(f'Playlist {i+1}')

        playlist_data[f'playlist_{i+1}'] = pd.DataFrame(track_info)

    df1, df2 = playlist_data['playlist_1'], playlist_data['playlist_2']

    # Brani in comune
    common_tracks = set(df1['track_name']) & set(df2['track_name'])
    similarity = len(common_tracks) / min(len(df1), len(df2)) * 100 if min(len(df1), len(df2)) > 0 else 0
    similarity_df = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1], 'Comuni'],
        'Numero Brani': [len(df1), len(df2), len(common_tracks)]
    })
    similarity_chart = px.bar(similarity_df, x='Playlist', y='Numero Brani',
                              title=f'Brani in comune (Somiglianza: {similarity:.2f}%)')

    # Artisti in comune
    a1 = df1.explode('artists')['artists']
    a2 = df2.explode('artists')['artists']
    common_artists = set(a1) & set(a2)
    artist_freq = pd.DataFrame({
        'Artista': list(common_artists),
        f'Frequenza {playlist_names[0]}': [a1.tolist().count(a) for a in common_artists],
        f'Frequenza {playlist_names[1]}': [a2.tolist().count(a) for a in common_artists]
    })
    artist_chart = px.bar(artist_freq.melt(id_vars='Artista', var_name='Playlist', value_name='Frequenza'),
                          x='Artista', y='Frequenza', color='Playlist', barmode='group',
                          title='Artisti in comune e frequenze')

    # Popolarità media
    pop_data = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1]],
        'Popolarità Media': [df1['popularity'].mean(), df2['popularity'].mean()]
    })
    pop_chart = px.bar(pop_data, x='Playlist', y='Popolarità Media', title='Confronto Popolarità Media')

    # Generi musicali
    g1 = df1.explode('genres')['genres']
    g2 = df2.explode('genres')['genres']
    genre_freq = pd.DataFrame({
        'Genere': list(set(g1) | set(g2)),
        playlist_names[0]: [g1.tolist().count(g) for g in set(g1) | set(g2)],
        playlist_names[1]: [g2.tolist().count(g) for g in set(g1) | set(g2)]
    })
    genre_chart = px.bar(genre_freq.melt(id_vars='Genere', var_name='Playlist', value_name='Frequenza'),
                         x='Genere', y='Frequenza', color='Playlist', barmode='group',
                         title='Confronto dei Generi Musicali')

    # Distribuzione temporale
    df1['release_year'] = pd.to_numeric(df1['release_year'], errors='coerce')
    df2['release_year'] = pd.to_numeric(df2['release_year'], errors='coerce')
    year_df = pd.concat([
        df1[['release_year']].assign(Playlist=playlist_names[0]),
        df2[['release_year']].assign(Playlist=playlist_names[1])
    ])
    time_chart = px.histogram(year_df, x='release_year', color='Playlist', barmode='overlay',
                              title='Distribuzione Temporale dei Brani')

    # Analisi generali (Top Artisti, Album, Generi)
    combined_df = pd.concat([df1, df2])

    # Top 5 artisti
    top_artists = combined_df.explode('artists')['artists'].value_counts().head(5).reset_index()
    top_artists.columns = ['Artista', 'Occorrenze']
    top_artists_chart = px.bar(top_artists, x='Artista', y='Occorrenze', title='Top 5 Artisti Più Presenti')

    # Top 5 album
    top_albums = combined_df['album'].value_counts().head(5).reset_index()
    top_albums.columns = ['Album', 'Occorrenze']
    top_albums_chart = px.bar(top_albums, x='Album', y='Occorrenze', title='Top 5 Album Più Presenti')

    # Distribuzione generi
    top_genres = combined_df.explode('genres')['genres'].value_counts().head(5).reset_index()
    top_genres.columns = ['Genere', 'Occorrenze']
    top_genres_chart = px.pie(top_genres, names='Genere', values='Occorrenze', title='Top 5 Generi Musicali')

    return render_template(
        'analysis.html',
        similarity_chart=similarity_chart.to_html(full_html=False),
        artist_chart=artist_chart.to_html(full_html=False),
        pop_chart=pop_chart.to_html(full_html=False),
        genre_chart=genre_chart.to_html(full_html=False),
        time_chart=time_chart.to_html(full_html=False),
        top_artists_chart=top_artists_chart.to_html(full_html=False),
        top_albums_chart=top_albums_chart.to_html(full_html=False),
        top_genres_chart=top_genres_chart.to_html(full_html=False)
    )

"""