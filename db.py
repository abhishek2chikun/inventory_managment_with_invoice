from mysql.connector import connect, Error

# Singleton DB connection
class Database:
    _connection = None

    @staticmethod
    def get_connection():
        if Database._connection is None:
            try:
                Database._connection = connect(
                    host="localhost",
                    user="root",
                    password="Hello2world",
                    database="gananath"
                )
            except Error as e:
                print(f"Error connecting to the database: {e}")
        return Database._connection

# Define a class to manage session state
class SessionState:
    def __init__(self):
        self.items = []

