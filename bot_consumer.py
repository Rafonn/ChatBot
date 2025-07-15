import os
import pika
import json
import time
import traceback

from src.agents.agents import IntelligentAssistant
from src.db.bot_logs_saver import Bot_Logs

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()

# --- CONFIGS ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
USER_LOG_EXCHANGE = os.getenv("USER_LOG_EXCHANGE")
BOT_LOG_EXCHANGE = os.getenv("BOT_LOG_EXCHANGE")
USER_LOG_QUEUE = os.getenv("USER_LOG_QUEUE")
USER_LOG_ROUTING_KEY = os.getenv("USER_LOG_ROUTING_KEY")

assistant = IntelligentAssistant()
chat_histories = {}


class BotConsumer:
    def publish_bot_response(self, channel, user_id, bot_response):
        """
        Publica a resposta do bot para a exchange que a API C# (WebSocketHandler) escuta.
        """
        try:
            payload = {"lastLog": bot_response}

            channel.basic_publish(
                exchange=BOT_LOG_EXCHANGE,
                routing_key=user_id,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
            print(f" > [PRODUTOR] Resposta para '{user_id}' publicada com sucesso.")
        except Exception as e:
            print(f"   [!] ERRO ao publicar resposta para '{user_id}': {e}")
            traceback.print_exc()

    def on_message_callback(self, ch, method, properties, body):
        """
        Função executada para cada mensagem de usuário recebida.
        """

        try:
            data = json.loads(body)
            user_id = data.get("userId")
            user_message = data.get("userMessage")

            if not user_id or not user_message:
                print(
                    "   [!] Mensagem inválida, faltando userId ou userMessage. Descartando."
                )
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if user_id not in chat_histories:
                chat_histories[user_id] = []

            current_history = chat_histories[user_id]

            bot_response = assistant.run(user_message, current_history)
            print(f"   [*] Resposta da IA: '{bot_response}'")

            current_history.append(HumanMessage(content=user_message))
            current_history.append(AIMessage(content=bot_response))

            if len(current_history) > 20:
                chat_histories[user_id] = current_history[-20:]

            try:
                log_saver = Bot_Logs(bot_response, user_id)
                log_saver.save_bot_response()
            except Exception as db_error:
                print(f"   [!] ERRO ao salvar no banco: {db_error}")

            self.publish_bot_response(ch, user_id, bot_response)

        except Exception as e:
            print(f"   [!] ERRO GERAL no processamento da mensagem: {e}")
            traceback.print_exc()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def main(self):
        """Função principal que configura e inicia o consumidor RabbitMQ."""
        while True:
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=RABBITMQ_HOST, heartbeat=600)
                )
                channel = connection.channel()

                print("Bot conectado ao RabbitMQ. Aguardando mensagens...")

                channel.exchange_declare(
                    exchange=USER_LOG_EXCHANGE, exchange_type="direct", durable=False
                )
                channel.exchange_declare(
                    exchange=BOT_LOG_EXCHANGE, exchange_type="direct", durable=False
                )

                channel.queue_declare(queue=USER_LOG_QUEUE, durable=True)

                channel.queue_bind(
                    queue=USER_LOG_QUEUE,
                    exchange=USER_LOG_EXCHANGE,
                    routing_key=USER_LOG_ROUTING_KEY,
                )

                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(
                    queue=USER_LOG_QUEUE, on_message_callback=self.on_message_callback
                )

                channel.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                print(
                    f"Erro de conexão com o RabbitMQ: {e}. Tentando reconectar em 5 segundos..."
                )
                time.sleep(5)
            except KeyboardInterrupt:
                if "connection" in locals() and connection.is_open:
                    connection.close()
                break
            except Exception as e:
                print(f"Um erro inesperado ocorreu no loop principal: {e}")
                traceback.print_exc()
                print("Tentando reiniciar em 10 segundos...")
                time.sleep(10)


if __name__ == "__main__":
    bot_consumer = BotConsumer()
    bot_consumer.main()
