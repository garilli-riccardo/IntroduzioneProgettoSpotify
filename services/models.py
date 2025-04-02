import pymmsql
import sqlite3
import os
class database:

    def __init__(self , db_file='db.sqlite'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self.create_tables()



    def connessione(self):
        return sqlite3.connect(self.db_path)
    
    
    
    
    def create_tables(self):
        conn = self.connessione()
        cursor = conn.cursor()

        # Crea la tabella user (con idps come chiave esterna)
        cursor.execute('''CREATE TABLE IF NOT EXISTS user (
                            nome TEXT NOT NULL,
                            idu INTEGER PRIMARY KEY AUTOINCREMENT,
                            password TEXT NOT NULL,
                            idps INTEGER,
                            FOREIGN KEY(idps) REFERENCES playlist_salvate(idps)
                          )''')

        # Crea la tabella playlist_salvate
        cursor.execute('''CREATE TABLE IF NOT EXISTS playlist_salvate (
                            nome TEXT NOT NULL,
                            idps INTEGER PRIMARY KEY AUTOINCREMENT
                          )''')

        conn.commit()
        conn.close()



            def insert_user(self, nome, password, idps=None):
        conn = self.connessione()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO user (nome, password, idps)
            VALUES (?, ?, ?)
        ''', (nome, password, idps))

        conn.commit()
        conn.close()

    def insert_playlist_salvata(self, nome):
        conn = self.connessione()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO playlist_salvate (nome)
            VALUES (?)
        ''', (nome,))

        conn.commit()
        conn.close()



        def get_user_by_id(self, user_id):
        conn = self.connessione()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM user WHERE idu = ?
        ''', (user_id,))
        user = cursor.fetchone()

        conn.close()
        return user

    def get_playlist_salvata_by_idps(self, idps):
        conn = self.connessione()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM playlist_salvate WHERE idps = ?
        ''', (idps,))
        playlist = cursor.fetchone()

        conn.close()
        return playlist


"""
    def get_db_connection():
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor
        )

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Creazione delle tabelle utenti, playlist e relazione molti-a-molti
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                username VARCHAR(80) UNIQUE NOT NULL,
                                password VARCHAR(120) NOT NULL)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS playlists (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                name VARCHAR(255) NOT NULL,
                                image VARCHAR(255))''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS user_playlists (
                                user_id INT,
                                playlist_id INT,
                                PRIMARY KEY (user_id, playlist_id),
                                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE)''')
            
            connection.commit()

"""