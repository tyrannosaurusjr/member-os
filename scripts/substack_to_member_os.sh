#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

INPUT_PATH=""
OUTPUT_PATH="${OUTPUT_PATH:-${REPO_ROOT}/tmp/substack-subscribers-$(date +%Y%m%d-%H%M%S).csv}"
DO_IMPORT="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)
      INPUT_PATH="$2"
      shift 2
      ;;
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
Usage: scripts/substack_to_member_os.sh --input /path/to/substack.csv [--import] [--output /path/to/export.csv]

Transforms a Substack subscribers export into a Member OS CSV.

Options:
  --input PATH         Path to the original Substack CSV export
  --import             Also run `python manage.py import_external_profiles_csv ...`
  --output PATH        Where to save the transformed CSV export
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${INPUT_PATH}" ]]; then
  echo "Missing --input /path/to/substack.csv" >&2
  exit 1
fi

python3 "${REPO_ROOT}/scripts/transform_substack_subscribers.py" --input "${INPUT_PATH}" --output "${OUTPUT_PATH}"

if [[ "${DO_IMPORT}" == "1" ]]; then
  if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    echo "Missing ${REPO_ROOT}/.venv/bin/python. Create the virtualenv and install requirements first." >&2
    exit 1
  fi

  "${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/manage.py" import_external_profiles_csv "${OUTPUT_PATH}" --source-system substack
fi

echo "done"
