"""Stage the self-contained website for GitHub Pages."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent


def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    config=json.loads((ROOT/'deployment/site.json').read_text())
    home=config['expected_url'].rstrip('/')+'/'
    url=home+'?demo=1'
    host=urlsplit(home).hostname or ''
    if not url.startswith('https://') or not host.endswith('github.io'):raise ValueError('The demo requires the published GitHub Pages HTTPS URL')
    base=urlsplit(home).path
    if base!=config['base_path']:raise ValueError('Hosting URL and routing base must agree')
    report=(ROOT/'results/SaltShield_Wachusett.html').read_text()
    report=report.replace('name="saltshield-base" content="/"','name="saltshield-base" content="'+base+'"')
    report=report.replace('href="#experience"','href="'+base+'"').replace('href="?demo=1#experience"','href="'+base+'?demo=1"')
    (output/'index.html').write_text(report)
    (output/'.nojekyll').write_text('')
    files=['index.html','.nojekyll']
    for route in ['overview','investments','coverage','evidence']:
        (output/route).mkdir(exist_ok=True)
        (output/route/'index.html').write_text(report)
        files.append(route+'/index.html')
    manifest={'source_report_sha256':hashlib.sha256((ROOT/'results/SaltShield_Wachusett.html').read_bytes()).hexdigest(),'published_index_sha256':hashlib.sha256((output/'index.html').read_bytes()).hexdigest(),'demo_entry':url,'base_path':base,'files':files}
    (output/'build_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'output':str(output),'files':manifest['files'],'demo_entry':url},indent=2))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default=str(ROOT/'docs'));args=parser.parse_args();build(args.output)
