"""Package the finished project without runtime data, caches or attachments."""
from pathlib import Path
from datetime import datetime,timezone
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]
directories=['app','assets','data','diagrams','docs','evidence','reports','scripts','tests','tools']
files=[ROOT/name for name in ['.gitignore','README.md','requirements-docs.txt']]
for name in directories:
 files.extend(p for p in (ROOT/name).rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.tmp']
              and not p.name.startswith('.~lock.'))
files=sorted(files)
validation=json.loads((ROOT/'evidence/document-validation.json').read_text())
assert validation['status']=='passed'
for report in validation['reports']:
 for suffix,digest in report['sha256'].items():
  path=ROOT/'reports'/f'УИТУ_Практическая_{report["report"]}_ТехноСервис{suffix}'
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
manifest={'created_at':datetime.now(timezone.utc).isoformat(),
          'report_pages':{str(r['report']):r['pages'] for r in validation['reports']},
          'checks':{'unit':10,'api':20,'browser':13},'idef0_diagrams':12,
          'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
target=ROOT/'deliverables';target.mkdir(exist_ok=True)
manifest_path=target/'manifest.json'
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
archive=target/'УИТУ_Практические_4-6_ТехноСервис.zip'
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
 for path in files+[manifest_path]:z.write(path,str(path.relative_to(ROOT)))
with ZipFile(archive) as z:
 assert z.testzip() is None
 for name,digest in manifest['files'].items():
  assert hashlib.sha256(z.read(name)).hexdigest()==digest
print(f'Packaged and verified {len(files)} files: {archive.name}')
