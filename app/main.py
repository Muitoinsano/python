import uuid
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import generate_latest, start_http_server
from http_metrics import instrumented_request

app = FastAPI()

# Configurar o logger para capturar mensagens detalhadas
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
CALLER_LOG_CODE = "MAIN_test_post"

# Endpoint de métricas para Prometheus
@app.get('/metrics')
async def metrics():
    return PlainTextResponse(generate_latest(), media_type='text/plain')

# Endpoint para testar POST, GET e DELETE
@app.post('/test-post')
@app.get('/test-post')
@app.delete('/test-post/{id_cards}')
async def test_post(request: Request, id_cards: str = None):
    # Transformar os cabeçalhos para um dicionário mutável
    mutable_headers = dict(request.headers)

    for header in [
        "user-agent", "accept", "postman-token", "host",
        "accept-encoding", "connection", "content-length"
    ]:
        mutable_headers.pop(header, None)

    try:
        if request.method == 'POST':
            # Para o método POST, envia dados
            data = await request.json()  # JSON do corpo da requisição
            if not data:
                raise HTTPException(status_code=400, detail="O corpo da requisição JSON é obrigatório para POST.")

            # Chamada ao endpoint usando instrumented_request
            response = instrumented_request(
                {
                    "method": "POST",
                    "url": "https://5e9618385b19f10016b5e25c.mockapi.io/testeInteiro/cards",
                    "headers": mutable_headers,
                    "kwargs": {"json": data}
                },
                {
                    "caller_log_code": CALLER_LOG_CODE,
                    "mask_headers_request": ["authorization"],
                    "mask_body_request": ["description"],
                    "mask_body_response": ["numero","description"]
                }
            )

            # Validar o tipo de resposta antes de acessar .json()
            response_data = response.json() if hasattr(response, 'json') else response.text

            return JSONResponse(
                content={"status": response.status_code, "response": response_data},
                status_code=response.status_code
            )

        elif request.method == 'DELETE':
            # Validar o parâmetro id_cards
            if not id_cards:
                raise HTTPException(status_code=400, detail="O parâmetro 'id_cards' na URL é obrigatório para DELETE.")

            # Construir a URL com o ID
            url = f"https://5e9618385b19f10016b5e25c.mockapi.io/testeInteiro/cards/{id_cards}"

            # Chamada ao endpoint usando instrumented_request
            response = instrumented_request(
                {
                    "method": "DELETE",
                    "url": url,
                    "headers": mutable_headers
                },
                {
                    "mask_headers": ["Authorization"]
                }
            )

            # Validar o tipo de resposta antes de acessar .json()
            response_data = response.json() if hasattr(response, 'json') else response.text

            return JSONResponse(
                content={"status": response.status_code, "response": response_data},
                status_code=response.status_code
            )

    except Exception as e:
        # Logar a stack trace completa
        logger.error("Erro ao processar a requisição", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar a requisição.")

# Inicialização do servidor
if __name__ == '__main__':
    import uvicorn
    start_http_server(8000)  # Prometheus endpoint (porta 8000)
    uvicorn.run(app, host='0.0.0.0', port=5000)
