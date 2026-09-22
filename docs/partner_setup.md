# CurricuPath Partner Setup

This guide starts CurricuPath on a new Windows computer from the shared project
folder. Run every command from the repository root, the folder containing
`compose.yaml` and `requirements.txt`.

## 1. Install prerequisites

Install:

- Python 3.12 (enable **Add Python to PATH** during installation).
- Docker Desktop with the WSL 2 backend.
- Git and VS Code are useful but are not required when receiving the folder
  directly.

PostgreSQL does not need to be installed separately. The Docker image in
`compose.yaml` contains PostgreSQL 16 and pgvector 0.8.6.

Confirm the required tools in PowerShell:

```powershell
py --version
docker --version
docker compose version
```

Start Docker Desktop and wait until it reports that the engine is running.

## 2. Prepare Python

```powershell
cd C:\path\to\curricupath
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The `Set-ExecutionPolicy` command affects only the current PowerShell process
and is needed only if Windows blocks virtual-environment activation.

## 3. Transfer the prototype configuration

For the current prototype, include the existing `.env` in the private folder
handoff so both developers use the same database settings, Gemini key, and
Hugging Face token. Do not add `.env` to Git, upload it to a public drive, paste
it into messages, or include it in a public ZIP. It is already excluded by
`.gitignore`.

If `.env` is missing from the private handoff, create it from the template:

```powershell
Copy-Item .env.example .env
```

For a simple local setup, make these PostgreSQL values agree in `.env`:

```dotenv
POSTGRES_DB=curricupath
POSTGRES_USER=curricupath
POSTGRES_PASSWORD=curricupath_dev
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://curricupath:curricupath_dev@127.0.0.1:5432/curricupath
CATALOGUE_BACKEND=postgresql
CATALOGUE_CSV_FALLBACK=true
```

The prototype configuration uses these fields:

```dotenv
GEMINI_API_KEY=replace-with-shared-prototype-key
HF_TOKEN=replace-with-shared-prototype-token
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIMENSION=384
SEMANTIC_SEARCH_ENABLED=true
```

Gemini is optional; without it, deterministic intent extraction is used.
Hugging Face is optional; without it, set `SEMANTIC_SEARCH_ENABLED=false` and
skip the embedding command below. Eligibility rules never depend on either API.
Because the prototype credentials have been shared, revoke them and issue fresh
credentials before deployment, publication, or wider testing.

## 4. Check the shared data

The handoff must include `data/processed/` and the reviewed source files under
`data/raw/`. The raw directory is intentionally ignored by Git, so a Git clone
alone will not contain those PDFs. Share only documents that the team is allowed
to redistribute.

Validate the CSVs and source trail before importing:

```powershell
python scripts/validate_database.py
```

Do not continue if validation reports errors. Missing files usually mean that a
referenced handbook or CBO was omitted from `data/raw/` during the handoff.

## 5. Start PostgreSQL and pgvector

```powershell
docker compose up -d database
docker compose ps
```

The `database` service should show `healthy`. Build the schema and import the
reviewed CSV catalogue:

```powershell
python scripts/build_database.py
```

Expected final output includes `Database ready`, a pgvector version, table
counts, module counts, and search-chunk counts.

If a Hugging Face token is configured, generate any missing vectors:

```powershell
python scripts/embed_catalogue.py
```

This hosted step is resumable. Re-running it does not regenerate unchanged
vectors. It sends searchable catalogue text to Hugging Face, not student
profiles or raw chat logs.

## 6. Run and verify CurricuPath

```powershell
python -m app.main
```

Open:

- Application: `http://127.0.0.1:8000/`
- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Run the automated checks in a second PowerShell window with the virtual
environment activated:

```powershell
python -m pytest -q
python scripts/validate_database.py
```

Stop the web server with `Ctrl+C`. Stop PostgreSQL without deleting its data:

```powershell
docker compose down
```

## 7. Share a temporary UI review link

The application address `http://127.0.0.1:8000/` works only on the computer
running the API. To let a teammate review the running prototype remotely, keep
the API terminal open and run this in a separate PowerShell window:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate
```

Copy the `https://...trycloudflare.com` URL printed by Cloudflare and share it
privately with the reviewer. This is a temporary, unauthenticated preview, not
a deployment. It expires when the tunnel command stops and the address changes
on the next run. Do not share it widely or use it for participant data.
`cloudflared` must be installed separately by the person creating the preview;
it is optional and not needed for the normal local setup.

## 8. Inspect the database

From PowerShell:

```powershell
docker compose exec database psql -U curricupath -d curricupath
```

Useful `psql` commands are:

```sql
\dt
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
SELECT COUNT(*) FROM modules;
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;
\q
```

In Docker Desktop, open **Containers**, expand the CurricuPath Compose project,
select the `database` container, and use **Logs** or **Exec**. The Exec terminal
can run the same `psql -U curricupath -d curricupath` command.

## 9. CSV-only fallback

If Docker cannot be started, CurricuPath can still demonstrate its deterministic
catalogue, eligibility, and controlled-vocabulary behavior. Change `.env` to:

```dotenv
CATALOGUE_BACKEND=csv
SEMANTIC_SEARCH_ENABLED=false
```

Then run:

```powershell
python -m app.main
```

CSV mode does not provide PostgreSQL sessions, recommendation logs, or pgvector
semantic matching.

## 10. Updating catalogue data

After an approved CSV or source-document change, run:

```powershell
python scripts/validate_database.py
python scripts/build_database.py
python scripts/embed_catalogue.py
python -m pytest -q
```

Skip `embed_catalogue.py` only when hosted embeddings are disabled. Never edit
PostgreSQL catalogue rows as the primary data source; the reviewed CSV files are
authoritative and the database is a reproducible runtime copy.

## Troubleshooting

- `127.0.0.1 refused to connect`: start the app with `python -m app.main` and
  keep that terminal open.
- Docker service is not healthy: open Docker Desktop, then inspect with
  `docker compose logs database`.
- Port 5432 is already in use: change `POSTGRES_PORT` and the port in
  `DATABASE_URL` to the same unused value, such as `5433`.
- Password authentication fails after changing `.env`: an existing Docker
  volume may still use the old password. On a disposable local database only,
  `docker compose down -v` removes that volume; then start and rebuild it. This
  deletes the container database but not the authoritative CSV files.
- `HF_TOKEN is not configured`: add the partner's token or disable semantic
  search and skip embedding generation.
- A token has been pasted into chat or committed: revoke it at the provider,
  issue a new token, and keep the replacement only in `.env`.
