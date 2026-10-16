from pathlib import Path
import csv, hashlib, json, random, shutil, zipfile
from xml.etree import ElementTree as ET
project = Path('C:/OllamaLimit/Sei l\u00e1/Projeto TTC/Babel Pura TTC')
run = project / 'experiments' / 'X1-X6_20261015'
copy_root = run / 'source-copy'
fixtures = run / 'fixtures'
x6 = run / 'x6_user_files'
for p in (copy_root, fixtures, x6):
    if p.exists(): raise SystemExit('Refusing to overwrite ' + str(p))
copy_root.mkdir(parents=True)
fixtures.mkdir()
x6.mkdir()
def ignore_cache(directory, names):
    return {n for n in names if n == '__pycache__' or n.endswith('.pyc')}
for name in ('babel_pura', 'tests'):
    shutil.copytree(project / name, copy_root / name, ignore=ignore_cache)
inputs = [
 ('dossier_v3_docx', Path('C:/Users/User PC/Downloads/Dossi\u00ea Operacional \u2014 Babel Pura App v3 (revisado).docx')),
 ('dossier_v2_docx', Path('C:/Users/User PC/Downloads/Dossie_Operacional_Babel_Pura_App_v2_Revisado.docx')),
 ('codec_py', project / 'babel_pura' / 'codec.py'),
 ('address_py', project / 'babel_pura' / 'address.py'),
 ('test_codec_py', project / 'tests' / 'test_codec.py'),
 ('test_address_py', project / 'tests' / 'test_address.py'),
]
manifest=[]
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
for label, source in inputs:
    dest=x6/(label+source.suffix)
    shutil.copyfile(source,dest)
    manifest.append({'kind':'real_user_file','label':label,'source_path':str(source),'copy_path':str(dest),'size_bytes':dest.stat().st_size,'sha256':sha(dest)})
source_docx=next(x6.glob('dossier_v3_docx.docx'))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(source_docx) as z: root=ET.fromstring(z.read('word/document.xml'))
paras=[]
for node in root.iter('{%s}p'%ns['w']):
    text=''.join(t.text or '' for t in node.iter('{%s}t'%ns['w']))
    if text.strip(): paras.append(text)
text_path=x6/'dossier_v3_extracted.txt'
text_path.write_bytes(('\n'.join(paras)+'\n').encode('utf-8'))
manifest.append({'kind':'derived_real_user_text','label':'dossier_v3_extracted','source_path':str(source_docx),'copy_path':str(text_path),'size_bytes':text_path.stat().st_size,'sha256':sha(text_path)})
sizes=[1024,65536,1048576,4194304,16777216]
for i,size in enumerate(sizes):
    seed=20261015+i
    data=random.Random(seed).randbytes(size)
    path=fixtures/f'seeded_random_{size}.bin'
    path.write_bytes(data)
    manifest.append({'kind':'seeded_random','label':path.name,'copy_path':str(path),'size_bytes':size,'seed':seed,'sha256':sha(path)})
edge={
 'empty':b'', 'single_nul':b'\x00', 'single_ff':b'\xff',
 'leading_zeroes':b'\x00\x00\x01\xff', 'all_byte_values':bytes(range(256)),
 'boundary_255':bytes(range(255)), 'boundary_256':bytes(range(256)),
 'carry_run_ff_64':b'\xff'*64, 'all_zero_4096':b'\x00'*4096,
}
for label,data in edge.items():
    path=fixtures/f'edge_{label}.bin'; path.write_bytes(data)
    manifest.append({'kind':'edge_vector','label':label,'copy_path':str(path),'size_bytes':len(data),'sha256':sha(path)})
(run/'input_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
copy_manifest=[]
for path in sorted(p for p in copy_root.rglob('*') if p.is_file()):
    rel=path.relative_to(copy_root).as_posix()
    copy_manifest.append({'relative_path':rel,'size_bytes':path.stat().st_size,'sha256':sha(path)})
(run/'source_copy_sha256.json').write_text(json.dumps(copy_manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'source_copy_files':len(copy_manifest),'x6_real_or_derived_files':len(inputs)+1,'random_fixtures':len(sizes),'edge_vectors':len(edge),'source_copy_root':str(copy_root),'input_manifest':str(run/'input_manifest.json'),'source_copy_sha256':str(run/'source_copy_sha256.json')},indent=2))
for row in manifest: print(f"INPUT {row['kind']} {row['label']} bytes={row['size_bytes']} sha256={row['sha256']}")
