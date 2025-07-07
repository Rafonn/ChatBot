import pyodbc
from src.db.db_connector import Db_Connection


class Bot_Logs:
    def __init__(self, message, user_id):
        self.message = message
        self.user_id = user_id
        self.db_manager = Db_Connection()

    def setup_database(self):
        try:
            with self.db_manager as conn:
                cursor = conn.cursor()
                cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'bot_logs')
                BEGIN
                    CREATE TABLE bot_logs (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        userId NVARCHAR(50) NOT NULL,
                        botMessage NVARCHAR(MAX) NOT NULL,
                        botTimeStamp DATETIMEOFFSET NOT NULL 
                            DEFAULT SYSDATETIMEOFFSET()
                    );
                END
                """)
        except pyodbc.Error as e:
            print(f"Erro durante o setup do banco de dados: {e}")

    def save_bot_response(self):
        """
        Salva a mensagem do bot no banco, confirma a transação e
        retorna os dados inseridos.
        """
        try:
            with self.db_manager as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO bot_logs (userId, botMessage)
                    OUTPUT INSERTED.botTimeStamp
                    VALUES (?, ?);
                """,
                    (self.user_id, self.message),
                )

                inserted_ts = cursor.fetchone()[0]

                conn.commit()

                return {"botMessage": self.message, "botTimeStamp": inserted_ts}

        except pyodbc.Error as e:
            print(f"Erro de banco de dados: {e}")
            return None
