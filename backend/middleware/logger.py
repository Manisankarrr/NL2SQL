"""
Usage Example:
from backend.middleware.logger import pipeline_logger, setup_logging

# 1. startup
setup_logging("INFO")
pipeline_logger.stage("Initializing system")

# 2. API call
pipeline_logger.api("POST", "openrouter.ai", 200, 1.42)

# 3. DB query
pipeline_logger.db("SELECT", "appointments", 12, 0.030)

# 4. validation block
pipeline_logger.warn("Validation blocked SQL: DROP TABLE appointments")

# 5. done
pipeline_logger.done()
"""
import sys
import time
import uuid
import logging
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware

# Configure standard streams to support unicode printing on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

class CallableCounter:
    def __init__(self, method):
        self.method = method
        self.value = 0

    def __call__(self, *args, **kwargs):
        return self.method(*args, **kwargs)

    def __iadd__(self, other):
        self.value += other
        return self

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)

    def __int__(self):
        return self.value


class PipelineLogger:
    def __init__(self, app_name: str = "BarberSQL", session_id: str = None):
        self.app_name = app_name
        self.session_id = session_id if session_id else uuid.uuid4().hex[:8]
        self.start_time = time.perf_counter()
        
        # Prevent attribute name collision with methods 'ok' and 'warn'
        self.ok = CallableCounter(self._ok_method)
        self.warn = CallableCounter(self._warn_method)
        self.err = 0
        
        self._print_header()

    def _print_header(self):
        print("─" * 52)
        print(f" {self.app_name}  |  session: {self.session_id}")
        print("─" * 52)

    def _now(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _line(self, symbol: str, tag: str, message: str):
        tag_padded = f"{tag:<10}"
        print(f"{self._now()} {symbol} [{tag_padded}] {message}")

    def _ok_method(self, message: str):
        self.ok += 1
        self._line("✓", "OK", message)

    def stage(self, message: str):
        self._line("→", "STAGE", f"▶ {message}")

    def step(self, message: str):
        self._line(" ", "STEP", message)

    def result(self, message: str):
        self.ok += 1
        self._line("✓", "RESULT", message)

    def api(self, method: str, host: str, status: int, elapsed_s: float):
        self._line("⇆", "API", f"{method} {host} · {status} · {elapsed_s:.2f}s")

    def db(self, operation: str, table: str, rows: int, elapsed_s: float):
        self._line("◉", "DB", f"{operation} · {table} · {rows} rows · {elapsed_s:.3f}s")

    def _warn_method(self, message: str):
        self.warn += 1
        self._line("⚠", "WARN", message)

    def error(self, message: str, exc: Exception = None):
        self.err += 1
        if exc is not None:
            message += f" — {type(exc).__name__}: {exc}"
        self._line("✗", "ERROR", message)

    def done(self, message: str = "Complete"):
        elapsed = round(time.perf_counter() - self.start_time, 1)
        full_message = f"{message} · elapsed={elapsed}s ok={self.ok} warn={self.warn} err={self.err}"
        self._line("✓", "DONE", full_message)
        print("─" * 52)



def setup_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiomysql").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("gradio").setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        
        # Route standard HTTP requests through the pipeline log structure
        pipeline_logger.api(request.method, str(request.url.path), response.status_code, elapsed)
        
        return response


# Module-level convenience singleton
pipeline_logger = PipelineLogger()
