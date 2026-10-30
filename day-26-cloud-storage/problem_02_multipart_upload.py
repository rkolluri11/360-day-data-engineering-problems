"""Problem 2 — multipart upload: big objects go up in pieces, or not at all.

THE PROBLEM (beginner foothold first)
------------------------------------
A 40 GB export cannot be one PUT: one dropped connection restarts the
whole file, and a single request cannot hold it in memory. Object
storage splits the upload into parts — upload each part, then send a
"complete" call listing the parts, and the service assembles the
object. If any part is missing, the object must not appear half-built.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - Part numbers run 1..10000. Every part except the last must be at
    least 5 MiB — a 1 KiB middle part is a contract violation, not a
    small file, because the service rejects it at complete time.
  - Completing requires a contiguous run of parts starting at 1: a
    gap (parts 1 and 3, no 2) must fail loudly, never assemble a hole.
  - Re-uploading the same part number replaces it (retrying a failed
    part is the normal path, not an error).
  - The assembled object's ETag is the S3-style multipart ETag: the
    hex MD5 of the concatenated per-part MD5 digests, plus "-N" where
    N is the part count. A single-part upload has no "-N" suffix.
  - Abort discards every staged part and leaves no object behind;
    listing in-progress uploads shows only uploads not yet completed
    or aborted. Completing or aborting an unknown upload id is an
    error, not a no-op.

Plain words: ship the furniture in labelled boxes, check every box
arrived before you call the room furnished, and throw the boxes away
cleanly if you cancel the move.
"""

import hashlib

MIN_PART_SIZE = 5 * 1024 * 1024
MAX_PART_NUMBER = 10000


class MultipartError(ValueError):
    """Raised for a broken multipart upload: bad part, gap, or bad id."""


class MultipartStore:
    """In-memory multipart uploads over a plain dict object store."""

    def __init__(self, objects):
        # ``objects`` is a dict key -> bytes shared with the caller,
        # so a completed upload is visible exactly where objects live.
        self._objects = objects
        self._uploads = {}
        self._counter = 0

    def begin_upload(self, key):
        self._counter += 1
        upload_id = f"upload-{self._counter}"
        self._uploads[upload_id] = {"key": key, "parts": {}}
        return upload_id

    def upload_part(self, upload_id, part_number, data):
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise MultipartError(f"unknown upload id: {upload_id!r}")
        if not isinstance(part_number, int) or isinstance(part_number, bool) \
                or not 1 <= part_number <= MAX_PART_NUMBER:
            raise MultipartError(
                f"part number must be 1..{MAX_PART_NUMBER}: {part_number!r}")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("part data must be bytes")
        upload["parts"][part_number] = bytes(data)

    def complete_upload(self, upload_id):
        upload = self._uploads.get(upload_id)
        if upload is None:
            raise MultipartError(f"unknown upload id: {upload_id!r}")
        parts = upload["parts"]
        if not parts:
            raise MultipartError("cannot complete an upload with no parts")
        numbers = sorted(parts)
        if numbers != list(range(1, len(numbers) + 1)):
            raise MultipartError(
                f"part numbers must be contiguous from 1, got: {numbers}")
        for number in numbers[:-1]:
            if len(parts[number]) < MIN_PART_SIZE:
                raise MultipartError(
                    f"part {number} is {len(parts[number])} bytes, "
                    f"below the {MIN_PART_SIZE}-byte minimum for non-final parts")
        digests = b"".join(
            hashlib.md5(parts[n]).digest() for n in numbers)
        etag = hashlib.md5(digests).hexdigest() + f"-{len(numbers)}"
        self._objects[upload["key"]] = b"".join(parts[n] for n in numbers)
        del self._uploads[upload_id]
        return etag

    def abort_upload(self, upload_id):
        if upload_id not in self._uploads:
            raise MultipartError(f"unknown upload id: {upload_id!r}")
        del self._uploads[upload_id]

    def list_uploads(self):
        """Return sorted [(upload_id, key)] for in-progress uploads."""
        return sorted((uid, up["key"]) for uid, up in self._uploads.items())
