from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from app.config import RSVP_SERVER_HOST, RSVP_SERVER_PORT
from services.rsvp_service import RSVPService
from services.rsvp_token_service import RSVPTokenService
from services.outing_service import OutingService
from services.open_slot_token_service import OpenSlotTokenService
from repositories.member_repository import MemberRepository
from html import escape
from repositories.guest_repository import GuestRepository


class _RSVPRequestHandler(BaseHTTPRequestHandler):
    rsvp_service: RSVPService | None = None
    token_service: RSVPTokenService | None = None
    outing_service: OutingService | None = None
    member_repo: MemberRepository | None = None
    open_slot_token_service: OpenSlotTokenService | None = None

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/rsvp/yes":
            self._handle_rsvp_yes(parsed)
            return

        if parsed.path == "/rsvp/cancel":
            self._handle_rsvp_cancel(parsed)
            return

        if parsed.path == "/claim-open-slot":
            self._handle_claim_open_slot(parsed)
            return

        self._send_html(
            404,
            "<html><body><h1>Not Found</h1></body></html>",
        )

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/rsvp/guests":
            self._handle_rsvp_guests_post()
            return

        self._send_html(
            404,
            "<html><body><h1>Not Found</h1></body></html>",
        )

    def _handle_rsvp_yes(self, parsed):
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
            self.rsvp_service.set_member_rsvp_status(
                outing_id,
                member_id,
                "yes",
                "RSVP yes via email link",
            )

            outing = self.outing_service.get_outing(outing_id)
            member = self.member_repo.get(member_id)

            course_name = str(outing["course_name"] or "") if outing else ""
            outing_date = str(outing["outing_date"] or "") if outing else ""
            member_name = ""
            if member:
                member_name = f"{member['first_name']} {member['last_name']}".strip()

            safe_token = escape(token, quote=True)

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>RSVP Recorded</h1>
                <p>Thanks{f", {member_name}" if member_name else ""}. Your RSVP YES has been recorded.</p>
                <p><strong>Course:</strong> {course_name}</p>
                <p><strong>Date:</strong> {outing_date}</p>

                <hr style="margin: 28px 0;">

                <h2>Bringing a guest?</h2>
                <p>If you plan to bring guests, add them here. Otherwise, you are all set.</p>

                <form method="POST" action="/rsvp/guests">
                  <input type="hidden" name="token" value="{safe_token}">

                  <p><strong>Guest 1</strong></p>
                  <p>
                    <input type="text" name="guest1_first" placeholder="First name" style="width:160px; margin-right:8px;">
                    <input type="text" name="guest1_last" placeholder="Last name" style="width:160px;">
                  </p>

                  <p><strong>Guest 2</strong></p>
                  <p>
                    <input type="text" name="guest2_first" placeholder="First name" style="width:160px; margin-right:8px;">
                    <input type="text" name="guest2_last" placeholder="Last name" style="width:160px;">
                  </p>

                  <p><strong>Guest 3</strong></p>
                  <p>
                    <input type="text" name="guest3_first" placeholder="First name" style="width:160px; margin-right:8px;">
                    <input type="text" name="guest3_last" placeholder="Last name" style="width:160px;">
                  </p>

                  <p style="margin-top: 16px;">
                    <button type="submit" style="padding: 8px 16px; font-size: 14px;">
                      Add guests
                    </button>
                  </p>
                </form>
              </body>
            </html>
            """
            self._send_html(200, html)

        except Exception as exc:
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>RSVP Error</h1>
                <p>{exc.__class__.__name__}: {str(exc)}</p>
              </body>
            </html>
            """
            self._send_html(400, html)

    def _handle_rsvp_guests_post(self):
        try:
            assert self.token_service is not None
            assert self.outing_service is not None
            assert self.member_repo is not None
            assert self.rsvp_service is not None

            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            params = parse_qs(raw_body)

            token = params.get("token", [""])[0].strip()
            if not token:
                raise ValueError("Missing token.")

            outing_id, member_id = self.token_service.decode_token(token)

            outing = self.outing_service.get_outing(outing_id)
            member = self.member_repo.get(member_id)

            if not outing:
                raise ValueError("Outing not found.")
            if not member:
                raise ValueError("Member not found.")

            # Keep RSVP yes intact / refresh note.
            self.rsvp_service.set_member_rsvp_status(
                outing_id,
                member_id,
                "yes",
                "RSVP yes via email link; guests submitted",
            )

            guest_repo = GuestRepository(self.rsvp_service.repo.db)

            saved_guest_names: list[str] = []

            for index in range(1, 4):
                first_name = params.get(f"guest{index}_first", [""])[0].strip()
                last_name = params.get(f"guest{index}_last", [""])[0].strip()

                if not first_name and not last_name:
                    continue

                if not first_name:
                    first_name = "Guest"

                guest_id = guest_repo.create_guest(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": "",
                        "phone": "",
                        "notes": f"Added via RSVP form for outing {outing_id}",
                        "active": 1,
                    }
                )

                guest_repo.add_guest_to_outing(
                    outing_id=outing_id,
                    guest_id=guest_id,
                    sponsoring_member_id=member_id,
                    status="yes",
                    note="Added via RSVP form",
                )

                saved_guest_names.append(f"{first_name} {last_name}".strip())

            member_name = f"{member['first_name']} {member['last_name']}".strip()
            course_name = str(outing["course_name"] or "")
            outing_date = str(outing["outing_date"] or "")

            if saved_guest_names:
                guest_items = "".join(
                    f"<li>{escape(name)}</li>" for name in saved_guest_names
                )
                guest_html = f"<ul>{guest_items}</ul>"
            else:
                guest_html = "<p>No guest names were entered.</p>"

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>Guests Saved</h1>
                <p>Thanks, {escape(member_name)}. Your guest information has been saved.</p>
                <p><strong>Course:</strong> {escape(course_name)}</p>
                <p><strong>Date:</strong> {escape(outing_date)}</p>
                {guest_html}
              </body>
            </html>
            """
            self._send_html(200, html)

        except Exception as exc:
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>Guest RSVP Error</h1>
                <p>{escape(exc.__class__.__name__)}: {escape(str(exc))}</p>
              </body>
            </html>
            """
            self._send_html(400, html)

    def _handle_rsvp_cancel(self, parsed):
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

            outing = self.outing_service.get_outing(outing_id)
            member = self.member_repo.get(member_id)

            if not outing:
                raise ValueError("Outing not found.")
            if not member:
                raise ValueError("Member not found.")

            vacated_tee_time_id = self.outing_service.get_member_tee_time_id_for_outing(
                outing_id,
                member_id,
            )

            self.rsvp_service.set_member_rsvp_status(
                outing_id,
                member_id,
                "invited",
                "Cancelled via email link",
            )

            # Remove from schedule if assigned
            if self.outing_service.is_member_assigned_for_outing(outing_id, member_id):
                self.outing_service.remove_member_from_schedule(outing_id, member_id)

            # Auto-promote next waitlist player
            if vacated_tee_time_id is not None:
                print(
                    "Calling targeted waitlist promotion",
                    outing_id,
                    vacated_tee_time_id,
                )

                self.outing_service.auto_promote_waitlist_to_tee_time(
                    outing_id,
                    vacated_tee_time_id,
                )
            else:
                print("Calling fallback waitlist promotion", outing_id)

                self.outing_service.auto_promote_waitlist(outing_id)

            member_name = f"{member['first_name']} {member['last_name']}".strip()
            course_name = str(outing["course_name"] or "")
            outing_date = str(outing["outing_date"] or "")

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>Cancellation Recorded</h1>
                <p>Thanks, {member_name}. You have been removed from the outing.</p>
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
                <h1>Cancellation Error</h1>
                <p>{exc.__class__.__name__}: {str(exc)}</p>
              </body>
            </html>
            """
            self._send_html(400, html)

    def _handle_claim_open_slot(self, parsed):
        params = parse_qs(parsed.query)
        token = params.get("token", [""])[0].strip()

        if not token:
            self._send_html(
                400,
                "<html><body><h1>Missing token</h1></body></html>",
            )
            return

        try:
            assert self.open_slot_token_service is not None
            assert self.rsvp_service is not None
            assert self.outing_service is not None
            assert self.member_repo is not None

            outing_id, member_id, tee_time_id = (
                self.open_slot_token_service.decode_token(token)
            )

            member = self.member_repo.get(member_id)
            if not member:
                raise ValueError("Member not found.")

            if int(member["active"]) != 1:
                raise ValueError("This member is not active.")

            outing = self.outing_service.get_outing(outing_id)
            if not outing:
                raise ValueError("Outing not found.")

            tee_time = self.outing_service.get_tee_time_by_id(tee_time_id)
            if not tee_time:
                raise ValueError("Tee time not found.")

            if int(tee_time["outing_id"]) != int(outing_id):
                raise ValueError("This tee time does not belong to the outing.")

            existing_rsvps = self.rsvp_service.list_member_rsvps_for_outing(outing_id)
            invited_member_ids = {int(row["member_id"]) for row in existing_rsvps}
            if member_id not in invited_member_ids:
                raise ValueError("This member was not invited for the outing.")

            if self.outing_service.is_member_assigned_for_outing(outing_id, member_id):
                raise ValueError(
                    "You are already assigned to a tee time for this outing."
                )

            yes_member_ids = set(
                self.rsvp_service.get_schedulable_member_ids(outing_id)
            )
            if member_id in yes_member_ids:
                raise ValueError("You already responded YES for this outing.")

            self.outing_service.add_member_to_tee_time(
                outing_id=outing_id,
                tee_time_id=tee_time_id,
                member_id=member_id,
            )

            self.rsvp_service.set_member_rsvp_status(
                outing_id,
                member_id,
                "yes",
                "Claimed open slot via email link",
            )

            member_name = f"{member['first_name']} {member['last_name']}".strip()
            course_name = str(outing["course_name"] or "")
            outing_date = str(outing["outing_date"] or "")
            tee_time_text = str(tee_time["tee_time"] or "")

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>Open Slot Claimed</h1>
                <p>Thanks, {member_name}. You have been added to the outing.</p>
                <p><strong>Course:</strong> {course_name}</p>
                <p><strong>Date:</strong> {outing_date}</p>
                <p><strong>Tee Time:</strong> {tee_time_text}</p>
              </body>
            </html>
            """
            self._send_html(200, html)

        except Exception as exc:
            # remove later
            print(repr(exc))
            message = str(exc).strip() or exc.__class__.__name__

            lines = [line.strip() for line in message.splitlines() if line.strip()]
            if len(lines) >= 2 and all(line == lines[0] for line in lines):
                message = lines[0]

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 24px;">
                <h1>Open Slot Unavailable</h1>
                <p>{message}</p>
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
        handler.open_slot_token_service = OpenSlotTokenService()

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
