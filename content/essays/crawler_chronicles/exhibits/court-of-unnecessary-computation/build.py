#!/usr/bin/env python3
"""Build the satirical exhibit using the author's local latex-atlas styles."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
ATLAS = Path(os.environ.get('ATLAS_ROOT', str(Path.home() / 'Repos/personal/latex-atlas')))
styles = [ATLAS / 'sty' / name for name in ('atlas.sty', 'atlas-grand.sty')]
if not all(p.is_file() for p in styles):
    raise SystemExit('Set ATLAS_ROOT to the latex-atlas checkout.')
work = Path(tempfile.mkdtemp(prefix='crawler-chancery-'))
env = dict(os.environ, TEXINPUTS=str(ATLAS / 'sty') + os.pathsep,
           TEXMFCACHE=str(work / 'tex-cache'), SOURCE_DATE_EPOCH='1792368000',
           FORCE_SOURCE_DATE='1', TZ='UTC')
(work / 'tex-cache').mkdir()
# PDF viewers disagree on the seal's individually rotated font glyphs. Outline
# its lettering through SVG before embedding it; retain vector shapes at any zoom.
result = subprocess.run(['lualatex', '-no-shell-escape', '-interaction=nonstopmode',
                         '-halt-on-error', '-file-line-error',
                         '-output-directory=' + str(work), str(ROOT / 'seal.tex')],
                        cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
(work / 'seal-build.txt').write_text(result.stdout + result.stderr)
if result.returncode:
    print((result.stdout + result.stderr)[-5000:])
    raise SystemExit(f'Seal compilation failed; logs: {work}')
subprocess.run(['pdftocairo', '-svg', str(work / 'seal.pdf'),
                str(work / 'court-seal.svg')], check=True)
svg = (work / 'court-seal.svg').read_text()
if '<text' in svg or '<image' in svg:
    raise SystemExit('The seal must contain vector outlines only.')
subprocess.run(['rsvg-convert', '--format=pdf', '--output=' + str(work / 'court-seal.pdf'),
                str(work / 'court-seal.svg')], check=True)
fonts = subprocess.run(['pdffonts', str(work / 'court-seal.pdf')],
                       capture_output=True, text=True, check=True).stdout.splitlines()
if len(fonts) > 2:
    raise SystemExit('The seal still contains fonts; expected outlines only.')
for name in ('court-seal.svg', 'court-seal.pdf'):
    shutil.copyfile(work / name, ROOT / name)
for run in range(3):
    result = subprocess.run(['lualatex', '-no-shell-escape', '-interaction=nonstopmode',
                             '-halt-on-error', '-file-line-error',
                             '-output-directory=' + str(work), str(ROOT / 'notice.tex')],
                            cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    (work / f'pass-{run+1}.txt').write_text(result.stdout + result.stderr)
    if result.returncode:
        print((result.stdout + result.stderr)[-5000:])
        raise SystemExit(f'Compilation failed; logs: {work}')
shutil.copyfile(work / 'notice.pdf', ROOT / 'notice.pdf')
subprocess.run(['pdftoppm', '-f', '1', '-singlefile', '-scale-to', '1500',
                '-png', str(ROOT / 'notice.pdf'), str(ROOT / 'notice-preview')], check=True)
subprocess.run(['pdftoppm', '-f', '5', '-singlefile', '-scale-to', '1500',
                '-png', str(ROOT / 'notice.pdf'), str(ROOT / 'notice-certificate-preview')], check=True)
manifest = {'source_sha256': hashlib.sha256((ROOT / 'notice.tex').read_bytes()).hexdigest(),
            'pdf_sha256': hashlib.sha256((ROOT / 'notice.pdf').read_bytes()).hexdigest(),
            'seal': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                     for name in ('seal.tex', 'court-seal.svg', 'court-seal.pdf')},
            'seal_rendering': 'Vector outlines only; no fonts or raster images.',
            'atlas_styles': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in styles},
            'build_logs': str(work), 'passes': 3, 'shell_escape': False,
            'status': 'Satirical petition prepared for dispatch; no dispatch recorded.'}
(ROOT / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print('Built:', ROOT / 'notice.pdf')
print('Logs:', work)
