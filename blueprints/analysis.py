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
import statsmodels.api as sm
import time 

analysis_bp = Blueprint('analysis', __name__)

sp = sp_public

def apply_spotify_theme(fig):
    fig.update_layout(
        template='plotly_dark',
        plot_bgcolor='#121212',
        paper_bgcolor='#121212',
        font=dict(
            family="Circular, Arial, sans-serif",
            color="#FFFFFF",
            size=16
        ),
        title=dict(
            font=dict(
                size=24,
                color="#1DB954"
            ),
            x=0.5
        ),
        xaxis=dict(
            color='white',
            gridcolor='#333333'
        ),
        yaxis=dict(
            color='white',
            gridcolor='#333333'
        ),
        yaxis_title_font=dict(
            color='white'
        ),
        xaxis_title_font=dict(
            color='white'
        ),
        legend=dict(
            title=None,
            font=dict(color='white'),
            bgcolor='#121212'
        )
    )
    return fig

def get_track_details(track_id):
    playlists = []
    if current_user.is_authenticated:
        saved_playlists = db.fetch_query(
            'SELECT * FROM Playlist WHERE nickname = ?', 
            (current_user.nickname,)
        )
        for saved in saved_playlists:
            playlist_id = saved[0]
            try:
                playlist_data = sp_public.playlist(playlist_id)
                playlists.append(playlist_data)
            except Exception as e:
                print(f"Errore nel recupero della playlist {playlist_id}: {e}")
    else:
        print("Utente non autenticato.")

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
            'release_year': track.get('album', {}).get('release_date', '1900')[:4],
            'duration_ms': track.get('duration_ms', 0),
            'user_playlists': playlists
        }
    except Exception as e:
        print(f"Errore recuperando dettagli per {track_id}: {e}")
        return {}

# Funzione ottimizzata per ottenere tutti i dettagli dei brani
def get_all_track_details(track_ids):
    all_details = []
    for i in range(0, len(track_ids), 50):  # Batch di massimo 50 ID
        batch_ids = track_ids[i:i+50]
        try:
            batch_tracks = sp.tracks(batch_ids)['tracks']
            for track in batch_tracks:
                if track and track.get('id'):
                    details = {
                        'id': track['id'],
                        'name': track['name'],
                        'popularity': track.get('popularity', 0),
                        'artists': [artist['name'] for artist in track.get('artists', [])],
                        'genres': [],  # I generi dei brani non sempre sono disponibili direttamente
                        'release_year': track['album']['release_date'][:4] if track['album'] and track['album'].get('release_date') else None,
                        'track': track
                    }
                    all_details.append(details)
        except Exception as e:
            print(f"Errore durante il recupero dei dettagli dei brani: {e}")
    return all_details

