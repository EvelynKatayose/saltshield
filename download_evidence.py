"""Refresh the public DCR evidence snapshot; analysis uses the saved copy offline."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = 'https://www.mass.gov/info-details/dcr-watershed-system-salt-reduction'
DIRECTORY = Path(__file__).resolve().parent / 'data' / 'evidence'


def save_snapshot(content, retrieved_at=None):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    (DIRECTORY / 'dcr_salt_reduction_source.html').write_bytes(content)
    manifest = {
        'url': URL,
        'retrieved_at': retrieved_at or datetime.now(timezone.utc).isoformat(),
        'sha256': hashlib.sha256(content).hexdigest(),
        'record_scope': 'Historical awards FY2021–FY2026 listed by DCR',
        'interpretation': 'Award amount is not total equipment cost; award purpose is not proof of installation or current capacity.',
    }
    (DIRECTORY / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    request = urllib.request.Request(URL, headers={'User-Agent': 'SaltShield/0.2'})
    with urllib.request.urlopen(request, timeout=60) as response:
        print(json.dumps(save_snapshot(response.read()), indent=2))
