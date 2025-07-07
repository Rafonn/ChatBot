import pyodbc

from src.db.db_connector import Db_Connection


class SqlServerUserFetcher:
    def __init__(self):
        self.table_name = "ActiveUsers"
        self.email_column = "UserEmail"
        self.active_column = "Active"

        self.db_manager = Db_Connection()

    def get_user_ids(self) -> list:
        """Busca os e-mails de usuários ativos usando o gerenciador de conexão."""
        query = (
            f"SELECT {self.email_column}, {self.active_column} FROM {self.table_name}"
        )
        ids = []
        try:
            with self.db_manager as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                ids = [row[0] for row in cursor.fetchall() if row[1] == 1]
        except pyodbc.Error as e:
            print(f"Erro ao acessar o banco: {e}")
        return ids


if __name__ == "__main__":
    fetcher = SqlServerUserFetcher()
    user_ids = fetcher.get_user_ids()

    if user_ids:
        for email in user_ids:
            print(f"- {email}")
    else:
        print("❌ Nenhum usuário ativo foi encontrado.")
