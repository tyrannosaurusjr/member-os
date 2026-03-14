#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.apple_contacts import build_import_rows, export_contacts, write_contacts_csv


def main():
    parser = argparse.ArgumentParser(
        description='Export Apple Contacts into the Member OS CSV import format.'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Where to write the CSV export',
    )
    args = parser.parse_args()

    contacts = export_contacts()
    rows = build_import_rows(contacts)
    output_path = write_contacts_csv(rows, Path(args.output))
    print(f'exported_contacts={len(rows)}')
    print(f'output_path={output_path}')


if __name__ == '__main__':
    main()
