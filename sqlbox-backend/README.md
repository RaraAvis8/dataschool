# Local SQLBox Backend

A drop-in replacement for Chartio's original SQLBox server (`sqlbox.herokuapp.com`, dead long time ago). Serves the interactive "Run SQL" boxes on the Learn SQL tutorial pages.

## What it runs

- **PostgreSQL 16** with the **Chinook** sample dataset (11 tables, canonical row counts), loaded as database `herokuchinook` to match the original.
- **FastAPI shim** on port **8084** that implements the contract expected by `dataschool/assets/sqlbox/sqlbox.js`:
  - `POST /` with form fields `sql`, `dbtype`, `dbname`, `answer`
  - Returns `{"sqlerror": "..."}` on bad SQL, otherwise `{"columns": [...], "rows": [[...]], "correct_data": bool}`
  - `correct_data` is computed by comparing the user's resultset to the answer query's resultset (order- and column-order-insensitive, matching tutorial expectations like `SELECT title, id` ≡ `SELECT id, title`)
  - CORS allows `http://localhost:4000` with credentials (the site JS uses `withCredentials`)
- API connects as a **read-only Postgres role** (`readonly`) and additionally rejects non-SELECT statements and multi-statement input in app code.

## Schema adaptation

The tutorials use lowercase plural table names and `id` PKs (`albums.id`, `tracks.album_id`...), so `db/init/02-rename-to-snakecase.sql` renames Chinook's `album`→`albums`, `album_id`→`id`, etc. after the vanilla dump loads. FK columns keep descriptive names (`tracks.album_id`), matching all tutorial queries.

## Run it

```bash
cd sqlbox-backend
docker compose up -d --build      # start (db + api)
docker compose logs -f api        # watch logs
docker compose down               # stop
docker compose down -v            # stop AND wipe the loaded data
```

The Jekyll site's `_config.yml` is already set to `sqlboxurl: "http://localhost:8084"`. If you change that config, restart Jekyll (`_config.yml` is not hot-reloaded):

```bash
cd dataschool
bundle exec jekyll serve --watch
```

Then open http://localhost:4000/learn-sql/select/ and click **Run SQL**.

## Inspect the database directly

```bash
docker compose exec db psql -U postgres -d herokuchinook
# or from the host:
psql -h localhost -p 5433 -U postgres -d herokuchinook   # password: postgres
# read-only role used by the API:
psql -h localhost -p 5433 -U readonly -d herokuchinook   # password: readonly
```

## Smoke test

```bash
curl -s -X POST http://localhost:8084/ \
  -d "sql=SELECT 42;" -d "dbtype=PostgreSQL" -d "dbname=herokuchinook" -d "answer=SELECT 42;"
# {"columns":[{"title":"?column?"}],"data":[[42]],"correct_data":true,"escape":true}
```

## Notes

- `db/init/01-chinook.sql` is the upstream [lerocha/chinook-database](https://github.com/lerocha/chinook-database) `Chinook_PostgreSql_SerialPKs.sql` with its `CREATE DATABASE`/`\connect` lines commented out (the postgres docker entrypoint runs init scripts inside `POSTGRES_DB`).
- Init scripts only run on **first** volume creation; use `docker compose down -v` to re-initialize.
- Max 500 rows per query and 10s statement timeout (configurable via env in `compose.yaml`).
- The original backend also had sakila `films`/`actors` tables (referenced only in sqlbox.js editor autocomplete). They were never used by any tutorial, so they are not loaded here.
