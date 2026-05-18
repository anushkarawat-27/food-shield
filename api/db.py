import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def get_conn() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


@contextmanager
def cursor():
    with get_conn() as conn, conn.cursor() as cur:
        yield cur
        conn.commit()