# Route Flask aggiornata
@analysis_bp.route('/confronta_playlist', methods=['POST'])
@login_required
def confronta_playlist():
    selected_playlists = request.form.getlist('playlist')

    if len(selected_playlists) != 2:
        flash('Devi selezionare esattamente due playlist per confrontarle.', 'error')
        return redirect(url_for('analysis.seleziona_playlist'))

    playlist_id_1, playlist_id_2 = selected_playlists

    playlist_data = {}
    playlist_names = []

    for idx, playlist_id in enumerate([playlist_id_1, playlist_id_2]):
        track_info = []
        try:
            playlist_metadata = sp.playlist(playlist_id)
            playlist_name = playlist_metadata.get('name', f'Playlist {idx+1}')
            playlist_names.append(playlist_name)

            # Raccogli TUTTI gli ID dei brani
            track_ids = []
            tracks = playlist_metadata['tracks']['items']
            while tracks:
                for item in tracks:
                    track = item.get('track')
                    if track and track.get('id'):
                        track_ids.append(track['id'])

                # Se ci sono più pagine
                if playlist_metadata['tracks'].get('next'):
                    playlist_metadata['tracks'] = sp.next(playlist_metadata['tracks'])
                    tracks = playlist_metadata['tracks']['items']
                else:
                    tracks = None

            # Ottieni tutti i dettagli
            track_info = get_all_track_details(track_ids)

        except Exception as e:
            print(f"Errore con playlist {playlist_id}: {e}")
            playlist_names.append(f'Playlist {idx+1}')

        playlist_data[f'playlist_{idx+1}'] = pd.DataFrame(track_info)

    df1, df2 = playlist_data['playlist_1'], playlist_data['playlist_2']

    # Assicurati che ci sia 'track_name'
    if 'track_name' not in df1.columns:
        df1['track_name'] = df1['track'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)
    if 'track_name' not in df2.columns:
        df2['track_name'] = df2['track'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)

    # Brani in comune
    common_tracks = set(df1['track_name']) & set(df2['track_name'])
    similarity = len(common_tracks) / min(len(df1), len(df2)) * 100 if min(len(df1), len(df2)) > 0 else 0
    similarity_df = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1], 'Comuni'],
        'Numero Brani': [len(df1), len(df2), len(common_tracks)]
    })
    similarity_chart = apply_spotify_theme(px.bar(similarity_df, x='Playlist', y='Numero Brani',
                                  title=f'Brani in comune (Somiglianza: {similarity:.2f}%)'))

    # Artisti in comune
    a1 = df1.explode('artists')['artists']
    a2 = df2.explode('artists')['artists']
    common_artists = set(a1) & set(a2)
    artist_freq = pd.DataFrame({
        'Artista': list(common_artists),
        f'Frequenza {playlist_names[0]}': [a1.tolist().count(a) for a in common_artists],
        f'Frequenza {playlist_names[1]}': [a2.tolist().count(a) for a in common_artists]
    })
    artist_chart = apply_spotify_theme(px.bar(
        artist_freq.melt(id_vars='Artista', var_name='Playlist', value_name='Frequenza'),
        x='Artista', y='Frequenza', color='Playlist', barmode='group',
        title='Artisti in comune e frequenze'
    ))

    # Popolarità media
    pop_data = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1]],
        'Popolarità Media': [df1['popularity'].mean(), df2['popularity'].mean()]
    })
    pop_chart = apply_spotify_theme(px.bar(
        pop_data, x='Playlist', y='Popolarità Media', title='Confronto Popolarità Media'
    ))

    # Generi musicali (lasciamo vuoti se non li hai, o miglioriamo dopo)
    g1 = df1.explode('genres')['genres']
    g2 = df2.explode('genres')['genres']
    genre_freq = pd.DataFrame({
        'Genere': list(set(g1) | set(g2)),
        playlist_names[0]: [g1.tolist().count(g) for g in set(g1) | set(g2)],
        playlist_names[1]: [g2.tolist().count(g) for g in set(g1) | set(g2)]
    })
    genre_chart = apply_spotify_theme(px.bar(
        genre_freq.melt(id_vars='Genere', var_name='Playlist', value_name='Frequenza'),
        x='Genere', y='Frequenza', color='Playlist', barmode='group',
        title='Confronto dei Generi Musicali'
    ))

    # Anni di pubblicazione
    df1['release_year'] = pd.to_numeric(df1['release_year'], errors='coerce')
    df2['release_year'] = pd.to_numeric(df2['release_year'], errors='coerce')
    year_df = pd.concat([
        df1[['release_year']].assign(Playlist=playlist_names[0]),
        df2[['release_year']].assign(Playlist=playlist_names[1])
    ])
    time_chart = apply_spotify_theme(px.histogram(
        year_df, x='release_year', color='Playlist', barmode='overlay',
        title='Distribuzione Temporale dei Brani'
    ))

    return render_template(
        'confronto.html',
        similarity_chart=similarity_chart.to_html(full_html=False),
        artist_chart=artist_chart.to_html(full_html=False),
        pop_chart=pop_chart.to_html(full_html=False),
        genre_chart=genre_chart.to_html(full_html=False),
        time_chart=time_chart.to_html(full_html=False),
        playlist_names=playlist_names
    )



