"""Local replacement for Chartio's dead SQLBox backend (sqlbox.herokuapp.com).

Contract (reverse-engineered from dataschool/assets/sqlbox/sqlbox.js):

- POST /  with form fields: sql, dbtype, dbname, answer
- Response JSON:
    {"sqlerror": "..."}                      on SQL error
    {"columns": [{"title": "..."}],          on success
     "data": [[...]],
     "correct_data": true|false}

The success response is passed straight into bootstrap-table 1.14.2 by
sqlbox.js, which requires: columns = array of column OBJECTS (no `field` key ->
bootstrap-table assigns numeric indexes), data = array of row ARRAYS (indexed by
those numbers). A plain `{"columns": ["name"], "rows": [...]}` shape throws
`can't assign to property "fieldIndex" on string`.
- CORS must allow http://localhost:4000 with credentials, since the site JS
  uses $.ajax with withCredentials: true.

`answer` correctness is judged by resultset equality (per sqlbox.js docs:
"This is not matched character by character, but by the resultsets being the same").
Rows are compared as an ordered multiset (order-insensitive) because answer SQL
often omits ORDER BY.
"""

import logging
import os
import re

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sqlbox")

PGHOST = os.environ.get("PGHOST", "db")
PGPORT = os.environ.get("PGPORT", "5432")
PGDATABASE = os.environ.get("PGDATABASE", "herokuchinook")
PGUSER = os.environ.get("PGUSER", "readonly")
PGPASSWORD = os.environ.get("PGPASSWORD", "readonly")

SITE_ORIGIN = os.environ.get("SITE_ORIGIN", "http://localhost:4000")
MAX_ROWS = int(os.environ.get("MAX_ROWS", "500"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[SITE_ORIGIN],
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


def get_conn():
    return psycopg2.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        options="-c statement_timeout=10000",
    )


def run_query(sql: str):
    """Execute a single SELECT and return (columns, rows)."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        if cur.description is None:
            raise ValueError("Query returned no result set. Only SELECT queries are allowed.")
        columns = [d.name for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
        truncated = len(rows) > MAX_ROWS
        return columns, rows[:MAX_ROWS], truncated


def normalize_cell(v):
    if v is None:
        return None
    if isinstance(v, float):
        return round(v, 9)
    return str(v) if not isinstance(v, (int, bool)) else v


def resultset_matches(sql_a: str, sql_b: str) -> bool:
    """Compare resultsets of two queries (order-insensitive).

    Cell values within each row are also compared order-insensitively:
    the tutorials explicitly treat `SELECT title, id` as correct for
    answer `SELECT id, title` (see basic/from.md quiz).
    """
    try:
        _c1, r1, _t1 = run_query(sql_a)
        _c2, r2, _t2 = run_query(sql_b)
    except Exception:
        return False
    if len(r1) != len(r2):
        return False
    def key(rows):
        return sorted(tuple(sorted((repr(normalize_cell(c)) for c in row))) for row in rows)
    return key(r1) == key(r2)


IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@app.get("/health")
def health():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "db error", "detail": str(e)})


@app.post("/")
def sqlbox(request: Request, sql: str = Form(""), dbtype: str = Form(""), dbname: str = Form(""), answer: str = Form("")):
    origin = request.headers.get("origin")
    sql = (sql or "").strip().rstrip(";")
    answer = (answer or "").strip()

    # --- guards -------------------------------------------------------------
    if not sql:
        return JSONResponse(status_code=400, content={"sqlerror": "No SQL provided."})
    if dbtype and dbtype.lower() not in ("postgres", "postgresql"):
        return JSONResponse(status_code=400, content={"sqlerror": f"Unsupported dbtype: {dbtype} (this server runs PostgreSQL)"})
    if dbname and dbname != PGDATABASE:
        return JSONResponse(status_code=400, content={"sqlerror": f"Unknown database: {dbname} (this server exposes {PGDATABASE})"})

    forbidden = re.findall(r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy)\b", sql, re.I)
    if forbidden:
        return JSONResponse(status_code=400, content={"sqlerror": "Only SELECT queries are allowed (found: %s)." % ", ".join(sorted({w.upper() for w in forbidden}))})

    # Prevent the query itself from ending in a subquery-terminator mess or
    # multiple statements: psycopg2 would run them all.
    if ";" in sql:
        return JSONResponse(status_code=400, content={"sqlerror": "Multiple SQL statements are not allowed."})

    # MultipleStatements protection: prefix check above catches CTEs with
    # writes only loosely; the read-only DB role is the real enforcement.
    # (This comment intentionally left in the code for maintainers.)
    try:
        columns, rows, truncated = run_query(sql)
    except psycopg2.Error as e:
        log.info("SQL error: %s", e.diag.message_primary)
        return {"sqlerror": e.diag.message_primary or str(e)}
    except Exception as e:
        return {"sqlerror": str(e)}

    resp = {
        # bootstrap-table 1.14.2 (called directly with this JSON by sqlbox.js)
        # needs column objects here; without a `field` key it auto-assigns
        # numeric field indexes, which makes arrays-of-arrays row data work and
        # keeps duplicate column names (e.g. joins on two `name` columns) intact.
        "columns": [{"title": name} for name in columns],
        "data": [[normalize_cell(c) for c in row] for row in rows],
        "correct_data": True,  # no answer => display-only box, treat as "ran fine"
        "escape": True,        # escape HTML in cells (SELECT '<img src=x>' etc.)
    }
    if truncated:
        resp["truncated"] = True
    if answer:
        try:
            resp["correct_data"] = resultset_matches(sql, answer)
        except Exception:
            resp["correct_data"] = False
    _ = origin  # CORS handled by middleware
    return resp
