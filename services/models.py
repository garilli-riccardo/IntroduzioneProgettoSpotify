import pymysql
import os
class database:

    DB_HOST = os.environ.get("MYSQL_HOST", "localhost")
    DB_USER = os.environ.get("MYSQL_USER", "username")
    DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "password")
    DB_NAME = os.environ.get("MYSQL_DATABASE", "Models")

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

