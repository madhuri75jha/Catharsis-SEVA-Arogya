#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
KEEP_MIGRATIONS="false"
CONFIRMED="false"
SKIP_COGNITO="false"
ALLOW_LOCAL_DB="false"
API_BASE_URL="${SYSTEM_RESET_API_URL:-}"
API_TOKEN="${SYSTEM_RESET_TOKEN:-}"
API_ONLY="false"

usage() {
  cat <<'EOF'
Usage: ./scripts/reset_database.sh --yes [--keep-migrations] [--skip-cognito] [--allow-local-db] [--api-base-url URL] [--api-token TOKEN] [--api-only] [--env-file path]

Dangerous operation:
- Truncates all tables in the public schema
- Removes all data (consultations, transcriptions, prescriptions, hospitals, doctors, user_roles, etc.)
- Resets sequences/IDs
- Disables and deletes all users in the configured Cognito User Pool

Options:
  --yes               Required confirmation flag
  --keep-migrations   Keep schema_migrations rows
  --skip-cognito      Skip Cognito user disable/delete step
  --allow-local-db    Allow localhost/127.0.0.1 DB targets (disabled by default)
  --api-base-url URL  Base URL of deployed app (for internal reset endpoint)
  --api-token TOKEN   Token matching SYSTEM_RESET_TOKEN on deployed app
  --api-only          Require remote API reset; do not fall back to local DB reset
  --env-file PATH     Load environment variables from a specific file (default: .env)
  -h, --help          Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      CONFIRMED="true"
      shift
      ;;
    --keep-migrations)
      KEEP_MIGRATIONS="true"
      shift
      ;;
    --skip-cognito)
      SKIP_COGNITO="true"
      shift
      ;;
    --allow-local-db)
      ALLOW_LOCAL_DB="true"
      shift
      ;;
    --api-base-url)
      if [[ $# -lt 2 ]]; then
        echo "Error: --api-base-url requires a URL"
        exit 1
      fi
      API_BASE_URL="$2"
      shift 2
      ;;
    --api-token)
      if [[ $# -lt 2 ]]; then
        echo "Error: --api-token requires a token value"
        exit 1
      fi
      API_TOKEN="$2"
      shift 2
      ;;
    --api-only)
      API_ONLY="true"
      shift
      ;;
    --env-file)
      if [[ $# -lt 2 ]]; then
        echo "Error: --env-file requires a path"
        exit 1
      fi
      ENV_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: Unknown argument '$1'"
      usage
      exit 1
      ;;
  esac
done

if [[ "$CONFIRMED" != "true" ]]; then
  echo "Error: Missing required --yes flag"
  usage
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "Warning: Env file not found at '$ENV_FILE'. Using current environment only."
fi

if [[ -z "$API_BASE_URL" && -n "${SYSTEM_RESET_API_URL:-}" ]]; then
  API_BASE_URL="$SYSTEM_RESET_API_URL"
fi
if [[ -z "$API_TOKEN" && -n "${SYSTEM_RESET_TOKEN:-}" ]]; then
  API_TOKEN="$SYSTEM_RESET_TOKEN"
fi

PYTHON_CMD="python3"
if ! command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python"
fi

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  echo "Error: Python is not installed"
  exit 1
fi

echo "Starting database reset..."
echo "  Env file: $ENV_FILE"
echo "  Keep schema_migrations: $KEEP_MIGRATIONS"
echo "  Skip Cognito purge: $SKIP_COGNITO"
echo "  Allow local DB target: $ALLOW_LOCAL_DB"
if [[ -n "$API_BASE_URL" ]]; then
  echo "  Remote API base URL: $API_BASE_URL"
fi

call_remote_reset_api() {
  if [[ -z "$API_BASE_URL" ]]; then
    return 1
  fi

  if [[ -z "$API_TOKEN" ]]; then
    echo "Remote API URL provided but token is missing. Set --api-token or SYSTEM_RESET_TOKEN."
    return 1
  fi

  echo "Attempting remote reset via internal API..."
  RESET_API_BASE_URL="$API_BASE_URL" \
  RESET_API_TOKEN="$API_TOKEN" \
  RESET_KEEP_MIGRATIONS="$KEEP_MIGRATIONS" \
  RESET_SKIP_COGNITO="$SKIP_COGNITO" \
  "$PYTHON_CMD" - <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

base_url = os.environ["RESET_API_BASE_URL"].rstrip("/")
token = os.environ["RESET_API_TOKEN"]
keep_migrations = os.environ.get("RESET_KEEP_MIGRATIONS", "false").lower() == "true"
skip_cognito = os.environ.get("RESET_SKIP_COGNITO", "false").lower() == "true"

url = f"{base_url}/api/v1/internal/system-reset"
payload = {
    "confirm": "RESET_ALL_DATA",
    "reset_db": True,
    "reset_cognito": not skip_cognito,
    "keep_migrations": keep_migrations,
}

request = urllib.request.Request(
    url=url,
    method="POST",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "X-System-Reset-Token": token,
    },
)

try:
    with urllib.request.urlopen(request, timeout=180) as response:
        body = response.read().decode("utf-8", errors="replace")
        print(body)
        if 200 <= response.status < 300:
            try:
                data = json.loads(body)
                if data.get("success") is True:
                    sys.exit(0)
            except Exception:
                pass
        sys.exit(1)
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    print(f"HTTP {exc.code}: {body}")
    sys.exit(1)
except Exception as exc:
    print(f"Remote reset call failed: {exc}")
    sys.exit(1)
PY
}

if call_remote_reset_api; then
  echo "Remote reset completed successfully."
  exit 0
fi

if [[ "$API_ONLY" == "true" ]]; then
  echo "Error: --api-only set and remote reset failed."
  exit 1
fi

echo "Remote reset unavailable or failed. Falling back to direct local execution."

RESET_KEEP_MIGRATIONS="$KEEP_MIGRATIONS" RESET_ALLOW_LOCAL_DB="$ALLOW_LOCAL_DB" "$PYTHON_CMD" - <<'PY'
import json
import os
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql


def is_local_hostname(host: str) -> bool:
    normalized = (host or "").strip().lower()
    return normalized in {"localhost", "127.0.0.1", "::1"}


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_secret_db_credentials():
    secret_name = (os.getenv("DB_SECRET_NAME", "") or "").strip()
    if not secret_name:
        return None

    region = (os.getenv("AWS_REGION", "") or "").strip()
    if not region:
        raise RuntimeError("DB_SECRET_NAME is set but AWS_REGION is missing.")

    try:
        import boto3
    except Exception as exc:
        raise RuntimeError(
            "DB_SECRET_NAME is set but boto3 is unavailable in this Python environment."
        ) from exc

    client = boto3.client("secretsmanager", region_name=region)
    resp = client.get_secret_value(SecretId=secret_name)
    secret_string = resp.get("SecretString")
    if not secret_string:
        raise RuntimeError(f"Secret '{secret_name}' did not contain SecretString.")

    try:
        secret = json.loads(secret_string)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Secret '{secret_name}' is not valid JSON.") from exc

    if not isinstance(secret, dict):
        raise RuntimeError(f"Secret '{secret_name}' must be a JSON object.")

    host = (secret.get("host") or "").strip()
    port = str(secret.get("port") or "5432").strip()
    dbname = (secret.get("dbname") or secret.get("database") or "").strip()
    user = (secret.get("username") or secret.get("user") or "").strip()
    password = (secret.get("password") or "").strip()

    if not (host and dbname and user and password):
        raise RuntimeError(
            f"Secret '{secret_name}' is missing one of: host, dbname/database, username/user, password."
        )

    return {"host": host, "port": port, "dbname": dbname, "user": user, "password": password}


def build_dsn() -> str:
    allow_local = parse_bool(os.getenv("RESET_ALLOW_LOCAL_DB", "false"))

    env_host = os.getenv("DB_HOST", "").strip()
    env_port = os.getenv("DB_PORT", "5432").strip()
    env_dbname = os.getenv("DB_NAME", "").strip()
    env_user = os.getenv("DB_USERNAME", "").strip() or os.getenv("DB_USER", "").strip()
    env_password = os.getenv("DB_PASSWORD", "").strip()

    if env_host and env_dbname and env_user and env_password:
        if is_local_hostname(env_host) and not allow_local:
            raise RuntimeError(
                f"Refusing to reset local DB host '{env_host}'. "
                "Set RDS DB_* values or use DB_SECRET_NAME. "
                "If this is intentional, pass --allow-local-db."
            )
        return f"host={env_host} port={env_port} dbname={env_dbname} user={env_user} password={env_password}"

    secret_creds = get_secret_db_credentials()
    if secret_creds:
        if is_local_hostname(secret_creds["host"]) and not allow_local:
            raise RuntimeError(
                f"Refusing to reset local DB host '{secret_creds['host']}' from DB secret. "
                "If this is intentional, pass --allow-local-db."
            )
        return (
            f"host={secret_creds['host']} port={secret_creds['port']} "
            f"dbname={secret_creds['dbname']} user={secret_creds['user']} password={secret_creds['password']}"
        )

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        parsed = urlparse(database_url)
        host = (parsed.hostname or "").strip()
        if is_local_hostname(host) and not allow_local:
            raise RuntimeError(
                "DATABASE_URL points to localhost. This script is configured to reset RDS, "
                "not local DB. Set DB_SECRET_NAME or RDS DB_* env vars."
            )
        return database_url

    raise RuntimeError(
        "Missing DB config. Set RDS DB_* env vars or DB_SECRET_NAME. "
        "DATABASE_URL is only a final fallback."
    )


def main() -> int:
    keep_migrations = os.getenv("RESET_KEEP_MIGRATIONS", "false").lower() == "true"

    try:
        dsn = build_dsn()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
            tables = [row[0] for row in cur.fetchall()]

            if keep_migrations:
                tables = [t for t in tables if t != "schema_migrations"]

            if not tables:
                print("No tables found to reset.")
                conn.rollback()
                return 0

            truncate_stmt = sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                sql.SQL(", ").join(sql.Identifier("public", table) for table in tables)
            )
            cur.execute(truncate_stmt)

        conn.commit()

        print("Database reset complete.")
        print(f"Truncated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        return 0

    except Exception as exc:
        print(f"ERROR: Database reset failed: {exc}")
        if conn:
            conn.rollback()
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
PY

purge_cognito_users() {
  if [[ "$SKIP_COGNITO" == "true" ]]; then
    echo "Skipping Cognito user purge (--skip-cognito set)."
    return 0
  fi

  if ! command -v aws >/dev/null 2>&1; then
    echo "Error: aws CLI is required for Cognito user purge but was not found."
    exit 1
  fi

  local user_pool_id="${AWS_COGNITO_USER_POOL_ID:-${COGNITO_USER_POOL_ID:-}}"
  local region="${AWS_REGION:-${COGNITO_REGION:-}}"

  if [[ -z "$user_pool_id" ]]; then
    echo "Error: Missing Cognito user pool ID. Set AWS_COGNITO_USER_POOL_ID (or COGNITO_USER_POOL_ID)."
    exit 1
  fi

  if [[ -z "$region" ]]; then
    echo "Error: Missing AWS region. Set AWS_REGION (or COGNITO_REGION)."
    exit 1
  fi

  echo "Purging Cognito users..."
  echo "  User Pool: $user_pool_id"
  echo "  Region: $region"

  local raw_usernames
  raw_usernames="$(aws cognito-idp list-users \
    --user-pool-id "$user_pool_id" \
    --region "$region" \
    --query 'Users[].Username' \
    --output text)"

  local usernames=()
  if [[ -n "${raw_usernames//[[:space:]]/}" && "$raw_usernames" != "None" ]]; then
    while IFS= read -r username; do
      if [[ -n "$username" ]]; then
        usernames+=("$username")
      fi
    done < <(printf '%s\n' "$raw_usernames" | tr '\t' '\n')
  fi

  if [[ ${#usernames[@]} -eq 0 ]]; then
    echo "No Cognito users found in user pool."
    return 0
  fi

  local deleted_count=0
  for username in "${usernames[@]}"; do
    aws cognito-idp admin-disable-user \
      --user-pool-id "$user_pool_id" \
      --username "$username" \
      --region "$region" >/dev/null 2>&1 || true

    aws cognito-idp admin-delete-user \
      --user-pool-id "$user_pool_id" \
      --username "$username" \
      --region "$region" >/dev/null

    deleted_count=$((deleted_count + 1))
    echo "  - Deleted Cognito user: $username"
  done

  echo "Cognito purge complete. Deleted $deleted_count user(s)."
}

purge_cognito_users
