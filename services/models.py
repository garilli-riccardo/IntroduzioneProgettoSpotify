import pymmsql
import os
class database:



    def __init__(self,server="192.168.40.19\\SQLexpress",user="utente116DB",password="Cs8Fwvpz",database="Utente116.DB"):
        self._server=server
        self._user=user
        self._password=password
        self._database=database


    def connessione(self):
        try:
            WrapperDbSuola.conn=pymssql.connect(server=self._server, user=self._user, password=self._password,database=self._database)
            print("connessione al db riscita")
            return WrapperDbSuola.conn
        
        except:
            return 0




    def disconnetti(self):
        try:
            WrapperDbSuola.conn.close()
            print("disconnessione al db avvenuta con successo")
            
        except:
            print("errore durante la disconessione al database")


    def createUser(self):
        c=self.connessione()
        try:
            q="""
                if not exist(
                    select * from sysobject
                    Where xtype ='U' and nome ='user')


                CREATE TABLE user(
                id_s int primary key
                username varchar(100) not null
                password varchar(200) not null
                id_p int not null
                foreign key (id_p) REFERENCES users(id_p) on delete cascade,

                );

                """
            curs=c.cursor()
            curs.execute(q)
            c.commit()
        except pymssql.error as e:
            print(f"errore: {e}")

    
    
    
    
    def createPlaylist(self):
        c=self.connessione()
        try:
            q="""
                if not exist(
                    select * from sysobject
                    Where xtype ='U' and nome ='playlist')


                CREATE TABLE user(
                id_p int primary key
                nome_plalist varchar(100) not null
                immagine varchar(255) not null
                id_s int not null
                foreign key (id_s) REFERENCES users(id_s) on delete cascade,

                );

                """
            curs=c.cursor()
            curs.execute(q)
            c.commit()
        except pymssql.error as e:
            print(f"errore: {e}")



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