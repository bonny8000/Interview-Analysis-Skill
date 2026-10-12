import argparse
import csv
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile


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


def validate(folder, expected_participants=None, require_full_review=False):
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
        if source.suffix in {'.md', '.txt'}:
            text = source.read_text(encoding='utf-8')
            sentence_type = row.get('sentence_type', 'verbatim')
            if sentence_type not in {'verbatim', 'contextual_reconstruction_not_verbatim'}:
                raise ValueError(f'RawData: invalid sentence_type {key}')
            if sentence_type == 'contextual_reconstruction_not_verbatim':
                if not all(row.get(field) for field in ['raw_sentence', 'context_turns', 'context_note', 'evidence_type']):
                    raise ValueError(f'RawData: reconstruction without context/provenance {key}')
                fragments = row['raw_sentence'].split(' ⟪…⟫ ')
                if any(not fragment or fragment not in text for fragment in fragments):
                    raise ValueError(f'RawData: raw fragment absent from source {key}')
            elif row['sentence'] not in text:
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
        for field in ['sentence_type', 'raw_sentence', 'source_turn', 'context_turns', 'Scenario']:
            if field in row and row[field] != original.get(field):
                raise ValueError(f'Combine Data: provenance/context drift {key} {field}')
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
    result = dict(raw_units=len(raw), coded_units=len(unit_assignments), coding_rows=len(combined), participants=len(participants), subthemes=len(groups))
    if require_full_review:
        coverage = read_table(folder, 'Source Coverage.csv', ['participant', 'source_turn'])
        review = read_table(folder, 'Review Queue.csv', ['participant', 'review_id'])
        manifest = read_table(folder / 'audit', 'source-manifest.csv', ['participant', 'filename', 'sha256', 'source_segments'])
        expected = {row['participant']: int(row['source_segments']) for row in manifest}
        if len(expected) != len(manifest) or set(expected) != participants:
            raise ValueError('Coverage: manifest/participant mismatch')
        seen = set()
        review_ids = {row['review_id'] for row in review}
        if len(review_ids) != len(review):
            raise ValueError('Review Queue: duplicate review_id')
        for row in review:
            if row['participant'] not in participants or not all(row.get(field) for field in ['source_turn', 'reason', 'action']):
                raise ValueError('Review Queue: missing specific provenance/reason/action')
        actual = defaultdict(int)
        for row in coverage:
            key = row['participant'], row['source_turn']
            if key in seen or row['participant'] not in expected:
                raise ValueError(f'Coverage: duplicate or unexpected source {key}')
            if not row.get('review_decision') or not row.get('reason') or not row.get('source_text'):
                raise ValueError(f'Coverage: missing disposition, reason, or source text {key}')
            for unit in filter(None, row.get('linked_units', '').split('; ')):
                if (row['participant'], unit) not in indexed:
                    raise ValueError(f'Coverage: unknown linked unit {key}')
            for flag in filter(None, row.get('review_flags', '').split('; ')):
                if flag not in review_ids:
                    raise ValueError(f'Coverage: unknown review flag {key}')
            seen.add(key)
            actual[row['participant']] += 1
        if dict(actual) != expected:
            raise ValueError('Coverage: source counts do not match manifest')
        result.update(source_segments=len(coverage), review_ranges=len(review))
    return result


def validate_xlsx(path):
    namespace = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    with ZipFile(path) as archive:
        table_paths = [name for name in archive.namelist() if re.fullmatch(r'xl/tables/table\d+\.xml', name)]
        sheet_paths = [name for name in archive.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name)]
        if not table_paths:
            raise ValueError('XLSX: no native filter tables')
        for name in table_paths:
            table = ET.fromstring(archive.read(name))
            auto_filter = table.find(namespace + 'autoFilter')
            if auto_filter is None or auto_filter.get('ref') != table.get('ref'):
                raise ValueError(f'XLSX: missing or partial table filter {name}')
            match = re.fullmatch(r'([A-Z]+)\d+:([A-Z]+)\d+', table.get('ref', ''))
            if not match:
                raise ValueError(f'XLSX: invalid table range {name}')
            def column_number(letters):
                result = 0
                for character in letters:
                    result = result * 26 + ord(character) - 64
                return result
            columns = table.find(namespace + 'tableColumns')
            expected = column_number(match[2]) - column_number(match[1]) + 1
            if columns is None or len(columns) != expected:
                raise ValueError(f'XLSX: table header width mismatch {name}')
            for column in auto_filter.findall(namespace + 'filterColumn'):
                if column.get('hiddenButton') in {'1', 'true'} or column.get('showButton') in {'0', 'false'}:
                    raise ValueError(f'XLSX: hidden filter button {name}')
        for name in sheet_paths:
            sheet = ET.fromstring(archive.read(name))
            if sheet.find(namespace + 'sheetData') is not None and sheet.find(namespace + 'tableParts') is None:
                raise ValueError(f'XLSX: worksheet has no native filter table {name}')
    return dict(native_filter_tables=len(table_paths), worksheets=len(sheet_paths))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate sentence-level interview analysis relationships and counts.')
    parser.add_argument('folder')
    parser.add_argument('--expected-participants', nargs='+')
    parser.add_argument('--require-full-review', action='store_true')
    parser.add_argument('--xlsx', type=Path)
    arguments = parser.parse_args()
    print(validate(arguments.folder, arguments.expected_participants, arguments.require_full_review))
    if arguments.xlsx:
        print(validate_xlsx(arguments.xlsx))
