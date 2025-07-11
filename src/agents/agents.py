from src.tools.machines.machines import machines_names
from src.tools.machines.formated_machines import formated_machines
from src.dude.filter import Filter
from src.cache.cache import ManualCachedEmbedder
from src.db.get_live_data import LiveData
from src.tools.fuzzy_matcher import FuzzyMatcher

from dotenv import load_dotenv
from typing import Optional

from langchain import hub
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import tool

from langchain.globals import set_llm_cache
from langchain_redis.cache import RedisCache

"""
Este é o código principal do assistente inteligente que integra várias ferramentas e funcionalidades.
Ele permite buscar informações em tempo real sobre máquinas e produtos, consultar ordens de serviço,

As @tool decorators definem as ferramentas que o assistente pode usar, não utilizando o princípio SRP para manter a simplicidade.
"""

load_dotenv()


@tool
def get_live_general_status() -> str:
    """
    Use esta ferramenta para obter o status em tempo real das maquinas e produtos.
    Quando não for informado uma máquina específica, retorna o status geral de todas as máquinas e produtos.
    """

    return LiveData.execute_query(
        query="""
                SELECT * FROM products_status 
                JOIN machines_status ON products_status.machine_name = machines_status.machine_name;
            """
    )


@tool
def get_live_machine_status(machine_name_db: str) -> str:
    """Use esta ferramenta para obter o status em tempo real de uma máquina ou tear específico. Forneça o nome ou identificador da máquina."""

    if machine_name_db:
        canonical_equipment_name = FuzzyMatcher.match(machine_name_db, machines_names)
        if not canonical_equipment_name:
            return f"Equipamento '{machine_name_db}' não encontrado na lista de máquinas válidas."

    return LiveData.execute_query_machine(
        query="SELECT * FROM machines_status WHERE machine_name LIKE ?",
        canonical_equipment_name=canonical_equipment_name,
    )


@tool
def get_live_product_status(machine_name_db: str) -> str:
    """Use esta ferramenta para obter o status em tempo real de um PRODUTO específico. Forneça o nome ou identificador da máquina."""

    if machine_name_db:
        canonical_equipment_name = FuzzyMatcher.match(machine_name_db, machines_names)
        if not canonical_equipment_name:
            return f"Equipamento '{machine_name_db}' não encontrado na lista de máquinas válidas."

    return LiveData.execute_query_machine(
        query="SELECT * FROM products_status WHERE machine_name LIKE ?",
        canonical_equipment_name=canonical_equipment_name,
    )


@tool
def search_service_orders_api(
    user_input: str,
    equipment_name: Optional[str] = None,
    status: Optional[str] = None,
    date_iso: Optional[str] = None,
) -> str:
    """
    Busca ordens de serviço em uma API externa (Dude). Use sempre que o usuário perguntar sobre ordens de serviço, OS, ou chamados no Dude.
    - user_input: A entrada original do usuário, necessária para a classe Filter.
    - status: O status da ordem de serviço. Valores permitidos: 'New Request', 'Completed', 'In Progress'.
    - equipment_name: O nome do equipamento ou máquina a ser consultado.
    - date_iso: Estamos em 2025. A data da consulta no formato 'YYYY-MM-DDThh-mm-ss'. O agente pode converter 'hoje' ou 'ontem' para este formato.
    """
    print("--- ATIVANDO FERRAMENTA: search_service_orders_api ---")
    print(
        f"Parâmetros recebidos: Equipamento='{equipment_name}', Status='{status}', Data='{date_iso}'"
    )

    canonical_equipment_name = None
    if equipment_name:
        canonical_equipment_name = FuzzyMatcher.match(equipment_name, formated_machines)

    api_body_list = ["vazio", "vazio", "vazio"]

    if date_iso:
        api_body_list[0] = date_iso

    if status:
        api_body_list[1] = status

    if canonical_equipment_name:
        api_body_list[2] = canonical_equipment_name

    filter_instance = Filter(api_body_list, user_input)
    result = filter_instance.filter_order()

    return result


@tool
def search_documentation(query: str, source_filter: Optional[dict] = None) -> str:
    """
    Busca informações em documentos, manuais e procedimentos da empresa.
    Para buscas focadas, use o parâmetro 'source_filter' com um dicionário.
    Exemplo para filtrar por nome de arquivo: {"file_name": "Analista de Automação Sr - 1.057 .pdf"}
    Exemplo para filtrar por tipo de documento (tabela): {"source_table": "mantas"}
    """
    print("--- ATIVANDO FERRAMENTA: search_documentation ---")
    print(f"Query: '{query}', Filtro: {source_filter}")

    db_path = r"C:\Users\Rafael\Desktop\Projeto 2025\Modelo\src\RAG\rag_db_index"

    base_embedder = OpenAIEmbeddings(model="text-embedding-3-small")
    cached_embedder = ManualCachedEmbedder(base_embedder=base_embedder)

    vectorstore = Chroma(
        persist_directory=db_path,
        embedding_function=cached_embedder,
    )

    search_kwargs = {"k": 2}

    if source_filter:
        search_kwargs["filter"] = source_filter

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    docs = retriever.invoke(query)

    if not docs:
        return "Nenhuma informação relevante foi encontrada para esta consulta com os filtros aplicados."

    context = "\n\n---\n\n".join(
        f"[Fonte: {doc.metadata.get('file_name', doc.metadata.get('source_table', 'N/A'))}]\n{doc.page_content}"
        for doc in docs
    )
    return (
        f"Aqui estão os trechos de documentos encontrados sobre '{query}':\n\n{context}"
    )


class IntelligentAssistant:
    def __init__(
        self,
    ):
        load_dotenv()

        try:
            redis_url = "redis://localhost:6379/0"
            set_llm_cache(RedisCache(redis_url=redis_url))
        except Exception as e:
            print(f"AVISO: Cache de LLM com Redis desativado. Erro: {e}")

        self.llm = ChatOpenAI(model="gpt-4.1", temperature=0)
        self.tools = self._create_tools()

        prompt = hub.pull("hwchase17/openai-functions-agent")
        prompt.input_variables.append("chat_history")
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    def _create_tools(self) -> list:
        print("Criando ferramenta de RAG com MultiQueryRetriever...")

        return [
            get_live_machine_status,
            get_live_product_status,
            search_service_orders_api,
            get_live_general_status,
            search_documentation,
        ]

    def run(self, user_input: str, chat_history: list) -> str:
        try:
            response = self.agent_executor.invoke(
                {"input": user_input, "chat_history": chat_history}
            )

            return response.get("output", "Não obtive uma resposta.")

        except Exception:
            return "Desculpe, enfrentei um problema técnico e não consegui processar sua solicitação."

    def start_chat(self):
        while True:
            user_input = input("Você: ")

            if user_input.lower() in ["sair", "exit", "quit"]:
                print("Até logo!")
                break

            assistant_response = self.run(user_input, "")

            print(f"\nAssistente: {assistant_response}\n")


if __name__ == "__main__":
    assistant = IntelligentAssistant()
    assistant.start_chat()
