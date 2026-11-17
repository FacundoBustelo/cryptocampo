#!/usr/bin/env python3
"""Revisa el contenido entregable sin red; opcionalmente exporta una copia limpia.

No instala dependencias ni acredita reproducción, publicación o estado actual de Sepolia.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delivery_files():
    raw = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT)
    paths = sorted(set(raw.decode().split('\0')) - {''})
    for name in paths:
        path = ROOT / name
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise ValueError(f'Ruta no permitida: {name}')
        if not path.is_file():
            raise ValueError(f'Archivo de entrega ausente: {name}')
    return paths


def anchors(path):
    result, counts = set(), {}
    source = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
    for title in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', source, flags=re.M):
        title = re.sub(r'[^\w\- ]', '', title.lower()).replace(' ', '-')
        count = counts.get(title, 0)
        counts[title] = count + 1
        result.add(title + (f'-{count}' if count else ''))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--snapshot', type=Path, help='Destino nuevo, fuera del proyecto; sin archivos ignorados.')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = (args.output_dir or ROOT / '.tools/delivery-check' / stamp).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'started_at': stamp, 'scope': 'local_files_only',
              'python': sys.version, 'checks': []}

    def check(name, errors, **details):
        report['checks'].append(dict(name=name, status='failed' if errors else 'passed',
                                     errors=errors, **details))
        print(f"{name}: {'failed' if errors else 'passed'}", flush=True)

    files = delivery_files()
    file_set = set(files)
    report['files_sha256'] = {name: sha(ROOT / name) for name in files}
    forbidden = []
    for name in files:
        parts = Path(name).parts
        if (any(p in {'.git', '.tools', 'lib', 'out', 'cache', 'broadcast', '__pycache__',
                      '.aws', 'keystores'} for p in parts)
                or (Path(name).name.startswith('.env') and name != '.env.example')
                or Path(name).suffix in {'.key', '.pem', '.pyc'}):
            forbidden.append(name)
    check('delivery-file-set', forbidden, files=len(files))

    # Leer solo valores del .env de este proyecto para detectar copias accidentales.
    # Nunca se imprimen valores, líneas de contenido ni hashes de secretos.
    secrets = []
    env_file = ROOT / '.env'
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.strip().removeprefix('export ').partition('=')
            value = value.strip().strip('\"\'')
            if sep and any(part in key for part in ('PRIVATE_KEY', 'API_KEY', 'RPC_URL')) and len(value) >= 16:
                secrets.append(value.lower())
                if value.startswith('0x'):
                    secrets.append(value[2:].lower())
    patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
                r'\bgh[pousr]_[A-Za-z0-9]{30,}', r'\bgithub_pat_[A-Za-z0-9_]{40,}',
                r'\bAKIA[0-9A-Z]{16}\b',
                r'--private-key\s+(?:0x)?[0-9a-fA-F]{64}\b',
                r'(?im)^\s*(?:export\s+)?\w*PRIVATE_KEY\s*=\s*[\"\']?(?:0x)?[0-9a-f]{64}\b']
    secret_hits = []
    for name in files:
        raw = (ROOT / name).read_bytes()
        source = raw.decode('utf-8', errors='replace')
        if any(value in source.lower() for value in secrets) or any(re.search(p, source) for p in patterns):
            secret_hits.append(name)
    check('credentials-scan', secret_hits, local_env_compared=bool(secrets),
          scope='Exact local env values and credential patterns; PNGs reviewed visually separately.')
    example = (ROOT / '.env.example').read_text().splitlines()
    check('env-example-empty', [line.split('=', 1)[0] for line in example
                               if '=' in line and not line.lstrip().startswith('#') and line.split('=', 1)[1].strip()])

    links, checked_links, checked_images = [], 0, 0
    for name in files:
        if not name.endswith('.md'):
            continue
        source = re.sub(r'```.*?```', '', (ROOT / name).read_text(), flags=re.S)
        for is_image, target in re.findall(r'(!?)\[[^\]]*\]\(([^)]+)\)', source):
            target = target.strip().strip('<>')
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            checked_links += 1
            path = ((ROOT / name).parent / unquote(url.path)).resolve() if url.path else ROOT / name
            if not path.is_relative_to(ROOT):
                links.append(f'{name}: enlace fuera de la entrega: {target}')
                continue
            relative = str(path.relative_to(ROOT))
            available = relative in file_set if path.is_file() else any(
                p.startswith(relative.rstrip('/') + '/') for p in files)
            if not available:
                links.append(f'{name}: enlace ausente del contenido entregable: {target}')
            elif url.fragment and path.suffix == '.md' and unquote(url.fragment) not in anchors(path):
                links.append(f'{name}: ancla ausente: {target}')
            if is_image:
                checked_images += 1
                if not path.is_file():
                    links.append(f'{name}: imagen ausente: {target}')
                elif path.suffix == '.png' and path.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
                    links.append(f'{name}: firma PNG inválida: {target}')
                elif path.suffix == '.svg':
                    ET.parse(path)
    check('relative-links-and-images', links, relative_links=checked_links, image_references=checked_images)

    base = ROOT / 'docs/evidence'
    for folder, expected in [('sepolia-journey-2026-11-15', 796), ('sepolia-verified-2026-11-15', 14)]:
        review = json.loads((base / folder / 'review.json').read_text())
        manifest = review['preserved_files_sha256']
        errors = [name for name, value in manifest.items()
                  if not (base / folder / name).is_file() or sha(base / folder / name) != value]
        if len(manifest) != expected:
            errors.append('Cantidad de archivos distinta de la revisión aprobada.')
        check(folder + '-hashes', errors, files=len(manifest))

    captures = base / 'metamask-import-2026-11-15'
    review = json.loads((captures / 'review.json').read_text())
    errors = []
    for name, record in review['captures'].items():
        path = captures / name
        raw = path.read_bytes()
        if (sha(path) != record['sha256'] or len(raw) != record['bytes']
                or raw[:8] != b'\x89PNG\r\n\x1a\n'
                or list(struct.unpack('>II', raw[16:24])) != record['dimensions_px']):
            errors.append(name)
    check('original-wallet-captures', errors, files=len(review['captures']))

    final = json.loads((base / 'sepolia-journey-2026-11-15/final-check/result.json').read_text())
    journey = json.loads((base / 'sepolia-journey-2026-11-15/review.json').read_text())
    receipts, errors = [], []
    guide = (ROOT / 'docs/entrega.md').read_text()
    for stage in final['context']['history']:
        urls = []
        for tx in stage['transactions']:
            receipt = tx['receipt']
            receipts.append(tx['hash'])
            urls.append(tx['url'])
            if (int(str(receipt['status']), 0) != 1 or receipt['transactionHash'] != tx['hash']
                    or tx['url'] != 'https://sepolia.etherscan.io/tx/' + tx['hash']
                    or tx['url'] not in guide):
                errors.append(f"Recibo o enlace inválido: {tx['hash']}")
        if urls != journey['transactions_by_stage'][stage['name']]:
            errors.append(f"Historial/enlaces difieren: {stage['name']}")
    if len(receipts) != 26 or len(set(receipts)) != 26:
        errors.append('Se requieren 26 recibos únicos.')
    if len(final['checks']) != 55 or any(c['status'] != 'passed' or c['actual'] != c['expected']
                                          for c in final['checks']):
        errors.append('Los 55 controles finales deben coincidir y estar aprobados.')
    check('archived-sepolia-receipts-and-state', errors, receipts=len(receipts), final_checks=len(final['checks']))

    old_sources = final['source_sha256']
    changed = [name for name, value in old_sources.items() if not (ROOT / name).is_file() or sha(ROOT / name) != value]
    # Única corrección reproducible: aislar la prueba RPC de out/ en una copia limpia.
    fixture_update = {'tools/test_sepolia.py': '03fca8b35a48d7dc152415b6d89ee30627b92ad6a2884efb99cad09289c4f11f'}
    unexpected = [name for name in changed if name != 'README.md'
                  and (name not in fixture_update or sha(ROOT / name) != fixture_update[name])]
    check('executed-sources-preserved', unexpected,
          changed_documentation=[name for name in changed if name == 'README.md'],
          corrected_test_fixtures={name: {'previous_sha256': old_sources[name], 'current_sha256': sha(ROOT / name)}
                                   for name in fixture_update},
          added_source_files=[name for name in sorted(file_set - set(old_sources))
                              if name.startswith(('src/', 'test/', 'script/', 'tools/', 'assets/', '.github/workflows/'))])

    original = ROOT.parent / 'Consignas-ProyectoFinal/README.md'
    check('assignment-copy', ['La copia difiere del README original.'] if original.is_file()
          and sha(original) != sha(ROOT / 'docs/consigna-entrega.md') else [],
          original_available=original.is_file(), copy_sha256=sha(ROOT / 'docs/consigna-entrega.md'))

    report['status'] = 'passed' if all(c['status'] == 'passed' for c in report['checks']) else 'failed'
    if args.snapshot and report['status'] == 'passed':
        destination = args.snapshot.resolve()
        if destination.is_relative_to(ROOT):
            raise ValueError('La copia debe estar fuera del proyecto.')
        destination.mkdir(parents=True, exist_ok=False)
        for name in files:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        report['snapshot'] = {'path': str(destination), 'files': len(files),
                              'hashes_match': all(sha(destination / name) == value
                                                  for name, value in report['files_sha256'].items()),
                              'installation_and_execution': 'not_run'}
        if not report['snapshot']['hashes_match']:
            report['status'] = 'failed'
    (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"{report['status']}: {output / 'result.json'}")
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
