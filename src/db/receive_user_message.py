import pyodbc

from db.db_connector import Db_Connection


class LastMessageFetcher:
    def __init__(self, user_id):
        self.user_id = user_id
        self.last_message_timestamp = None
        self.db_manager = Db_Connection()

    def fetch_last_message(self):
        """
        Busca a última mensagem usando o gerenciador de conexão.
        """
        try:
            with self.db_manager as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT TOP 1 
                        userTimeStamp, 
                        userMessage 
                    FROM user_logs 
                    WHERE userId = ? 
                    ORDER BY userTimeStamp DESC
                """,
                    self.user_id,
                )
                row = cursor.fetchone()

            if row:
                userTimeStamp, userMessage = row
                if userTimeStamp != self.last_message_timestamp:
                    self.last_message_timestamp = userTimeStamp
                    return userMessage

            return None
        except pyodbc.Error as e:
            print(f"Erro de banco de dados: {e}")
            return None
