import os
import json
import pyodbc
from src.db.db_connector import Db_Connection
from dotenv import load_dotenv


class LiveData:
    """
    Class to handle live data operations.
    """

    def execute_query_machine(query: str, canonical_equipment_name: str):
        """Conecta ao DB, executa uma query com o nome de um equipamento e retorna os resultados."""

        load_dotenv()

        try:
            with Db_Connection(db_name=os.getenv("DB_NAME_CONVERSATION")) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, f"%{canonical_equipment_name}%")
                    columns = [column[0] for column in cursor.description]
                    row = cursor.fetchone()

                    if not row:
                        return f"Nada encontrado para a máquina com nome parecido com '{canonical_equipment_name}'."

                    data = dict(zip(columns, row))

                    return json.dumps(data, ensure_ascii=False, indent=2)

        except pyodbc.Error as db_err:
            return f"Ocorreu um erro de banco de dados: {db_err}"

    def execute_query(query: str):
        """Conecta ao DB, executa uma query e retorna os resultados."""

        load_dotenv()

        try:
            db_manager = Db_Connection(db_name=os.getenv("DB_NAME_CONVERSATION"))

            with db_manager as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [column[0] for column in cursor.description]
                    rows = cursor.fetchall()

                    if not rows:
                        return "Nenhum dado encontrado."

                    data = [dict(zip(columns, row)) for row in rows]

                    return json.dumps(data, ensure_ascii=False, indent=2)

        except pyodbc.Error as db_err:
            return f"Ocorreu um erro de banco de dados: {db_err}"
