# Repository Guidelines

## Project Structure & Module Organization
RotaSeguraSP compares route exposure to recorded crime in São Paulo. The Python backend lives in `app/`: `routers/` defines FastAPI endpoints, `services/` handles routing, geocoding, and risk analysis, `models/` contains database models, and `core/` holds configuration, database access, and security. Schema migrations live in `alembic/versions/`. Backend tests are in `tests/`. The React/TypeScript frontend lives in `frontend/src/`, with components, services, types, and assets; public assets live in `frontend/public/`. Operational and ingestion scripts are in `scripts/`; environment-specific Compose files are in `deploy/`.

## Build, Test, and Development Commands
Use Python 3.13+, Poetry, Node.js 22+, PostgreSQL/PostGIS, and a configured Valhalla service.

- `poetry install --no-root`: install Python dependencies.
- `poetry run alembic upgrade head`: apply database migrations.
- `poetry run uvicorn app.main:app --reload`: run the API locally.
- In `frontend/`, run `npm ci` and `npm run dev` to start Vite.
- `poetry run pytest`: run backend tests.
- `poetry run ruff check app tests` and `poetry run ruff format --check app tests`: validate Python lint and formatting.
- In `frontend/`, run `npm run build` for TypeScript checks and production compilation, and `npm run lint` for ESLint.

## Coding Style & Naming Conventions
Use four-space indentation and snake_case for Python functions and modules; use PascalCase for classes. Follow Ruff's configured Python 3.13 rules. Match existing TypeScript style: two-space indentation, PascalCase components, and camelCase functions. Keep provider integrations in services and endpoint handling in routers.

## Testing Guidelines
Use pytest and pytest-asyncio; name files `test_*.py` and tests `test_*`. Mock external providers for API tests. For real spatial queries, set `TEST_DATABASE_URL` to a PostGIS database using `postgresql+asyncpg://...` and run `poetry run pytest -m postgis`; these tests skip without configuration. No coverage percentage is enforced. Add regression tests for changed behavior.

## Commit & Pull Request Guidelines
History uses short, informal Portuguese descriptions without a consistent prefix convention. Write concise, descriptive commits. PRs should explain behavior changes, list validation performed, link relevant issues, and include screenshots for UI changes. Document migrations and configuration changes.

## Security & Configuration
Start from `.env.example` and environment templates under `deploy/`. Keep credentials and route access tokens out of commits and logs. Treat exposure scores as experimental dataset comparisons, never as probabilities of victimization.