@analysis_bp.route('/seleziona_playlist', methods=['GET', 'POST'])
@login_required
def seleziona_playlist():
    playlists = db.fetch_query('SELECT id_p, nickname FROM Playlist WHERE nickname = ?', (current_user.nickname,))
    playlist_info = []
    
    # Ottieni metadati per ogni playlist
    for id_p, nickname in playlists:
        try:
            playlist_metadata = sp.playlist(id_p)  # Ottieni i metadati della playlist
            playlist_name = playlist_metadata['name']
            image_url = playlist_metadata['images'][0]['url'] if playlist_metadata['images'] else 'https://fakeimg.pl/250x250/'  # URL dell'immagine o immagine finta
            playlist_info.append((id_p, playlist_name, image_url))
        except Exception as e:
            print(f"Errore con la playlist {id_p}: {e}")
            playlist_info.append((id_p, f'Playlist {nickname}', 'https://fakeimg.pl/250x250/'))  # Se errore, usa immagine finta

    # Gestione del metodo POST (quando invii il modulo)
    if request.method == 'POST':
        selected_playlists = request.form.getlist('playlist')  # Ottieni le playlist selezionate
        
        if len(selected_playlists) != 2:
            flash("Devi selezionare esattamente due playlist per il confronto.", 'error')
            return redirect(url_for('analysis.seleziona_playlist'))  # Ritorna alla stessa pagina
        
        # Procedi con il confronto delle playlist
        return redirect(url_for('analysis.confronta_playlist', selected_playlists=selected_playlists))

    # Renderizza il template con le playlist
    return render_template('seleziona_playlist.html', playlists=playlist_info)




@analysis_bp.route('/single_playlist_analysis', methods=['GET'])
@login_required
def single_playlist_analysis():
    playlist_id = request.args.get('playlist_id')
    query = request.args.get('query')  # <-- aggiunto qui

    if not playlist_id:
        flash('ID playlist non fornito.', 'error')
        return redirect(url_for('home.homepage'))

    try:
        playlist_metadata = sp.playlist(playlist_id)
    except Exception as e:
        flash(f"Errore nel recupero della playlist: {e}", "error")
        return redirect(url_for('home.homepage'))

    playlist_name = playlist_metadata.get('name', 'Playlist Sconosciuta')
    tracks = playlist_metadata['tracks']['items']

    track_info = []
    for item in tracks:
        track = item.get('track')
        if track and track.get('id'):
            details = get_track_details(track['id'])
            if details:
                track_info.append(details)

    if not track_info:
        flash("Nessun brano trovato nella playlist.", "error")
        return redirect(url_for('home.homepage'))

    df = pd.DataFrame(track_info)

    df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce')
    year_chart = px.histogram(df, x='release_year', title='Distribuzione Temporale dei Brani')

    df['duration_min'] = df['duration_ms'] / 60000
    duration_chart = px.histogram(df, x='duration_min', nbins=30, title='Distribuzione della Durata dei Brani (minuti)')

    popularity_chart = px.histogram(df, x='popularity', nbins=20, title='Distribuzione della Popolarità dei Brani')

    genre_series = df.explode('genres')['genres']
    genre_counts = genre_series.value_counts().head(10).reset_index()
    genre_counts.columns = ['genres', 'count']

    genre_chart = px.bar(
        genre_counts,
        x='genres',
        y='count',
        title='Top 10 Generi Musicali'
    )
    genre_chart.update_layout(xaxis_title='Genere', yaxis_title='Numero di Brani')

    evolution_chart = px.scatter(
        df, 
        x='release_year', 
        y='popularity', 
        trendline="ols",
        title='Evoluzione della Popolarità nel Tempo',
        labels={'release_year': 'Anno di Pubblicazione', 'popularity': 'Popolarità'}
    )

    return render_template(
        'analisiplaylistsingola.html',
        playlist_name=playlist_name,
        query=query,
        year_chart=year_chart.to_html(full_html=False),
        duration_chart=duration_chart.to_html(full_html=False),
        popularity_chart=popularity_chart.to_html(full_html=False),
        genre_chart=genre_chart.to_html(full_html=False),
        evolution_chart=evolution_chart.to_html(full_html=False)
    )

