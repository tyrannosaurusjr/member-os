#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.substack_export import build_import_rows, parse_substack_csv, write_members_csv


def main():
    parser = argparse.ArgumentParser(
        description='Transform a Substack subscribers CSV into the Member OS CSV import format.'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Path to the original Substack CSV export',
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Where to write the transformed CSV export',
    )
    args = parser.parse_args()

    source_rows = parse_substack_csv(Path(args.input))
    import_rows = build_import_rows(source_rows)
    output_path = write_members_csv(import_rows, Path(args.output))
    print(f'transformed_rows={len(import_rows)}')
    print(f'output_path={output_path}')


if __name__ == '__main__':
    main()
