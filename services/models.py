import sqlite3
import os

class DatabaseWrapper:
    def __init__(self, db_file='SpotifyDB.db'):

        self.db_file = db_file
        self.create_tables()  

    def connect(self):
        return sqlite3.connect(self.db_file)

    def execute_query(self, query, params=()):
        conn = self.connect()
        with conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def fetch_query(self, query, params=()):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result

    def create_tables(self):
        self.create_table_Utente()
        self.create_table_playlist()

    def create_table_Utente(self):
        self.execute_query(''' 
            CREATE TABLE IF NOT EXISTS Utente (
                nickname TEXT NOT NULL,
                password TEXT NOT NULL,
                PRIMARY KEY (nickname)
            )
        ''')

    def create_table_playlist(self):
        self.execute_query(''' 
            CREATE TABLE IF NOT EXISTS Playlist (
                id_p TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                PRIMARY KEY (id_p, nickname),
                FOREIGN KEY (nickname) REFERENCES Utente(nickname) ON DELETE CASCADE
            )
        ''')

    def get_Utente(self):
        return self.fetch_query('SELECT * FROM Utente')

    def get_Playlist(self):
        return self.fetch_query('SELECT * FROM Playlist')

    def aggiungi_Utente(self, nickname, password):
        self.execute_query('INSERT INTO Utente (nickname, password) VALUES (?, ?)', (nickname, password))

    def aggiungi_Playlist(self, id_p, nickname):
        self.execute_query('INSERT OR IGNORE INTO Playlist (id_p, nickname) VALUES (?, ?)', (id_p, nickname))

    def rimuovi_Playlist(self, id_p):
        self.execute_query('DELETE FROM Playlist WHERE id_p = ?', (id_p,))

    def rimuovi_Utente(self, indice):
        self.execute_query('DELETE FROM Utente WHERE nickname = ?', (indice,))

    def svuota_Utente(self):
        self.execute_query('DELETE FROM Utente')

    def svuota_Playlist(self):
        self.execute_query('DELETE FROM Playlist')


db = DatabaseWrapper(db_file="SpotifyDB.db")  # Crea un'istanza globale qui

from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, nickname):
        self.nickname = nickname

    @staticmethod
    def get(user_id):
        utenti = db.get_Utente()
        user_data = next((u for u in utenti if u[0] == user_id), None)
        if user_data:
            return User(nickname=user_data[0]) 
        return None

    def get_id(self):
        return self.nickname