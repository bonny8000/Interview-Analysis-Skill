import argparse
import csv
from collections import defaultdict
from pathlib import Path


def read_table(folder, name, prefix):
    path = folder / name
    if not path.read_bytes().startswith(b'\xef\xbb\xbf'):
        raise ValueError(f'{name}: UTF-8 BOM required')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or reader.fieldnames[:len(prefix)] != prefix:
            raise ValueError(f'{name}: unexpected core columns')
        rows = list(reader)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'{name}: inconsistent column count')
        if any('\n' in value or '\r' in value for value in row.values()):
            raise ValueError(f'{name}: embedded cell newline')
    return rows


def validate(folder, expected_participants=None):
    folder = Path(folder).resolve()
    raw = read_table(folder, 'RawData.csv', ['participant', 'sentence_id', 'sentence', 'Categories', 'Initial Code', 'Final Categories'])
    combined = read_table(folder, 'Combine Data.csv', ['participant', 'sentence_id', 'sentence', 'Initial Code', 'Sub Theme', 'Theme', 'Categories'])
    codebook = read_table(folder, 'Codebook.csv', ['Initial Code', 'Definition', 'Include', 'Exclude', 'Sub Theme', 'Theme', 'Categories', 'failure_mode'])
    summary = read_table(folder, 'Subtheme Summary.csv', ['Theme', 'Sub Theme', 'coding_rows', 'sentence_count', 'participant_count', 'participants'])
    indexed = {}
    for row in raw:
        key = row['participant'], row['sentence_id']
        if not all(key) or not row['sentence'] or key in indexed:
            raise ValueError(f'RawData: empty or duplicate unit {key}')
        if row.get('analysis_status') not in {'coded', 'needs_review', 'not_relevant'}:
            raise ValueError(f'RawData: invalid analysis_status {key}')
        if row['analysis_status'] != 'coded' and not row.get('exclusion_reason'):
            raise ValueError(f'RawData: missing exclusion reason {key}')
        if not row.get('source_turn') or not row.get('source_file'):
            raise ValueError(f'RawData: missing provenance {key}')
        source = (folder / row['source_file']).resolve()
        if not source.is_relative_to(folder) or not source.is_file():
            raise ValueError(f'RawData: source outside delivery or missing {key}')
        if source.suffix == '.md' and row['sentence'] not in source.read_text(encoding='utf-8'):
            raise ValueError(f'RawData: sentence absent from cleaned source {key}')
        indexed[key] = row
    codes = {}
    parents = {}
    for row in codebook:
        code = row['Initial Code']
        if not code or code in codes or any(not row[field] for field in ['Definition', 'Include', 'Exclude', 'Sub Theme', 'Theme', 'Categories']):
            raise ValueError(f'Codebook: incomplete or duplicate code {code}')
        if row['Sub Theme'] in parents and parents[row['Sub Theme']] != row['Theme']:
            raise ValueError(f'Codebook: conflicting subtheme parent {code}')
        parents[row['Sub Theme']] = row['Theme']
        codes[code] = row
    assignments = set()
    unit_assignments = defaultdict(list)
    groups = defaultdict(list)
    for row in combined:
        key = row['participant'], row['sentence_id']
        assignment = key + (row['Initial Code'],)
        original = indexed.get(key)
        if original is None or original['analysis_status'] != 'coded':
            raise ValueError(f'Combine Data: orphan or ineligible unit {key}')
        if row['sentence'] != original['sentence']:
            raise ValueError(f'Combine Data: sentence drift {key}')
        if original.get('speaker_status') not in {'verified', 'context_attributed'}:
            raise ValueError(f'Combine Data: unresolved speaker counted {key}')
        if assignment in assignments:
            raise ValueError(f'Combine Data: duplicate assignment {assignment}')
        code = codes.get(row['Initial Code'])
        if code is None or any(code[field] != row[field] for field in ['Sub Theme', 'Theme', 'Categories']):
            raise ValueError(f'Combine Data: hierarchy mismatch {assignment}')
        assignments.add(assignment)
        unit_assignments[key].append(row)
        groups[row['Theme'], row['Sub Theme']].append(row)
    for key, row in indexed.items():
        assigned = unit_assignments.get(key, [])
        if (row['analysis_status'] == 'coded') != bool(assigned):
            raise ValueError(f'RawData: coded status/assignment mismatch {key}')
        if assigned:
            for raw_field, combined_field in [('Initial Code', 'Initial Code'), ('Categories', 'Categories'), ('Final Categories', 'Theme')]:
                actual = set(row[raw_field].split('; '))
                expected = {item[combined_field] for item in assigned}
                if actual != expected:
                    raise ValueError(f'RawData: aggregated labels drift {key} {raw_field}')
    summary_index = {(row['Theme'], row['Sub Theme']): row for row in summary}
    if len(summary_index) != len(summary) or set(summary_index) != set(groups):
        raise ValueError('Summary: missing, extra, or duplicate group')
    for group, rows in groups.items():
        participant_set = {row['participant'] for row in rows}
        counts = len(rows), len({(row['participant'], row['sentence_id']) for row in rows}), len(participant_set)
        actual = summary_index[group]
        if tuple(int(actual[field]) for field in ['coding_rows', 'sentence_count', 'participant_count']) != counts:
            raise ValueError(f'Summary: counts mismatch {group}')
        if set(actual['participants'].split('; ')) != participant_set:
            raise ValueError(f'Summary: participant list mismatch {group}')
    participants = {row['participant'] for row in combined}
    if expected_participants is not None:
        allowed = set(expected_participants)
        if participants != allowed or {row['participant'] for row in raw} - allowed:
            raise ValueError('Participant allowlist mismatch')
    return dict(raw_units=len(raw), coded_units=len(unit_assignments), coding_rows=len(combined), participants=len(participants), subthemes=len(groups))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate sentence-level interview analysis relationships and counts.')
    parser.add_argument('folder')
    parser.add_argument('--expected-participants', nargs='+')
    arguments = parser.parse_args()
    print(validate(arguments.folder, arguments.expected_participants))
