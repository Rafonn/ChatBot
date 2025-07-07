import os
import pyodbc
from dotenv import load_dotenv


class Db_Connection:
    def __init__(self, db_name: str = None):
        load_dotenv()

        server = os.getenv("DB_SERVER_DEV")
        username = os.getenv("DB_USER_DEV")
        password = os.getenv("DB_PASSWORD")

        database = db_name if db_name else os.getenv("DB_NAME")

        if not database:
            raise ValueError(
                "O nome do banco de dados não foi fornecido nem encontrado no arquivo .env"
            )

        self.conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        self.connection = None

    def __enter__(self):
        try:
            self.connection = pyodbc.connect(self.conn_str)
            return self.connection
        except pyodbc.Error as ex:
            print(f"Erro ao conectar ao banco de dados: {ex}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
