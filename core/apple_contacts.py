import csv
import json
import subprocess
from pathlib import Path


FIELD_SEPARATOR = chr(31)
RECORD_SEPARATOR = chr(30)

EXPORT_HEADERS = [
    'source_record_id',
    'full_name',
    'first_name',
    'last_name',
    'primary_email',
    'secondary_email',
    'all_emails_json',
    'primary_phone',
    'secondary_phone',
    'all_phones_json',
    'company',
    'job_title',
    'notes',
]

APPLE_CONTACTS_EXPORT_SCRIPT = r'''
set fieldSeparator to ASCII character 31
set recordSeparator to ASCII character 30

on sanitizeText(valueText)
    if valueText is missing value then return ""
    set outputText to valueText as text
    set AppleScript's text item delimiters to return
    set outputText to (text items of outputText) as text
    set AppleScript's text item delimiters to linefeed
    set outputText to (text items of outputText) as text
    set AppleScript's text item delimiters to tab
    set outputText to (text items of outputText) as text
    set AppleScript's text item delimiters to " "
    set outputText to (text items of outputText) as text
    set AppleScript's text item delimiters to ""
    return outputText
end sanitizeText

on joinValues(valueList, joiner)
    if (count of valueList) is 0 then return ""
    set AppleScript's text item delimiters to joiner
    set outputText to valueList as text
    set AppleScript's text item delimiters to ""
    return outputText
end joinValues

set outputLines to {}
tell application "Contacts"
    repeat with personRecord in every person
        set contactId to ""
        set fullName to ""
        set firstName to ""
        set lastName to ""
        set organizationName to ""
        set jobTitle to ""
        set noteText to ""
        set emailValues to {}
        set phoneValues to {}

        try
            set contactId to my sanitizeText(id of personRecord)
        end try
        try
            set fullName to my sanitizeText(name of personRecord)
        end try
        try
            set firstName to my sanitizeText(first name of personRecord)
        end try
        try
            set lastName to my sanitizeText(last name of personRecord)
        end try
        try
            set organizationName to my sanitizeText(organization of personRecord)
        end try
        try
            set jobTitle to my sanitizeText(job title of personRecord)
        end try
        try
            set noteText to my sanitizeText(note of personRecord)
        end try

        try
            repeat with emailEntry in emails of personRecord
                copy my sanitizeText(value of emailEntry) to end of emailValues
            end repeat
        end try

        try
            repeat with phoneEntry in phones of personRecord
                copy my sanitizeText(value of phoneEntry) to end of phoneValues
            end repeat
        end try

        set primaryEmail to ""
        set secondaryEmail to ""
        if (count of emailValues) > 0 then set primaryEmail to item 1 of emailValues
        if (count of emailValues) > 1 then set secondaryEmail to item 2 of emailValues

        set primaryPhone to ""
        set secondaryPhone to ""
        if (count of phoneValues) > 0 then set primaryPhone to item 1 of phoneValues
        if (count of phoneValues) > 1 then set secondaryPhone to item 2 of phoneValues

        if fullName is "" then set fullName to my sanitizeText(my joinValues({firstName, lastName}, " "))

        set rowValues to {contactId, fullName, firstName, lastName, primaryEmail, secondaryEmail, my joinValues(emailValues, "|||"), primaryPhone, secondaryPhone, my joinValues(phoneValues, "|||"), organizationName, jobTitle, noteText}
        copy my joinValues(rowValues, fieldSeparator) to end of outputLines
    end repeat
end tell

set AppleScript's text item delimiters to recordSeparator
return outputLines as text
'''


def parse_contacts_export(raw_text: str):
    contacts = []
    for raw_record in raw_text.split(RECORD_SEPARATOR):
        if not raw_record.strip():
            continue
        parts = raw_record.split(FIELD_SEPARATOR)
        padded = parts + [''] * (len(EXPORT_HEADERS) - len(parts))
        row = dict(zip(EXPORT_HEADERS, padded))
        contacts.append(
            {
                'source_record_id': row['source_record_id'],
                'full_name': row['full_name'],
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'emails': [
                    value for value in row['all_emails_json'].split('|||') if value
                ],
                'phones': [
                    value for value in row['all_phones_json'].split('|||') if value
                ],
                'company': row['company'],
                'job_title': row['job_title'],
                'notes': row['notes'],
            }
        )
    return contacts


def build_import_rows(contacts):
    rows = []
    for contact in contacts:
        emails = [value for value in contact.get('emails', []) if value]
        phones = [value for value in contact.get('phones', []) if value]
        rows.append(
            {
                'source_record_id': contact.get('source_record_id', ''),
                'full_name': contact.get('full_name', ''),
                'first_name': contact.get('first_name', ''),
                'last_name': contact.get('last_name', ''),
                'primary_email': emails[0] if emails else '',
                'secondary_email': emails[1] if len(emails) > 1 else '',
                'all_emails_json': json.dumps(emails, ensure_ascii=False),
                'primary_phone': phones[0] if phones else '',
                'secondary_phone': phones[1] if len(phones) > 1 else '',
                'all_phones_json': json.dumps(phones, ensure_ascii=False),
                'company': contact.get('company', ''),
                'job_title': contact.get('job_title', ''),
                'notes': contact.get('notes', ''),
            }
        )
    return rows


def export_contacts():
    result = subprocess.run(
        ['osascript', '-l', 'AppleScript'],
        input=APPLE_CONTACTS_EXPORT_SCRIPT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or '').strip()
        if 'Not authorized' in detail or '(-1743)' in detail:
            raise RuntimeError(
                'Apple Contacts access was denied. Grant Terminal or osascript access to Contacts and try again.'
            )
        raise RuntimeError(f'Apple Contacts export failed: {detail}')
    return parse_contacts_export(result.stdout)


def write_contacts_csv(rows, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path

