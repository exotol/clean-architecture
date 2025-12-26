PATH_TO_SETTINGS = "configs/settings.toml"
PATH_TO_SECRETS = "configs/.secrets.toml"
PATH_TO_ENVS = "configs/.env"

HELLO_WORLD = "Hello World"

DEFAULT_PROBLEM_DETAIL_TYPE = "about:blank"
TRACE_ID = "X-Request-ID"
USER_ID = "X-User-ID"
VALIDATION_UUID_OFF = None
NO_PARAMS = None


# Metrics
METRICS_REQUESTS_TOTAL_NAME = "app_requests_total"
METRICS_REQUESTS_TOTAL_DESC = "Total number of requests"
METRICS_REQUESTS_TOTAL_UNIT = "1"

METRICS_REQUEST_DURATION_NAME = "app_request_duration_seconds"
METRICS_REQUEST_DURATION_DESC = "Request duration in seconds"
METRICS_REQUEST_DURATION_UNIT = "s"

# Tracing
OTLP_LOCAL_ENDPOINT = "console"