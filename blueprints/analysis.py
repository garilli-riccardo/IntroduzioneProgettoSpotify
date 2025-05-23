from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_login import login_required, current_user
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
import plotly.express as px
import statsmodels.api as sm
import time
from concurrent.futures import ThreadPoolExecutor

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

def get_track_details(track_id, user_playlists=None):
    playlists = user_playlists or []

    try:
        track = sp.track(track_id)
        artist_ids = [artist['id'] for artist in track['artists'] if artist.get('id')]
        artists_data = sp.artists(artist_ids)['artists'] if artist_ids else []
        genres = {genre for artist in artists_data for genre in artist.get('genres', [])}

        return {
            'track_id': track_id,
            'track_name': track.get('name', 'Unknown Track'),
            'artists': [a.get('name', 'Unknown') for a in track.get('artists', [])],
            'album': track.get('album', {}).get('name', 'Unknown Album'),
            'genres': list(genres),
            'popularity': track.get('popularity', 0),
            'release_year': track.get('album', {}).get('release_date', '1900')[:4],
            'duration_ms': track.get('duration_ms', 0),
            'user_playlists': playlists
        }
    except Exception as e:
        print(f"Error retrieving details for {track_id}: {e}")
        return {}


    try:
        track = sp.track(track_id)
        artist_ids = [artist['id'] for artist in track['artists'] if artist.get('id')]
        artists_data = sp.artists(artist_ids)['artists'] if artist_ids else []
        genres = {genre for artist in artists_data for genre in artist.get('genres', [])}

        return {
            'track_id': track_id,
            'track_name': track.get('name', 'Unknown Track'),
            'artists': [a.get('name', 'Unknown') for a in track.get('artists', [])],
            'album': track.get('album', {}).get('name', 'Unknown Album'),
            'genres': list(genres),
            'popularity': track.get('popularity', 0),
            'release_year': track.get('album', {}).get('release_date', '1900')[:4],
            'duration_ms': track.get('duration_ms', 0),
            'user_playlists': playlists
        }
    except Exception as e:
        print(f"Error retrieving details for {track_id}: {e}")
        return {}

def get_all_track_details(track_ids):
    all_details = []
    for i in range(0, len(track_ids), 50):  # Batch of up to 50 IDs
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
                        'genres': [],  # Track genres not always available directly
                        'release_year': track['album']['release_date'][:4] if track['album'] and track['album'].get('release_date') else None,
                        'track': track
                    }
                    all_details.append(details)
        except Exception as e:
            print(f"Error during track details retrieval: {e}")
    return all_details

