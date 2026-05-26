"""Shared pytest fixtures.

The application's DB layer is `api.db.cursor()` — a context-manager that yields
a psycopg cursor. Tests run without a live Postgres, so we patch `cursor()`
with a FakeCursor whose `fetchall()` / `fetchone()` return scripted rows.
"""
from __future__ import annotations

import contextlib
from typing import Any

import pytest


class FakeCursor:
    """Minimal cursor stand-in: dispatches SQL substring → canned rows."""

    def __init__(self, scripts: dict[str, list[dict]]):
        # `scripts` maps a substring (case-insensitive) of the SQL to rows.
        self._scripts = {k.lower(): v for k, v in scripts.items()}
        self._last: list[dict] = []

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        sql_l = sql.lower()
        # Longest matching key wins so more specific SQL beats a generic substring.
        match = max(
            (k for k in self._scripts if k in sql_l),
            key=len,
            default=None,
        )
        self._last = list(self._scripts.get(match, []))

    def fetchall(self) -> list[dict]:
        return self._last

    def fetchone(self) -> dict | None:
        return self._last[0] if self._last else None


@pytest.fixture
def fake_cursor(monkeypatch):
    """Returns a builder: `build({sql_substr: rows})` patches api.db.cursor."""

    def build(scripts: dict[str, list[dict]]):
        cur = FakeCursor(scripts)

        @contextlib.contextmanager
        def fake_cm():
            yield cur

        # Patch every import site of `cursor`.
        import api.db
        import simulator.impact
        import optimizer.allocator
        import simulator.projector
        import api.routes.export
        monkeypatch.setattr(api.db, "cursor", fake_cm)
        monkeypatch.setattr(simulator.impact, "cursor", fake_cm)
        monkeypatch.setattr(optimizer.allocator, "cursor", fake_cm)
        monkeypatch.setattr(api.routes.export, "cursor", fake_cm)
        return cur

    return build
