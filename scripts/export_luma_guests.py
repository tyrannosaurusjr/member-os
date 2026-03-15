#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.luma_export import export_guests, write_guests_csv


def main():
    parser = argparse.ArgumentParser(
        description='Export Luma guests into the Member OS CSV import format.'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Where to write the CSV export',
    )
    parser.add_argument(
        '--api-key',
        default=os.environ.get('LUMA_API_KEY', ''),
        help='Luma API key. Defaults to LUMA_API_KEY.',
    )
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit('Missing Luma API key. Pass --api-key or set LUMA_API_KEY.')

    rows = export_guests(args.api_key)
    output_path = write_guests_csv(rows, Path(args.output))
    print(f'exported_people={len(rows)}')
    print(f'output_path={output_path}')


if __name__ == '__main__':
    main()
