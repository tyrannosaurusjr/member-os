#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OUTPUT_PATH="${OUTPUT_PATH:-${REPO_ROOT}/tmp/apple-contacts-$(date +%Y%m%d-%H%M%S).csv}"
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
Usage: scripts/apple_contacts_to_member_os.sh [--import] [--output /path/to/export.csv]

Exports every contact from Apple Contacts into a Member OS CSV.

Options:
  --import              Also run `python manage.py import_external_profiles_csv ...`
  --output PATH         Where to save the CSV export
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

python3 "${REPO_ROOT}/scripts/export_apple_contacts.py" --output "${OUTPUT_PATH}"

if [[ "${DO_IMPORT}" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    echo "Missing ${REPO_ROOT}/.venv/bin/python. Create the virtualenv and install requirements first." >&2
    exit 1
  fi

  "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/manage.py" import_external_profiles_csv "${OUTPUT_PATH}" --source-system apple_contacts
fi

echo "done"
