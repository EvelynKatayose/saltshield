"""Extract structured, auditable award facts from the saved official DCR page."""
import csv
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data/evidence/dcr_salt_reduction_source.html'
URL = 'https://www.mass.gov/info-details/dcr-watershed-system-salt-reduction'
TARGETS = {'HOLDEN', 'STERLING', 'WEST BOYLSTON'}


def parse_awards(content):
    soup = BeautifulSoup(content, 'html.parser')
    heading = next(h for h in soup.find_all('h3') if h.get_text(strip=True) == 'Awards')
    year = None
    records = []
    for element in heading.find_next_siblings():
        if element.name == 'h4':
            match = re.fullmatch(r'FY(\d{2})', element.get_text(strip=True))
            if not match:
                raise ValueError('Unrecognized fiscal year heading')
            year = 2000 + int(match[1])
        elif element.name == 'h5':
            town = element.get_text(' ', strip=True).upper()
            details = element.find_next_sibling('ul')
            amount_line, purpose_line = details.find_all('li', recursive=False)
            match = re.search(r'\$\s*([\d,]+)', amount_line.get_text(' ', strip=True))
            if year is None or not match:
                raise ValueError('Award missing year or amount')
            purpose = purpose_line.get_text(' ', strip=True)
            lower = purpose.lower()
            tags = [tag for tag, patterns in {
                'spreader_controls': ['controller', 'spreader'],
                'brine_production': ['brine making', 'brine generator'],
                'brine_application': ['brine application', 'brine pump', 'spray bar', 'applicator'],
                'plow_blades': ['plow blade', 'plow blades', 'cutting edges'],
                'storage_or_facility': ['storage', 'shed', 'lean-to', 'electric service'],
                'temperature_sensors': ['temperature sensor'],
            }.items() if any(p in lower for p in patterns)]
            explicit_cost = re.search(r'\$\s*([\d,]+)', purpose)
            records.append({
                'record_id': f'DCR_FY{year}_{town.replace(" ", "_")}',
                'fiscal_year': year,
                'town': town,
                'grant_award_usd': int(match[1].replace(',', '')),
                'reported_historical_project_total_usd': int(explicit_cost[1].replace(',', '')) if explicit_cost else None,
                'equipment_categories': tags,
                'source_url': URL + '#' + element['id'],
                'source_locator': f'FY{year % 100:02d} / {town.title()}',
                'record_kind': 'OFFICIAL_HISTORICAL_AWARD',
                'grant_is_equipment_price': False,
                'current_quote_available': False,
                'installation_verified': False,
                'road_coverage_verified': False,
            })
    if not records:
        raise ValueError('No awards extracted')
    return records


def main():
    content = SOURCE.read_bytes()
    all_awards = parse_awards(content)
    records = [r for r in all_awards if r['town'] in TARGETS]
    # These checks validate the frozen snapshot, not future live-page counts.
    if len(all_awards) != 18 or len(records) != 13:
        raise ValueError('Source changed: review award extraction before updating the dataset')
    manifest = json.loads((SOURCE.parent / 'source_manifest.json').read_text())
    if manifest['sha256'] != hashlib.sha256(content).hexdigest():
        raise ValueError('Source checksum mismatch')
    summaries = []
    for town in sorted(TARGETS):
        rr = [r for r in records if r['town'] == town]
        summaries.append({
            'town': town, 'award_count': len(rr),
            'historical_grant_total_usd': sum(r['grant_award_usd'] for r in rr),
            'latest_award_fiscal_year': max(r['fiscal_year'] for r in rr),
            'categories_in_prior_awards': sorted({tag for r in rr for tag in r['equipment_categories']}),
            'asset_status': 'Prior funding documented; installed equipment and spare capacity unverified',
        })
    catalog = {
        'source': manifest,
        'all_watershed_award_count': len(all_awards),
        'three_town_award_count': len(records),
        'three_town_historical_grant_total_usd': sum(r['grant_award_usd'] for r in records),
        'records': records, 'town_summary': summaries,
        'current_procurement_costs_verified': False,
        'equipment_capacity_verified': False,
        'observed_local_salt_savings_available': False,
        'evidence_rules': [
            'Historical awards are evidence of funding, not current equipment quotes.',
            'Reported historical total costs are separate from grant awards and are not inflation-adjusted current prices.',
            'A funded purpose does not prove installation, availability, or road coverage.',
            'Prior award totals do not determine current grant eligibility or budget allocations.',
        ],
    }
    out = ROOT / 'results'
    (out / 'evidence_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
    flat = [{**r, 'equipment_categories': ';'.join(r['equipment_categories'])} for r in records]
    with (ROOT / 'data/evidence/dcr_historical_awards.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(flat[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(flat)
    print(json.dumps({'records': len(records), 'historical_grant_total_usd': catalog['three_town_historical_grant_total_usd'], 'summaries': summaries}, indent=2))
    return catalog


if __name__ == '__main__':
    main()