@analysis_bp.route('/confronta_playlist', methods=['POST'])
@login_required
def confronta_playlist():
    selected_playlists = request.form.getlist('playlist')

    if len(selected_playlists) != 2:
        flash('You must select exactly two playlists to compare.', 'error')
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

            # Collect all track IDs
            track_ids = []
            tracks = playlist_metadata['tracks']['items']
            while tracks:
                for item in tracks:
                    track = item.get('track')
                    if track and track.get('id'):
                        track_ids.append(track['id'])

                # Check for more pages
                if playlist_metadata['tracks'].get('next'):
                    playlist_metadata['tracks'] = sp.next(playlist_metadata['tracks'])
                    tracks = playlist_metadata['tracks']['items']
                else:
                    tracks = None

            # Get all details
            track_info = get_all_track_details(track_ids)

        except Exception as e:
            print(f"Error with playlist {playlist_id}: {e}")
            playlist_names.append(f'Playlist {idx+1}')

        playlist_data[f'playlist_{idx+1}'] = pd.DataFrame(track_info)

    df1, df2 = playlist_data['playlist_1'], playlist_data['playlist_2']

    # Ensure 'track_name' column exists
    if 'track_name' not in df1.columns:
        df1['track_name'] = df1['track'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)
    if 'track_name' not in df2.columns:
        df2['track_name'] = df2['track'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)

    # Common tracks
    common_tracks = set(df1['track_name']) & set(df2['track_name'])
    similarity = len(common_tracks) / min(len(df1), len(df2)) * 100 if min(len(df1), len(df2)) > 0 else 0
    similarity_df = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1], 'Common'],
        'Number of Tracks': [len(df1), len(df2), len(common_tracks)]
    })
    similarity_chart = apply_spotify_theme(px.bar(similarity_df, x='Playlist', y='Number of Tracks',
                                  title=f'Track Similarity ({similarity:.2f}%)'))

    # Common artists
    a1 = df1.explode('artists')['artists']
    a2 = df2.explode('artists')['artists']
    common_artists = set(a1) & set(a2)
    artist_freq = pd.DataFrame({
        'Artist': list(common_artists),
        f'Frequency {playlist_names[0]}': [a1.tolist().count(a) for a in common_artists],
        f'Frequency {playlist_names[1]}': [a2.tolist().count(a) for a in common_artists]
    })
    artist_chart = apply_spotify_theme(px.bar(
        artist_freq.melt(id_vars='Artist', var_name='Playlist', value_name='Frequency'),
        x='Artist', y='Frequency', color='Playlist', barmode='group',
        title='Common Artists and Frequencies'
    ))

    # Average popularity
    pop_data = pd.DataFrame({
        'Playlist': [playlist_names[0], playlist_names[1]],
        'Average Popularity': [df1['popularity'].mean(), df2['popularity'].mean()]
    })
    pop_chart = apply_spotify_theme(px.bar(
        pop_data, x='Playlist', y='Average Popularity', title='Average Popularity Comparison'
    ))

    # Musical genres
    g1 = df1.explode('genres')['genres']
    g2 = df2.explode('genres')['genres']
    genre_freq = pd.DataFrame({
        'Genre': list(set(g1) | set(g2)),
        playlist_names[0]: [g1.tolist().count(g) for g in set(g1) | set(g2)],
        playlist_names[1]: [g2.tolist().count(g) for g in set(g1) | set(g2)]
    })
    genre_chart = apply_spotify_theme(px.bar(
        genre_freq.melt(id_vars='Genre', var_name='Playlist', value_name='Frequency'),
        x='Genre', y='Frequency', color='Playlist', barmode='group',
        title='Musical Genres Comparison'
    ))

    # Release years
    df1['release_year'] = pd.to_numeric(df1['release_year'], errors='coerce')
    df2['release_year'] = pd.to_numeric(df2['release_year'], errors='coerce')
    year_df = pd.concat([
        df1[['release_year']].assign(Playlist=playlist_names[0]),
        df2[['release_year']].assign(Playlist=playlist_names[1])
    ])
    time_chart = apply_spotify_theme(px.histogram(
        year_df, x='release_year', color='Playlist', barmode='overlay',
        title='Temporal Distribution of Tracks'
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
    
    # Get metadata for each playlist
    for id_p, nickname in playlists:
        try:
            playlist_metadata = sp_public.playlist(id_p)  # Get playlist metadata
            playlist_name = playlist_metadata.get('name', f'Playlist {nickname}')
            image_url = playlist_metadata['images'][0]['url'] if playlist_metadata['images'] else 'https://fakeimg.pl/250x250/'  # Image URL or placeholder
            playlist_info.append((id_p, playlist_name, image_url))
        except Exception as e:
            print(f"Error with playlist {id_p}: {e}")
            playlist_info.append((id_p, f'Playlist {nickname}', 'https://fakeimg.pl/250x250/'))  # Placeholder if error

    # Handle POST method (when form is submitted)
    if request.method == 'POST':
        selected_playlists = request.form.getlist('playlist')  # Get selected playlists
        
        if len(selected_playlists) != 2:
            flash("You must select exactly two playlists for comparison.", 'error')
            return redirect(url_for('analysis.seleziona_playlist'))  # Return to same page
        
        # Proceed to compare playlists
        return redirect(url_for('analysis.confronta_playlist'))

    # Render template with playlists
    return render_template('seleziona_playlist.html', playlists=playlist_info)


@analysis_bp.route('/single_playlist_analysis', methods=['GET'])
@login_required
def single_playlist_analysis():
    playlist_id = request.args.get('playlist_id')

    if not playlist_id:
        flash('Playlist ID not provided.', 'error')
        return redirect(url_for('home.homepage'))

    try:
        playlist_metadata = sp.playlist(playlist_id)
    except Exception as e:
        flash(f"Error retrieving playlist: {e}", "error")
        return redirect(url_for('home.homepage'))

    playlist_name = playlist_metadata.get('name', 'Unknown Playlist')
    tracks = playlist_metadata['tracks']['items']

    # === Pre-fetch user playlists (to avoid accessing current_user in threads) ===
    user_playlists = []
    saved_playlists = db.fetch_query(
        'SELECT * FROM Playlist WHERE nickname = ?', 
        (current_user.nickname,)
    )
    for saved in saved_playlists:
        playlist_id_db = saved[0]
        try:
            playlist_data = sp_public.playlist(playlist_id_db)
            user_playlists.append(playlist_data)
        except Exception as e:
            print(f"Error retrieving playlist {playlist_id_db}: {e}")

    # === Define worker ===
    def fetch_track_details_safe(track_item):
        track = track_item.get('track')
        if track and track.get('id'):
            return get_track_details(track['id'], user_playlists)
        return None

    # === Execute in parallel ===
    with ThreadPoolExecutor(max_workers=10) as executor:
        track_info = list(executor.map(fetch_track_details_safe, tracks))

    track_info = [info for info in track_info if info]

    if not track_info:
        flash("No tracks found in the playlist.", "error")
        return redirect(url_for('home.homepage'))

    # === Create DataFrame and Charts ===
    df = pd.DataFrame(track_info)
    df['release_year'] = pd.to_numeric(df['release_year'], errors='coerce')

    year_chart = apply_spotify_theme(px.histogram(df, x='release_year', title='Temporal Distribution of Tracks'))

    df['duration_min'] = df['duration_ms'] / 60000
    duration_chart = apply_spotify_theme(px.histogram(df, x='duration_min', nbins=30, title='Track Duration Distribution (minutes)'))

    popularity_chart = apply_spotify_theme(px.histogram(df, x='popularity', nbins=20, title='Track Popularity Distribution'))

    genre_series = df.explode('genres')['genres']
    genre_counts = genre_series.value_counts().head(10).reset_index()
    genre_counts.columns = ['genres', 'count']

    genre_chart = apply_spotify_theme(px.bar(
        genre_counts,
        x='genres',
        y='count',
        title='Top 10 Musical Genres'
    ))
    genre_chart.update_layout(xaxis_title='Genre', yaxis_title='Number of Tracks')

    evolution_chart = apply_spotify_theme(px.scatter(
        df, 
        x='release_year', 
        y='popularity', 
        trendline="ols",
        title='Popularity Evolution Over Time',
        labels={'release_year': 'Release Year', 'popularity': 'Popularity'}
    ))

    top_artists = df.explode('artists')['artists'].value_counts().head(5).reset_index()
    top_artists.columns = ['Artist', 'Occurrences']
    top_artists_chart = apply_spotify_theme(px.bar(
        top_artists, x='Artist', y='Occurrences', title='Top 5 Most Present Artists'
    ))

    # Recommendations (optional logic)
    top_artist_names = top_artists['Artist'].tolist()
    seed_artist = []
    for name in top_artist_names:
        try:
            results = sp.search(q=f'artist:{name}', type='artist', limit=1)
            items = results['artists']['items']
            if items:
                artist_id = items[0]['id']
                seed_artist.append(artist_id)
        except Exception as e:
            print(f"Error retrieving ID for '{name}': {e}")

    unique_genres = genre_series.dropna().unique().tolist()
    seed_genres = [str(genre) for genre in unique_genres if genre and genre != 'nan'][:3]

    tracks_data = []
    if seed_artist or seed_genres:
        try:
            recommendations = sp.recommendations(
                seed_artists=','.join(seed_artist),
                seed_genres=','.join(seed_genres),
                limit=20
            )
            if recommendations and 'tracks' in recommendations:
                tracks_data = recommendations['tracks']
        except Exception as e:
            flash("Failed to fetch song recommendations. Please try again.", "error")

    return render_template(
        'analisiplaylistsingola.html',
        playlist_name=playlist_name,
        tracks=tracks_data,
        year_chart=year_chart.to_html(full_html=False),
        duration_chart=duration_chart.to_html(full_html=False),
        popularity_chart=popularity_chart.to_html(full_html=False),
        genre_chart=genre_chart.to_html(full_html=False),
        evolution_chart=evolution_chart.to_html(full_html=False),
        top_artists_chart=top_artists_chart.to_html(full_html=False),
    )
