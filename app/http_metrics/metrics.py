from prometheus_client import Counter, Histogram

# Contador de requisições HTTP
http_requests_total = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status']
)

# Histograma de latência das requisições
http_request_latency = Histogram(
    'http_request_latency_seconds',
    'Latência das requisições HTTP',
    ['method', 'endpoint', 'status']
)