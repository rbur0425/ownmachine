"""Durable local control gate. All users of one VM must share this database.

BEGIN IMMEDIATE serializes transfers with writes across processes. A durable
in-flight marker survives a killed writer and prevents further input until an
operator acknowledges it through a transfer. Missing state starts paused.
This is a trusted-operator gate, not an authentication boundary against shell users.
"""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3


class LeaseError(RuntimeError):
    pass


class Lease:
    def __init__(self, path, timeout=35):
        self.path = Path(path)
        self.timeout = timeout
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY CHECK(id=1), controller TEXT NOT NULL, generation INTEGER NOT NULL, pending INTEGER NOT NULL)")
            db.execute("INSERT OR IGNORE INTO lease VALUES (1, 'paused', 0, 0)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=self.timeout)

    @contextmanager
    def _locked(self):
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _state(db):
        row = db.execute("SELECT controller, generation, pending FROM lease WHERE id=1").fetchone()
        if row is None or row[0] not in {"agent", "human", "paused"}:
            raise LeaseError("lease_invalid")
        return dict(controller=row[0], generation=row[1], pending=bool(row[2]))

    def status(self):
        db = self._connect()
        try:
            return self._state(db)
        finally:
            db.close()

    def transfer(self, controller, *, acknowledge=True):
        if controller not in {"agent", "human", "paused"}:
            raise LeaseError("invalid_controller")
        with self._locked() as db:
            state = self._state(db)
            if state["pending"] and not acknowledge:
                raise LeaseError("operator_review_required")
            db.execute("UPDATE lease SET controller=?, generation=generation+1, pending=0 WHERE id=1", (controller,))
            return self._state(db)

    @contextmanager
    def write(self, capture_generation, *, controller="agent"):
        if controller not in {"agent", "human"}:
            raise LeaseError("invalid_controller")
        # Mark uncertain outcome durably before dispatch. Transfer between these
        # two transactions is detected by the generation check below.
        with self._locked() as db:
            state = self._state(db)
            if state['controller'] != controller:
                raise LeaseError("human_takeover" if state['controller'] == 'human' else "paused")
            if state['pending']:
                raise LeaseError("transport_outcome_unknown")
            if capture_generation != state['generation']:
                raise LeaseError("stale_target")
            db.execute("UPDATE lease SET pending=1 WHERE id=1")
        with self._locked() as db:
            state = self._state(db)
            if state['generation'] != capture_generation or state['controller'] != controller:
                raise LeaseError("stale_target")
            # Exceptions roll back this transaction, retaining the durable marker.
            yield
            db.execute("UPDATE lease SET pending=0 WHERE id=1")

    @contextmanager
    def lifecycle(self):
        """Operator lifecycle transaction: invalidate targets and stay paused."""
        with self._locked() as db:
            state = self._state(db)
            if state['pending']:
                raise LeaseError('operator_review_required')
            db.execute("UPDATE lease SET controller='paused', generation=generation+1, pending=1 WHERE id=1")
            generation = self._state(db)['generation']
        with self._locked() as db:
            state = self._state(db)
            if state['generation'] != generation or state['controller'] != 'paused':
                raise LeaseError('control_changed')
            yield
            db.execute("UPDATE lease SET pending=0 WHERE id=1")
