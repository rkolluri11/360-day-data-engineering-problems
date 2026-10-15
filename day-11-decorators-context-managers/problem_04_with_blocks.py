"""Problem 4 — Context managers: the cursor closes even on exception
==================================================================

THE PROBLEM (beginner foothold first)
------------------------------------
The Day 11 post's 2 AM story: a job opened a DB cursor, the API call
in the middle threw, and the connection hung until the pool timed
out. Manual open/close can't survive exceptions — the ``close()``
after the throw never runs. A CONTEXT MANAGER moves the cleanup into
``__exit__``, which Python GUARANTEES to run:

    with managed_connection(pool) as conn:
        rows = call_api(conn)     # throws? conn still closes.

Plain words: the borrowed truck returns with a full tank even when
the trip goes wrong.

THE HARD VERSION (what actually breaks in production)
----------------------------------------------------
  - ``__exit__`` must COMMIT on a clean exit and ROLL BACK when the
    block raised — a half-written batch committed by accident is data
    corruption, not resilience.
  - ``__exit__`` must CLOSE in a ``finally`` of its own: a commit that
    throws must not skip the close.
  - ``__exit__`` returns ``False`` — it NEVER swallows the exception.
    Swallowing hides the 2 AM page; the caller decides what to do.
  - Both spellings are shown: a class (``__enter__``/``__exit__``) and
    the generator form (``@contextmanager``), where everything after
    ``yield`` is the ``__exit__``.

Your solution: ``managed_connection`` (class) and
``managed_connection_gen`` (generator form). Then run the tests:
``python -m pytest tests -q``.

ANALOGY
-------
A context manager returns your borrowed truck with a full tank —
setup, use, guaranteed return. The ``with`` block is the rental
contract; ``__exit__`` is the part that makes sure the truck comes
back no matter how the trip ended.
"""

from contextlib import contextmanager


class FakeConnection:
    """Stand-in for a DBAPI connection; tracks its own lifecycle."""

    def __init__(self):
        self.committed = 0
        self.rolled_back = 0
        self.closed = 0

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed += 1


class managed_connection:
    """Class-based context manager: commit on success, rollback on
    error, always close, never swallow the exception."""

    def __init__(self, factory=FakeConnection):
        self._factory = factory

    def __enter__(self):
        self.conn = self._factory()
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.conn.close()
        return False  # never swallow — the caller owns the exception


@contextmanager
def managed_connection_gen(factory=FakeConnection):
    """Generator spelling of the same contract: code after ``yield``
    is the ``__exit__``."""
    conn = factory()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    with managed_connection() as conn:
        conn.commit  # no-op; real work goes here
    print("clean exit:", conn.committed, conn.rolled_back, conn.closed)

    try:
        with managed_connection() as conn2:
            raise RuntimeError("mid-batch failure")
    except RuntimeError:
        pass
    print("on error:  ", conn2.committed, conn2.rolled_back, conn2.closed)

    with managed_connection_gen() as conn3:
        pass
    print("gen form:  ", conn3.committed, conn3.rolled_back, conn3.closed)
