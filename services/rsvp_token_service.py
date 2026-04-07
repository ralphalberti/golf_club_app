import base64
import hashlib
import hmac

from app.config import RSVP_TOKEN_SECRET


class RSVPTokenService:
    def __init__(self, secret: str | None = None):
        self.secret = (secret or RSVP_TOKEN_SECRET).encode("utf-8")

    def create_token(self, outing_id: int, member_id: int) -> str:
        payload = f"{outing_id}:{member_id}"
        signature = hmac.new(
            self.secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        token = f"{payload}:{signature}"
        return base64.urlsafe_b64encode(token.encode("utf-8")).decode("utf-8")

    def decode_token(self, token: str) -> tuple[int, int]:
        try:
            raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
            outing_id_str, member_id_str, signature = raw.split(":", 2)
        except Exception as exc:
            raise ValueError("Invalid RSVP token format.") from exc

        payload = f"{outing_id_str}:{member_id_str}"
        expected_signature = hmac.new(
            self.secret,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid RSVP token signature.")

        return int(outing_id_str), int(member_id_str)
