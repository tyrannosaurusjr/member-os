#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_PATH="${OUTPUT_PATH:-${REPO_ROOT}/tmp/stripe-customers-$(date +%Y%m%d-%H%M%S).csv}"
DO_IMPORT="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --import)
      DO_IMPORT="1"
      shift
      ;;
    --output)
      OUTPUT_PATH="$2"
      shift 2
      ;;
    --help|-h)
      cat <<'EOF'
Usage: scripts/stripe_to_member_os.sh [--import] [--output /path/to/export.csv]

Exports Stripe customers and subscriptions into a Member OS CSV.

Options:
  --import              Also run `python manage.py import_external_profiles_csv ...`
  --output PATH         Where to save the CSV export

Environment:
  STRIPE_API_KEY        Required Stripe secret key used for export
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${STRIPE_API_KEY:-}" ]]; then
  echo "Missing STRIPE_API_KEY. Export your Stripe secret key first." >&2
  exit 1
fi

python3 "${REPO_ROOT}/scripts/export_stripe_customers.py" --output "${OUTPUT_PATH}" --api-key "${STRIPE_API_KEY}"

if [[ "${DO_IMPORT}" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    echo "Missing ${REPO_ROOT}/.venv/bin/python. Create the virtualenv and install requirements first." >&2
    exit 1
  fi

  "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/manage.py" import_external_profiles_csv "${OUTPUT_PATH}" --source-system stripe
fi

echo "done"
