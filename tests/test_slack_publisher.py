import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from slack.publisher import build_payload, publish_digest


class _CaptureHandler(BaseHTTPRequestHandler):
    payload = None

    def do_POST(self) -> None:  # noqa: N802 - inherited HTTP handler API
        length = int(self.headers["Content-Length"])
        type(self).payload = json.loads(self.rfile.read(length))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args) -> None:
        return


class SlackPublisherTests(unittest.TestCase):
    def test_payload_has_fallback_text_and_blocks(self) -> None:
        payload = build_payload("# Digest\n- Update [M001]", "PM", "DVT")
        self.assertIn("EverCurrent Daily Digest", payload["text"])
        self.assertEqual(payload["blocks"][0]["type"], "header")
        self.assertIn("[M001]", payload["blocks"][-1]["text"]["text"])

    def test_posts_json_to_webhook(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/webhook"
            publish_digest(url, "# Digest\n- Update [M001]", "PM", "DVT")
            self.assertEqual(_CaptureHandler.payload["blocks"][0]["type"], "header")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
