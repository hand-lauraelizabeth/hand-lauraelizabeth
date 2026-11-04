"""Build browser-local Role Evidence Studio data from public source files.

Download input files from O*NET 31.0, Census 2020 ZCTA-to-county,
and BLS May 2025 OEWS area definitions and metropolitan wage tables.
"""

import csv
import base64
import gzip
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

import openpyxl


OUT = Path('data')
OUT.mkdir(exist_ok=True)
STOP = set('about across additional analysis based business candidate company demonstrated duties education employment excellent experience first good help high including internal job knowledge leadership manage management manager multiple organization people performance professional program project provide related report required requirements responsibility review role school services skills strong support system team tools use using work working years coordinate develop ensure activities perform information procedures prepare staff assigned other process maintain plans specific operations principles methods according following including'.split())


def words(text):
    return [w.rstrip('.') for w in re.findall(r'[a-z][a-z0-9+#.]{1,}', text.lower()) if (len(w) >= 3 or w in {'ai', 'hr', 'ux', 'it'}) and w.rstrip('.') not in STOP]


def write(name, data):
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()
    (OUT / f'{name}.json').write_bytes(payload)
    compressed = gzip.compress(payload, compresslevel=9, mtime=0)
    (OUT / f'{name}.b64').write_bytes(base64.b64encode(compressed))


def occupations():
    with ZipFile('onet31.zip') as bundle:
        def rows(filename):
            name = next(n for n in bundle.namelist() if n.endswith('/' + filename))
            with bundle.open(name) as binary, io.TextIOWrapper(binary, encoding='utf-8-sig') as text:
                yield from csv.DictReader(text, delimiter='\t')

        aliases = defaultdict(list)
        for row in rows('Job Titles.txt'):
            title = row['Job Title'].strip()
            if len(title) >= 5:
                aliases[row['O*NET-SOC Code']].append(title)
        tasks = defaultdict(Counter)
        for row in rows('Task Statements.txt'):
            if row['Task Type'] == 'Core':
                tasks[row['O*NET-SOC Code']].update(words(row['Task']))
        catalog = list(rows('Occupation Data.txt'))
        by_role = {}
        for row in catalog:
            code = row['O*NET-SOC Code']
            counts = Counter(words(row['Description']) * 3 + words(row['Title']) * 6)
            counts.update(tasks[code])
            counts.update(words(' '.join(aliases[code])))
            by_role[code] = counts
        df = Counter(term for counts in by_role.values() for term in counts)
        data = []
        for row in catalog:
            code, title = row['O*NET-SOC Code'], row['Title']
            counts = by_role[code]
            ranked = sorted(counts, key=lambda w: (-(counts[w] ** 0.65) / (df[w] ** 0.28), w))
            chosen = list(dict.fromkeys(words(title) + ranked[:28]))
            ordered_aliases = sorted(set(aliases[code]), key=lambda a: (-len(set(words(a)) & set(words(title))), len(a), a))
            data.append([code, title, ordered_aliases[:10], chosen])
    used = {word for row in data for word in row[3]}
    weights = {word: round(1 + 3 / (1 + df[word] ** 0.38), 2) for word in sorted(used)}
    write('occupations', {'roles': data, 'weights': weights})
    print('Occupations:', len(data), 'indexed words:', len(used), flush=True)


def wages_and_geography():
    mapping = defaultdict(set)
    names = {}
    definitions = openpyxl.load_workbook('definitions.xlsx', read_only=True, data_only=True)
    for state, _, _, code, name, county, _ in list(definitions.active.values)[1:]:
        if county and code and state:
            mapping[state.zfill(2) + county.zfill(3)].add(code)
            names[code] = name

    wages = defaultdict(dict)
    with ZipFile('wages.zip') as bundle:
        for group in ['MSA', 'BOS']:
            with bundle.open(f'oesm25ma/{group}_M2025_dl.xlsx') as file:
                workbook = openpyxl.load_workbook(file, read_only=True, data_only=True)
                rows = iter(workbook.active.values)
                header = {name: pos for pos, name in enumerate(next(rows))}
                for row in rows:
                    if row[header['O_GROUP']] != 'detailed' or row[header['NAICS']] != '000000':
                        continue
                    values = [row[header[key]] for key in ('A_PCT25', 'A_MEDIAN', 'A_PCT75')]
                    if not all(isinstance(v, (int, float)) and v > 0 for v in values) or values != sorted(values):
                        continue
                    area, soc = row[header['AREA']], row[header['OCC_CODE']]
                    wages[area][soc] = values
    areas = sorted(set(names) & set(wages))
    zip_areas = defaultdict(set)
    zip_counties = defaultdict(set)
    with open('zcta.txt', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file, delimiter='|'):
            zip_code, county = row['GEOID_ZCTA5_20'], row['GEOID_COUNTY_20']
            if zip_code and county and int(row['AREALAND_PART'] or 0) > 0:
                zip_counties[zip_code].add(county)
    # Replace historical Connecticut counties with the 2022 Census equivalents.
    ct_counties = defaultdict(set)
    with open('zcta-ct.txt', encoding='utf-8-sig') as file:
        for row in csv.DictReader(file, delimiter='|'):
            zip_code, subdivision = row['GEOID_ZCTA5_20'], row['GEOID_COUSUB_22']
            if zip_code and subdivision and int(row['AREALAND_PART'] or 0) > 0:
                ct_counties[zip_code].add(subdivision[:5])
    for zip_code, counties in ct_counties.items():
        zip_counties[zip_code] = {c for c in zip_counties[zip_code] if not c.startswith('09')} | counties
    for zip_code, counties in zip_counties.items():
        for county in counties:
            zip_areas[zip_code].update(mapping[county])
    available = set(areas)
    # Do not silently pick an area if any overlapping county could not be mapped.
    zips = {z: sorted(zip_areas[z]) for z, counties in zip_counties.items()
            if zip_areas[z] and all(mapping[c] and mapping[c] <= available for c in counties)}
    # Keep downloads modest and group contiguous area codes into fixed assets.
    area_index = {}
    for offset in range(0, len(areas), 24):
        group = areas[offset:offset + 24]
        asset = f'wages-{offset // 24:02}'
        write(asset, {code: wages[code] for code in group})
        area_index.update({code: [names[code], asset] for code in group})
    write('geography', {'zips': zips, 'areas': area_index})
    print('ZCTAs:', len(zips), '/', len(zip_counties), 'multi-area:', sum(len(v) > 1 for v in zips.values()), flush=True)
    print('Wage areas:', len(areas), 'valid percentile rows:', sum(len(wages[c]) for c in areas), flush=True)
    for z in ['11432', '10001', '02138', '94103', '06604', '99501', '96799', '99999']:
        print(z, [(area_index[c][0], wages[c].get('13-1151')) for c in zips.get(z, [])], flush=True)


if __name__ == '__main__':
    occupations()
    wages_and_geography()
