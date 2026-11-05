# Local database migrations

Run from `apps/backend` after installing its dependencies and starting PostgreSQL:

```sh
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

Review every migration before applying it. The initial revision creates the mapped SQLAlchemy metadata for a clean local database; follow-up revisions should use Alembic autogeneration and be reviewed. API startup does not create or alter tables.