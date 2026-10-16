from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent
manifest=root/'SHA256SUMS.txt'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
files=sorted((p for p in root.rglob('*') if p.is_file() and p!=manifest and p.name!='14_build_sha_manifest_raw.txt'),key=lambda p:p.relative_to(root).as_posix().lower())
lines=['SHA-256 inventory for Babel Pura H1 X1-X6 run','Paths are relative to this directory. The inventory excludes itself and captured stdout for this command.','']
for p in files:lines.append(f'{sha(p)}  {p.relative_to(root).as_posix()}')
manifest.write_text('\n'.join(lines)+'\n',encoding='utf-8')
entries=[]
for line in manifest.read_text(encoding='utf-8').splitlines()[3:]:
 digest,rel=line.split('  ',1); entries.append((digest,rel))
failed=[]
for digest,rel in entries:
 p=root/Path(rel)
 if not p.exists() or sha(p)!=digest:failed.append(rel)
print(f'files_hashed={len(files)}')
print(f'manifest_entries_verified={len(entries)}')
print(f'mismatches={failed}')
print(f'manifest_sha256={sha(manifest)}')


