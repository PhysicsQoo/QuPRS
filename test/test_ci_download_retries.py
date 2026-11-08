"""Offline integration tests for scoped CodSpeed installer download retries."""
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import shutil
import subprocess
import threading

import pytest

CURL_HOME = Path(__file__).resolve().parents[1] / ".github" / "codspeed-download"


def _request(statuses, tmp_path):
    class Handler(BaseHTTPRequestHandler):
        count = 0

        def do_GET(self):
            type(self).count += 1
            code = statuses[min(type(self).count - 1, len(statuses) - 1)]
            body = str(code).encode("ascii")
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        env = os.environ.copy()
        env["CURL_HOME"] = str(CURL_HOME)
        output = tmp_path / "response.txt"
        result = subprocess.run(
            ["curl", "-sSL", "-w", "%{http_code}", "-o", str(output),
             f"http://127.0.0.1:{server.server_port}/installer"],
            env=env, capture_output=True, text=True, timeout=20, check=False,
        )
        return Handler.count, result
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is unavailable")
def test_codspeed_retries_transient_http_504(tmp_path):
    count, result = _request([504, 200], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "200"
    assert count == 2


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is unavailable")
def test_codspeed_does_not_retry_permanent_http_404(tmp_path):
    count, result = _request([404, 200], tmp_path)
    # The upstream action checks the resulting HTTP code and rejects >=400.
    assert result.returncode == 0, result.stderr
    assert result.stdout == "404"
    assert count == 1
