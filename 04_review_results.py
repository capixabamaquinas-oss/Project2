from pathlib import Path
import csv, hashlib, json, re
root=Path(__file__).resolve().parent
project=root.parent.parent
basefile=root/'00_baseline_raw.txt'
text=basefile.read_text(encoding='utf-8-sig',errors='replace')
expected={}
for line in text.splitlines():
 m=re.match(r'^([0-9A-Fa-f]{64}) \*(.+)$',line)
 if m: expected[m.group(2)]=m.group(1).lower()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
match=0; missing=[]; changed=[]
for path,digest in expected.items():
 p=Path(path)
 if not p.exists():missing.append(path);continue
 if sha(p).lower()==digest:match+=1
 else:changed.append({'path':path,'expected':digest,'actual':sha(p)})
print('BASELINE_FILE_COUNT='+str(len(expected)))
print('BASELINE_MATCH_COUNT='+str(match))
print('BASELINE_MISSING='+json.dumps(missing,ensure_ascii=True))
print('BASELINE_CHANGED='+json.dumps(changed,ensure_ascii=True))
copy=json.loads((root/'source_copy_sha256.json').read_text(encoding='utf-8'))
copy_match=0
for row in copy:
 p=project/row['relative_path']
 if p.exists() and sha(p)==row['sha256']:copy_match+=1
print('SOURCE_COPY_FILES='+str(len(copy)))
print('SOURCE_COPY_MATCH_ORIGINAL='+str(copy_match))

with (root/'x1_formats.csv').open(encoding='utf-8',newline='') as f:x1=list(csv.DictReader(f))
print('X1_4M_FORMATS=')
for r in x1:
 if r['input_bytes']=='4194304':print(json.dumps({k:r[k] for k in ('case','format','text_chars','payload_to_input_ratio','encode_median_ms','decode_median_ms','roundtrip')},ensure_ascii=True))
with (root/'x2_x4_scale.csv').open(encoding='utf-8',newline='') as f:x2=list(csv.DictReader(f))
print('X2_16M=')
for r in x2:
 if r['size_bytes']=='16777216':
  print(json.dumps({'method':r['method'],'chunk_size':r['chunk_size'],'median_seconds':float(r['median_elapsed_seconds']),'peak_ws_MiB':round(float(r['median_peak_working_set_bytes'])/1048576,2),'peak_ws_delta_MiB':round(float(r['median_peak_working_set_delta_bytes'])/1048576,2),'peak_commit_MiB':round(float(r['median_peak_commit_bytes'])/1048576,2),'output_sha256':r['output_sha256'],'all_repeats_same_output':r['all_repeats_same_output']},sort_keys=True))
with (root/'x3_checksum_candidates.csv').open(encoding='utf-8',newline='') as f:x3=list(csv.DictReader(f))
print('X3_4M_BASE64URL=')
for r in x3:
 if r['size_bytes']=='4194304' and (r['format']=='base64url-no-padding' or r['coverage']=='bytes'):
  print(json.dumps({k:r[k] for k in ('format','algorithm','coverage','checksum_bytes','checksum_hex_chars','median_checksum_ms')},sort_keys=True))
with (root/'x5_hostile.csv').open(encoding='utf-8',newline='') as f:x5=list(csv.DictReader(f))
print('X5_CASES=')
for r in x5:
 print(json.dumps({k:r.get(k) for k in ('case','mode','input_bytes','outcome','parser_calls','format_decode_calls','elapsed_seconds','peak_working_set_bytes','peak_working_set_delta_bytes','peak_commit_bytes')},sort_keys=True))
with (root/'x6_real_user_files.csv').open(encoding='utf-8',newline='') as f:x6=list(csv.DictReader(f))
print('X6_FILES=')
for r in x6:
 if r['format']=='base64url-no-padding':print(json.dumps({k:r[k] for k in ('file','input_bytes','input_sha256','format','index_text_chars','draft_address_chars_no_checksum','draft_address_to_file_ratio','roundtrip')},ensure_ascii=True))
runlog=(root/'03_run_raw.txt').read_text(encoding='utf-8-sig',errors='replace')
for tag in ('X2_DECODE_VALIDATION_FAIL','X2_ROUNDTRIP_FAIL','X2_OUTPUT_MISMATCH','X2_WORKER_FAIL'):
 print(tag+'_COUNT='+str(runlog.count(tag)))
print('FINAL_SUMMARY='+json.dumps(json.loads((root/'run_summary.json').read_text(encoding='utf-8')),sort_keys=True))
