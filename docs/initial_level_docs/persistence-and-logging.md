# PostgreSQL Verification and Daily Logs

## Storage

All implemented project mutations commit business records to PostgreSQL: projects,
contracts, status changes, purchase orders and lines, vendor payments, project inventory
links, timecards, billing applications, plan metadata, and plan-based value history.
Uploaded PDF/image/DOCX bytes are stored separately in `data/uploads`; metadata and
their project links are in PostgreSQL. Back up the database and uploads together.
The standalone HTML prototype is not the React application's storage.

## Verify a Save

1. Save a transaction and note its project ID and record number/ID from the API response.
2. Run the verifier from `apps/backend` using the configured Python interpreter:

   ```sh
   python verify_persistence.py
   python verify_persistence.py --project-id PROJECT_UUID
   ```

   On this Mac the verified interpreter is `/opt/homebrew/bin/python3.12`.
   The script queries PostgreSQL in a read-only transaction and prints database identity
   and table counts. Compare project-specific counts before and after a new save.
   Edits do not increase counts; verify their values using SQL instead.

3. In pgAdmin/psql connected to `vridhi_dev`, query the saved record directly:

   ```sql
   SELECT id, name, status, baseline_budget FROM projects ORDER BY created_at DESC;
   SELECT id, project_id, number, order_date FROM purchase_orders ORDER BY created_at DESC;
   SELECT id, purchase_order_id, amount, payment_date FROM purchase_order_payments;
   SELECT id, project_id, employee_name, work_date, regular_hours FROM timecards;
   SELECT id, project_id, application_number, amount FROM billing_entries;
   SELECT id, project_id, filename, comment, uploaded_at FROM project_documents;
   SELECT project_id, previous_value, new_value, changed_at FROM project_value_history;
   ```

   Add `WHERE id = 'RECORD_UUID'` or `WHERE project_id = 'PROJECT_UUID'` as appropriate.
   Reloading or signing in again is a useful UI check, but direct SQL is stronger proof.

## Daily Logs

Logs are local files, grouped by **UTC date** under `data/logs/YYYY-MM-DD/`:

- `backend.jsonl`: startup/shutdown, request ID, method/path, response status and duration,
  failed-request exception category, and `database_commit` after a successful commit.
- `frontend.jsonl`: API status/duration/request ID, network errors, JavaScript errors,
  rejected promises, and console warning/error categories. Sent in batches every 3 seconds.
- `backend-server.log`: backend stdout/stderr when started through the launcher or wrapper.
- `frontend-server.log`: Vite stdout/stderr when started through the launcher or wrapper.

Both launchers now use the wrapper. Already-running servers must be restarted through
it to capture their process output. Manual startup from the construction folder:

```sh
node scripts/log-process.mjs backend-server /opt/homebrew/bin/uvicorn app.main:app --app-dir apps/backend --host 127.0.0.1 --port 8000
node scripts/log-process.mjs frontend-server npm --prefix apps/frontend run dev -- --host 127.0.0.1 --port 5174 --strictPort
```

Application files rotate by date on each write, including across midnight. The backend
log directory can be overridden with `LOG_DIRECTORY`. Server output uses `data/logs`.
Logs are excluded from Git. There is no automatic deletion policy yet; archive/remove
older date folders according to your retention needs.

Passwords, cookies, CSRF tokens, request bodies, document contents, and browser console
arguments are intentionally excluded from structured application logs. Browser errors
record categories, not potentially sensitive message text. Browser logging is best-effort:
events while offline or before CSRF bootstrap can be lost, and logging is not proof of a
database save. Raw server output may contain library exception messages; restrict access.
PostgreSQL server logs are separate and controlled by PostgreSQL/Docker, not this app.

## Coverage Limit

This verifies the implemented API workflows, not every future ERP feature. For example,
the inventory register is driven by procurement links; a dedicated stock receipt/issue
workflow is not yet exposed in this UI. Logs cannot recreate missing transactions.