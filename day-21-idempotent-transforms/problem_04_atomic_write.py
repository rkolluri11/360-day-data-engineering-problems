"""Problem 4 — write-then-rename: a file is never half-written
============================================================

THE PROBLEM (beginner foothold first)
------------------------------------
A job writes its output file directly. It crashes halfway and
leaves a HALF file behind — and the next reader cannot tell a
half file from a complete one:

    # NOT replay-safe: a crash leaves a torn file
    with open("out.csv", "w") as f:
        f.write(huge_output)      # crash here -> corrupt out.csv

Write-then-rename fixes it: write the full output to a TEMP
file in the same directory, then rename it over the target.
A rename inside one filesystem is atomic — readers see either
the old complete file or the new complete file, never a half:

    # replay-safe: crash leaves the old file intact
    with open("out.csv.tmp", "w") as f:
        f.write(huge_output)
    os.replace("out.csv.tmp", "out.csv")

Replaying the write just replaces the file with identical
bytes. No reader ever sees a torn write.

Plain words: direct writing is painting the shop sign while
customers read it — mid-stroke it says nonsense. Write-then-
rename is painting a new sign in the back room and swapping it
in one motion.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - The temp file MUST live in the same directory (same
    filesystem) as the target. ``os.replace`` across filesystems
    is a copy, not an atomic rename, and re-opens the torn
    window. A temp dir on another mount silently breaks the
    guarantee.
  - Flush + fsync before the rename, or the OS may report the
    rename done while the bytes are still only in a buffer.
    The rename is atomic; durability still needs the fsync.
  - A crashed writer leaves orphan temp files. They are harmless
    (the target is untouched) but must be cleaned up — and the
    cleanup must never delete a temp file another live writer
    is still filling. Unique temp names per writer solve that.
  - Replaying with DIFFERENT content is a full replacement,
    not a merge: the old bytes are gone, not appended to. That
    is the correct semantic for a regenerated output file.

Your solution: ``write_atomic`` is already written. The tests
prove replayed writes leave identical bytes, no temp files
remain, and a replacement fully replaces the old content.

ANALOGY
-------
Write-then-rename is replacing a bridge by building the new one
beside it and sliding it into place overnight. Nobody ever
drives across a half-built bridge.
"""

import os
import tempfile


def write_atomic(path, text):
    """Write text to path atomically: temp file + os.replace.

    Returns the path. After the call the file holds exactly
    ``text``; no temp file remains in the directory.
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return path
