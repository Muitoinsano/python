import time
import logging
import inspect
from datetime import datetime
from .metrics import http_requests_total, http_request_latency
import requests
import json

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def format_log(log):
    """Formata o log como JSON indentado."""
    return json.dumps(log, indent=4)

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

def instrumented_request(request_config, log_config):
    start_time = time.perf_counter()


    datetime_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    method = request_config.get("method")
    url = request_config.get("url")
    headers = {**request_config.get("headers", {})}
    kwargs = request_config.get("kwargs", {})
    timeout = request_config.get("timeout", 10)  # Timeout padrão

    log_config = {key.lower(): value for key, value in log_config.items()}

    mask_headers_request = log_config.get("mask_headers_request", [])
    mask_body_request = log_config.get("mask_body_request", [])
    mask_body_response = log_config.get("mask_body_response", [])
    caller_log_code = log_config.get("caller_log_code")

    masked_headers = mask_data(headers, mask_headers_request)
    masked_body_request = mask_data(kwargs.get('json'), mask_body_request) if kwargs.get('json') else None

    request_payload = {
        "method": method,
        "url": url,
        "headers": masked_headers,
        "body": masked_body_request
    }

    try:
        response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)

        response_body = response.json()

        # Atualiza métricas
        http_requests_total.labels(method=method, endpoint=url, status=response.status_code).inc()
        http_request_latency.labels(method=method, endpoint=url, status=response.status_code).observe(duration)

        masked_body_response = mask_data(response_body, mask_body_response) if isinstance(response_body, dict) else response_body

        response_payload = {
            "status_code": response.status_code,
            "body": str(masked_body_response)[:30],
            "duration_ms": duration_ms
        }

        log = {
            "datetime": datetime_now,
            "caller_log_code": caller_log_code,
            "logCode": "REQ_SUCCESS",
            "logMessage": "HTTP request successfully executed",
            "duration_ms": duration_ms,
            "payload": {
                "request": request_payload,
                "response": response_payload
            }
        }
        logging.info(format_log(log))
        return response

    except Exception as e:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_payload = {"status_code": "error", "error": str(e), "duration_ms": duration_ms}

        log = {
            "datetime": datetime_now,
            "caller_log_code": caller_log_code,
            "logCode": "REQ_ERROR",
            "logMessage": "HTTP request failed",
            "duration_ms": duration_ms,
            "payload": {
                "request": request_payload,
                "response": error_payload
            }
        }
        logging.error(format_log(log))
        raise e

