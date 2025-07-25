import os
import json
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import pyodbc
import fitz


class RAGIndexer:
    def __init__(
        self,
        persist_directory: str = "./rag_db",
        embedding_model: str = "text-embedding-3-small",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        db_config: dict = None,
    ):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.db_config = db_config

    def _get_db_connection(self):
        if not self.db_config:
            print("Erro: Configuração do banco de dados não fornecida.")
            return None

        conn_str = (
            f"DRIVER={self.db_config['driver']};SERVER={self.db_config['server']};"
            f"DATABASE={self.db_config['database']};UID={self.db_config['uid']};"
            f"PWD={self.db_config['pwd']};charset='UTF-8'"
        )
        try:
            conn = pyodbc.connect(conn_str)
            return conn
        except pyodbc.Error as ex:
            print(f"Erro ao conectar ao SQL Server: {ex}")
            return None

    def _load_docs_from_pdf_in_db(
        self,
        table_name: str,
        id_column: str = "id",
        filename_column: str = "file_name",
        content_column: str = "pdf_content",
    ) -> list[Document]:
        documents = []
        print(f"Buscando PDFs da tabela '{table_name}' para extração de texto...")

        try:
            with self._get_db_connection() as conn:
                if not conn:
                    return []
                with conn.cursor() as cursor:
                    query = f"SELECT {id_column}, {filename_column}, {content_column} FROM {table_name}"
                    cursor.execute(query)

                    for row in cursor.fetchall():
                        pdf_id = row[0]
                        pdf_filename = row[1]
                        pdf_binary_data = row[2]

                        if not pdf_binary_data:
                            continue

                        print(
                            f"  - Processando PDF: ID={pdf_id}, Nome='{pdf_filename}'"
                        )

                        try:
                            # Abre o PDF a partir dos dados binários em memória
                            with fitz.open(
                                stream=pdf_binary_data, filetype="pdf"
                            ) as doc:
                                extracted_text = ""
                                for page in doc:
                                    extracted_text += page.get_text("text")

                                if extracted_text:
                                    metadata = {
                                        "source_table": table_name,
                                        "file_name": pdf_filename,
                                        "content_column": content_column,
                                    }
                                    documents.append(
                                        Document(
                                            page_content=extracted_text,
                                            metadata=metadata,
                                        )
                                    )

                        except Exception as e:
                            print(
                                f"    ERRO: Não foi possível processar o PDF com ID={pdf_id}. Erro: {e}"
                            )

            print(
                f"Extração concluída. Coletados {len(documents)} documentos a partir dos PDFs."
            )
        except Exception as e:
            print(f"Erro geral ao buscar dados da tabela de PDF '{table_name}': {e}")

        return documents

    def _extract_content_and_metadata(
        self,
        row_data: dict,
        table_name: str,
        name_column: str = None,
        doc_type: str = None,
    ) -> Document:
        metadata = {"source_table": table_name}
        if "id" in row_data:
            metadata["id"] = row_data["id"]
        if name_column and name_column in row_data:
            metadata["file_name"] = row_data[name_column]
        if doc_type:
            metadata["type"] = doc_type

        clean_row_data = {k: str(v or "").strip() for k, v in row_data.items()}
        content_for_page = json.dumps(clean_row_data, ensure_ascii=False, indent=2)
        return Document(page_content=content_for_page, metadata=metadata)

    def _load_data_from_sql(
        self, table_name: str, name_column: str = None, doc_type: str = None
    ) -> list[Document]:
        documents = []
        try:
            with self._get_db_connection() as conn:
                if not conn:
                    return []
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    columns = [column[0] for column in cursor.description]

                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))
                        doc = self._extract_content_and_metadata(
                            row_dict, table_name, name_column, doc_type
                        )
                        documents.append(doc)
            print(f"Coletados {len(documents)} documentos da tabela '{table_name}'.")
        except Exception as e:
            print(f"Erro ao processar dados da tabela '{table_name}': {e}")
        return documents

    def _load_docs_from_json_column(
        self,
        table_name: str,
        content_column: str = "file_content",
        metadata_columns: list = ["id", "file_name"],
    ) -> list[Document]:
        documents = []
        try:
            with self._get_db_connection() as conn:
                if not conn:
                    return []
                with conn.cursor() as cursor:
                    columns_to_select = ", ".join(metadata_columns + [content_column])
                    cursor.execute(f"SELECT {columns_to_select} FROM {table_name}")
                    print(
                        f"Buscando e processando documentos da tabela '{table_name}' (formato JSON)..."
                    )
                    cols = [column[0] for column in cursor.description]
                    for row in cursor.fetchall():
                        row_dict = dict(zip(cols, row))
                        json_string = row_dict.get(content_column)
                        if not json_string:
                            continue
                        try:
                            data = json.loads(json_string)
                            page_content = "\n\n".join(
                                str(value).strip() for value in data.values()
                            )
                            metadata = {
                                "source_table": table_name,
                                "content_column": content_column,
                            }
                            for col in metadata_columns:
                                if col in row_dict:
                                    metadata[col] = row_dict[col]
                            documents.append(
                                Document(page_content=page_content, metadata=metadata)
                            )
                        except json.JSONDecodeError:
                            pass
            print(
                f"Coletados e processados {len(documents)} documentos da tabela '{table_name}'."
            )
        except Exception as e:
            print(f"Erro ao processar a tabela '{table_name}': {e}")
        return documents

    def index_data(self):
        all_documents = []

        all_documents.extend(
            self._load_docs_from_json_column(table_name="tecelagem_e_revisao")
        )
        all_documents.extend(self._load_docs_from_json_column(table_name="mantas"))
        all_documents.extend(
            self._load_docs_from_json_column(table_name="recepcao_de_materiais")
        )
        all_documents.extend(
            self._load_docs_from_json_column(table_name="preparacao_de_fios")
        )
        all_documents.extend(
            self._load_docs_from_json_column(table_name="pean_sean_felts_PSF")
        )
        all_documents.extend(self._load_docs_from_json_column(table_name="metrologia"))
        all_documents.extend(self._load_docs_from_json_column(table_name="expedicao"))
        all_documents.extend(self._load_docs_from_json_column(table_name="acabamento"))
        all_documents.extend(self._load_docs_from_pdf_in_db(table_name="DocumentosPDF"))

        if not all_documents:
            print("Nenhum dado encontrado para indexar. Indexação abortada.")
            return

        chunks = self.text_splitter.split_documents(all_documents)
        print(f"Total de fragmentos gerados: {len(chunks)}")

        # Define o tamanho do lote (batch size). Um valor entre 200 e 500 é seguro.
        batch_size = 300
        total_chunks = len(chunks)

        try:
            print(
                f"Iniciando a indexação de {total_chunks} fragmentos em lotes de {batch_size}..."
            )

            # Processa o primeiro lote para criar o banco de dados
            if total_chunks > 0:
                primeiro_lote = chunks[:batch_size]
                vector_store = Chroma.from_documents(
                    documents=primeiro_lote,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory,
                )
                print(f"Lote 1/{total_chunks // batch_size + 1} processado.")

            # Processa os lotes restantes, adicionando ao banco de dados existente
            for i in range(batch_size, total_chunks, batch_size):
                lote_atual = chunks[i : i + batch_size]
                vector_store.add_documents(documents=lote_atual)
                print(
                    f"Lote {i // batch_size + 1}/{total_chunks // batch_size + 1} processado."
                )

            print("Indexação concluída. Dados armazenados com sucesso!")

        except Exception as e:
            print(f"Erro durante a indexação ou persistência no ChromaDB: {e}")


if __name__ == "__main__":
    load_dotenv()
    sql_config = {
        "driver": "{ODBC Driver 17 for SQL Server}",
        "server": os.getenv("DB_SERVER_DEV"),
        "database": os.getenv("DB_NAME_CONVERSATION"),
        "uid": os.getenv("DB_USER_DEV"),
        "pwd": os.getenv("DB_PASSWORD"),
    }

    indexer = RAGIndexer(persist_directory="./rag_db_index", db_config=sql_config)
    indexer.index_data()
