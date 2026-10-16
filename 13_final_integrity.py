from pathlib import Path
import csv,hashlib,json,re
root=Path(__file__).resolve().parent; project=root.parent.parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def csvrows(name):
 with (root/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
base=(root/'00_baseline_raw.txt').read_text(encoding='utf-8-sig',errors='replace'); expected={}
for line in base.splitlines():
 m=re.match(r'^([0-9A-Fa-f]{64}) \*(.+)$',line)
 if m:expected[m.group(2)]=m.group(1).lower()
missing=[]; changed=[]
for name,h in expected.items():
 p=Path(name)
 if not p.exists():missing.append(name)
 elif sha(p)!=h:changed.append(name)
copy=json.loads((root/'source_copy_sha256.json').read_text(encoding='utf-8'))
copy_mismatch=[]
for r in copy:
 p=project/r['relative_path']
 if not p.exists() or sha(p)!=r['sha256']:copy_mismatch.append(r['relative_path'])
summary=json.loads((root/'run_summary.json').read_text(encoding='utf-8'))
x1=csvrows('x1_formats.csv'); x2=csvrows('x2_x4_scale.csv'); x3=csvrows('x3_checksum_candidates.csv'); x5=csvrows('x5_hostile.csv'); x5b=csvrows('x5_boundary_verified.csv'); x6=csvrows('x6_real_user_files.csv'); edge=csvrows('edge_vectors.csv')
by={(r['case'],r['mode']):r for r in x5b}
assert len(expected)==33 and not missing and not changed
assert len(copy)==5 and not copy_mismatch
assert len(edge)==99 and all(r['result']=='PASS' for r in edge)
assert len(x1)==39 and all(r['roundtrip']=='True' for r in x1)
assert len(x2)==35 and all(r['all_repeats_same_output']=='True' for r in x2)
assert len(x3)==140 and all(r['checksum_repeatable']=='True' for r in x3)
assert by[('lowercase_limit_4096','preflight')]['outcome']=='accepted'
assert by[('lowercase_limit_4097','preflight')]['parser_calls']=='0'
assert by[('lowercase_limit_4097','preflight')]['format_decode_calls']=='0'
assert by[('lowercase_limit_4097','direct')]['parser_calls']=='1'
assert len(x6)==21 and all(r['roundtrip']=='True' for r in x6)
report=root/'REPORT.md'; result={'baseline_original_files':len(expected),'baseline_hash_matches':len(expected)-len(missing)-len(changed),'baseline_missing':missing,'baseline_changed':changed,'source_copy_files':len(copy),'source_copy_mismatches':copy_mismatch,'edge_passed':len(edge),'x1_passed':len(x1),'x2_aggregate_cases':len(x2),'x3_checksum_rows':len(x3),'x5_hostile_rows':len(x5),'x5_corrected_boundary_rows':len(x5b),'x6_passed':len(x6),'report_sha256':sha(report),'status':'PASS'}
(root/'integrity_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,sort_keys=True))
