import random
import uuid
import logging
import json
from locust import HttpUser, TaskSet, task, between
import time

# Configurando o logger para salvar logs em um arquivo no formato JSON
log_file = "locust_test_logs.json"
file_handler = logging.FileHandler(log_file, mode='a')  # Salva no arquivo, sobrescrevendo a cada execução
file_handler.setFormatter(logging.Formatter('%(message)s'))  # Apenas a mensagem será registrada

stream_handler = logging.StreamHandler()  # Exibe no console
stream_handler.setFormatter(logging.Formatter('%(message)s'))

logger = logging.getLogger("LocustLogger")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

class FastAPITasks(TaskSet):
    def generate_headers(self):
        """
        Gera novos headers com um UUID único para cada requisição.
        """
        return {
            "Authorization": "Bearer my_token",
            "Content-Type": "application/json",
            "Correlation-ID": str(uuid.uuid4())
        }

    @task
    def execute_tasks_in_order(self):
        """
        Executa as tasks na ordem desejada: task 2 primeiro e task 1 depois.
        """
        # Executando a task 2
        self.test_root()

        # Delay de x segundos
        time.sleep(5)

        # Executando a task 1
        self.test_saudacao()

    def test_root(self):
        """
        Testa a rota /rota1 com logs detalhados.
        """
        url = "/rota1"
        method = "GET"
        payload = None  # Sem payload para GET
        headers = self.generate_headers()  # Gera novos headers para esta requisição
        with self.client.get(url, headers=headers, catch_response=True) as response:
            self.log_request_and_response(method, url, headers, payload, response)

    def test_saudacao(self):
        """
        Testa a rota /saudacao/rota2 com logs detalhados.
        """
        url = "/saudacao/rota2"
        method = "GET"
        payload = None
        headers = self.generate_headers()  # Gera novos headers para esta requisição
        with self.client.get(url, headers=headers, catch_response=True) as response:
            self.log_request_and_response(method, url, headers, payload, response)

    def log_request_and_response(self, method, url, headers, payload, response):
        """
        Loga os detalhes da requisição e resposta no formato JSON.
        """
        log_data = {
            "request": {
                "method": method,
                "url": url,
                "headers": headers,
                "payload": payload
            },
            "response": {
                "status_code": response.status_code,
                "body": response.text
            }
        }

        # Convertendo para JSON e logando
        logger.info(json.dumps(log_data, indent=4))

        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"HTTP {response.status_code}: {response.text}")

class FastAPIUser(HttpUser):
    tasks = [FastAPITasks]
    wait_time = between(0.1, 0.1)  # Tempo de espera entre requisições
    host = "http://localhost:8000"  # Alterar para o host real da aplicação
