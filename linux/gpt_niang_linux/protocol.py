"""Bounded byte-oriented JSONL decoding, including split UTF-8 sequences."""
import json

SCHEMA_VERSION = 1
MAX_LINE = 256 * 1024
TYPES = {"refreshing", "snapshot", "error", "shutdown"}


class ProtocolError(ValueError):
    pass


class Decoder:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk):
        messages = []
        for part in bytes(chunk).splitlines(keepends=True):
            self.buffer.extend(part)
            if len(self.buffer) > MAX_LINE:
                self.buffer.clear()
                raise ProtocolError("message too large")
            if not self.buffer.endswith(b"\n"):
                continue
            line = bytes(self.buffer).strip()
            self.buffer.clear()
            if not line:
                continue
            try:
                message = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise ProtocolError("invalid JSON") from exc
            if not isinstance(message, dict) or message.get("schemaVersion") != SCHEMA_VERSION or message.get("type") not in TYPES:
                raise ProtocolError("invalid protocol envelope")
            request_id = message.get("requestId")
            if request_id is not None and (not isinstance(request_id, str) or len(request_id) > 64):
                raise ProtocolError("invalid request id")
            messages.append(message)
        return messages
