from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


class HealthcheckHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != '/health':
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = b'ok\n'
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def start_healthcheck_server(*, host: str = '0.0.0.0', port: int = 8000) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), HealthcheckHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
