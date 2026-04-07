from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from app.config import RSVP_SERVER_HOST, RSVP_SERVER_PORT
from services.rsvp_service import RSVPService
from services.rsvp_token_service import RSVPTokenService
from services.outing_service import OutingService
from repositories.member_repository import MemberRepository


class _RSVPRequestHandler(BaseHTTPRequestHandler):
    rsvp_service: RSVPService | None = None
    token_service: RSVPTokenService | None = None
    outing_service: OutingService | None = None
    member_repo: MemberRepository | None = None

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != "/rsvp/yes":
            self._send_html(
                404,
                "<html><body><h1>Not Found</h1></body></html>",
            )
            return

        params = parse_qs(parsed.query)
        token = params.get("token", [""])[0].strip()

        if not token:
            self._send_html(
                400,
                "<html><body><h1>Missing token</h1></body></html>",
            )
            return

        try:
            assert self.token_service is not None
            assert self.rsvp_service is not None
            assert self.outing_service is not None
            assert self.member_repo is not None

            outing_id, member_id = self.token_service.decode_token(token)
            self.rsvp_service.record_yes_if_first(outing_id, member_id)

            outing = self.outing_service.get_outing(outing_id)
            member = self.member_repo.get(member_id)

            course_name = str(outing["course_name"] or "") if outing else ""
            outing_date = str(outing["outing_date"] or "") if outing else ""
            member_name = ""
            if member:
                member_name = f"{member['first_name']} {member['last_name']}".strip()

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>RSVP Recorded</h1>
                <p>Thanks{f", {member_name}" if member_name else ""}. Your RSVP YES has been recorded.</p>
                <p><strong>Course:</strong> {course_name}</p>
                <p><strong>Date:</strong> {outing_date}</p>
              </body>
            </html>
            """
            self._send_html(200, html)

        except Exception as exc:
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>RSVP Error</h1>
                <p>{str(exc)}</p>
              </body>
            </html>
            """
            self._send_html(400, html)

    def log_message(self, format, *args):
        return

    def _send_html(self, status_code: int, body: str):
        encoded = body.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class RSVPHTTPServer:
    def __init__(self, db):
        self.db = db
        self.server: HTTPServer | None = None

    def start(self):
        if self.server is not None:
            return

        handler = _RSVPRequestHandler
        handler.rsvp_service = RSVPService(self.db)
        handler.token_service = RSVPTokenService()
        handler.outing_service = OutingService(self.db)
        handler.member_repo = MemberRepository(self.db)

        self.server = HTTPServer(
            (RSVP_SERVER_HOST, RSVP_SERVER_PORT),
            handler,
        )
        print(f"RSVP server listening on http://{RSVP_SERVER_HOST}:{RSVP_SERVER_PORT}")
        self.server.serve_forever()

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
