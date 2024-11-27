import time
import logging
import inspect
from datetime import datetime
from .metrics import http_requests_total, http_request_latency
import requests
import json


class InstrumentedRequest:
    def __init__(self, log_code_requester: str):
        """
        Inicializa a classe com o LOG_CODE_REQUESTER.

        Args:
            log_code_requester (str): Identificador para logar o requisitante.
        """
        if not isinstance(log_code_requester, str):
            raise ValueError("LOG_CODE_REQUESTER deve ser uma string.")

        self.log_code_requester = log_code_requester

        # Configuração do logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def format_log(log):
        """Formata o log como JSON indentado."""
        return json.dumps(log, indent=4)

    @staticmethod
    def mask_data(data, mask_fields):
        """
        Mascarar campos sensíveis de um dicionário.
        """
        if not data or not mask_fields:
            return data

        masked_data = data.copy()
        for field in mask_fields:
            if field in masked_data:
                masked_data[field] = "*****"  # Substitui o valor por asteriscos
        return masked_data

    def request(self, request_config, log_config=None):
        """
        Faz uma requisição HTTP enquanto coleta métricas para Prometheus.
        Registra logs detalhados com informações de rastreamento, duração e contexto.
        Permite mascarar campos sensíveis nos headers e no body.

        Args:
            request_config (dict): Configurações da requisição:
                - method (str): Método HTTP (GET, POST, etc.).
                - url (str): URL da requisição.
                - headers (dict, opcional): Headers da requisição.
                - kwargs (dict, opcional): Outros parâmetros da função requests.request.
            log_config (dict): Configurações dos logs:
                - mask_headers_request (list, opcional): Campos do header da requisição a serem mascarados.
                - mask_body_request (list, opcional): Campos do body da requisição a serem mascarados.
                - mask_body_response (list, opcional): Campos da resposta a serem mascarados.
        """
        start_time = time.perf_counter()

        # Linha de código chamadora
        frame = inspect.currentframe().f_back
        invoker_line_location = f"{frame.f_code.co_filename}:{frame.f_lineno}"

        # Timestamp formatado
        datetime_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        # Extrair dados do request_config
        method = request_config.get("method")
        url = request_config.get("url")
        headers = request_config.get("headers", {})
        kwargs = request_config.get("kwargs", {})

        # Convertendo chaves de log_config para lowercase
        log_config = {key.lower(): value for key, value in log_config.items()}

        # Mascarar headers e body antes do log
        mask_headers_request = log_config.get("mask_headers_request", [])
        mask_body_request = log_config.get("mask_body_request", [])
        mask_body_response = log_config.get("mask_body_response", [])

        masked_headers = self.mask_data(headers, mask_headers_request)
        masked_body_request = self.mask_data(kwargs.get('json'), mask_body_request) if kwargs.get('json') else None

        # Dados da requisição para o log
        request_payload = {
            "method": method,
            "url": url,
            "headers": masked_headers,
            "body": masked_body_request
        }

        try:
            # Executa a requisição HTTP
            response = requests.request(method, url, headers=headers, **kwargs)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)  # Duração em milissegundos

            # Atualiza métricas
            http_requests_total.labels(method=method, endpoint=url, status=response.status_code).inc()
            http_request_latency.labels(method=method, endpoint=url, status=response.status_code).observe(duration_ms)

            # Processar resposta e mascarar campos, se aplicável
            response_body = response.json() if response.headers.get('Content-Type', '').startswith('application/json') else response.text
            if isinstance(response_body, dict):
                masked_response = self.mask_data(response_body, mask_body_response)
            else:
                masked_response = response_body

            # Dados da resposta para o log
            response_payload = {
                "status_code": response.status_code,
                "body": masked_response if isinstance(masked_response, str) else json.dumps(masked_response)[:200],
                "duration_ms": duration_ms
            }

            # Log unificado com sucesso
            log = {
                "datetime": datetime_now,
                "logMessage": "HTTP request successfully executed",
                "log_code_requester": self.log_code_requester,
                "invoker_line_location": invoker_line_location,
                "duration_ms": duration_ms,
                "payload": {
                    "request": request_payload,
                    "response": response_payload
                }
            }
            self.logger.info(self.format_log(log))
            return response

        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Dados de erro para o log
            error_payload = {
                "status_code": "error",
                "error": str(e),
                "duration_ms": duration_ms
            }

            # Log unificado com erro
            log = {
                "datetime": datetime_now,
                "log_cod_requester": self.log_code_requester,
                "logMessage": "HTTP request failed",
                "invoker_line_location": invoker_line_location,
                "duration_ms": duration_ms,
                "payload": {
                    "request": request_payload,
                    "response": error_payload
                }
            }
            self.logger.error(self.format_log(log))
            raise e
