from __future__ import annotations
import base64, collections, csv, hashlib, json, math, os, random, statistics, subprocess, sys, time, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE_ROOT=ROOT/'source-copy'
FIX=ROOT/'fixtures'
X6=ROOT/'x6_user_files'
WORK=ROOT/'work'
WORK.mkdir(exist_ok=True)
sys.dont_write_bytecode=True
sys.path.insert(0,str(PACKAGE_ROOT))
from babel_pura import codec, address
FORMATS=['hex-lower','base32-no-padding','base64url-no-padding']
FORMAT_FUNCS={'monolithic':codec.encode_monolithic_file,'segmented_reverse':codec.encode_segmented_reverse,'segmented_two_pass':codec.encode_segmented_two_pass}
DECODE_FUNCS={'monolithic':codec.decode_monolithic_file,'segmented_reverse':codec.decode_segmented_reverse,'segmented_two_pass':codec.decode_segmented_two_pass}

def sha_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def sha_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def equal_files(a:Path,b:Path)->bool:
 if a.stat().st_size!=b.stat().st_size:return False
 with a.open('rb') as x,b.open('rb') as y:
  while True:
   p=x.read(1024*1024); q=y.read(1024*1024)
   if p!=q:return False
   if not p:return True
def median(values): return statistics.median(values)
def write_csv(path,rows):
 rows=list(rows)
 if not rows:return
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def print_json(obj): print(json.dumps(obj,sort_keys=True,ensure_ascii=True))
def run_child(script,args,raw_log):
 argv=[sys.executable,'-X','utf8','-I',str(script)]+[str(x) for x in args]
 cp=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace')
 with raw_log.open('a',encoding='utf-8') as f:
  f.write('ARGV='+json.dumps(argv,ensure_ascii=True)+'\n')
  f.write('RETURN_CODE='+str(cp.returncode)+'\nSTDOUT_BEGIN\n'+cp.stdout+'STDOUT_END\nSTDERR_BEGIN\n'+cp.stderr+'STDERR_END\n')
 if cp.returncode!=0: return None,cp
 try:return json.loads(cp.stdout.strip().splitlines()[-1]),cp
 except Exception:return None,cp

print('RUN_RUNTIME='+sys.version.replace('\n',' '))
print('RUN_PLATFORM='+sys.platform+' '+__import__('platform').platform())
print('EXPERIMENT_PARAMETERS chunks=[4096,65536,1048576] x2_repeats=3 checksum_repeats=3 x5_limit_parameter=4096_not_product_policy')

# Edge-vector correctness exercise on the copied package only.
edge_rows=[]
edge_files=sorted(FIX.glob('edge_*.bin'))
edge_out=WORK/'edge_outputs'; edge_out.mkdir(exist_ok=True)
for src in edge_files:
 data=src.read_bytes(); value=codec.encode_h1_integer(data); expected=codec.integer_minimal_bytes(value)
 core_ok=codec.decode_h1_integer(value)==data
 fmt_ok=True
 for fmt in FORMATS:
  text=codec.encode_format(fmt,expected); restored=codec.decode_format(fmt,text)
  fmt_ok=fmt_ok and codec.decode_h1_integer(int.from_bytes(restored,'big'))==data
 methods=[('monolithic',None)]+[(m,c) for m in ('segmented_reverse','segmented_two_pass') for c in (1,2,3,64,4096)]
 for method,chunk in methods:
  suffix='mono' if chunk is None else f'{method}_{chunk}'
  enc=edge_out/(src.stem+'_'+suffix+'.idx'); dec=edge_out/(src.stem+'_'+suffix+'.bin')
  try:
   if chunk is None: FORMAT_FUNCS[method](src,enc)
   else: FORMAT_FUNCS[method](src,enc,chunk)
   enc_ok=enc.read_bytes()==expected
   if chunk is None: DECODE_FUNCS[method](enc,dec)
   else: DECODE_FUNCS[method](enc,dec,chunk)
   dec_ok=dec.read_bytes()==data
   outcome='PASS' if core_ok and fmt_ok and enc_ok and dec_ok else 'FAIL'
   detail=''
  except Exception as e:
   enc_ok=False; dec_ok=False; outcome='FAIL'; detail=type(e).__name__+': '+str(e)[:120]
  edge_rows.append({'vector':src.stem,'input_bytes':len(data),'input_sha256':sha_bytes(data),'method':method,'chunk_size':chunk,'core_roundtrip':core_ok,'format_roundtrip':fmt_ok,'file_encode_matches_integer':enc_ok,'file_decode_matches_input':dec_ok,'result':outcome,'detail':detail})
write_csv(ROOT/'edge_vectors.csv',edge_rows)
print('EDGE_SUMMARY='+json.dumps({'rows':len(edge_rows),'passed':sum(r['result']=='PASS' for r in edge_rows),'failed':sum(r['result']!='PASS' for r in edge_rows)},sort_keys=True))

# X1: payload serialization length and encode/decode time.
x1_rows=[]
x1_inputs=[(p.stem,p) for p in edge_files]
for p in sorted(FIX.glob('seeded_random_*.bin')):
 if p.stat().st_size<=4194304: x1_inputs.append((p.stem,p))
for label,path in x1_inputs:
 data=path.read_bytes(); index=codec.integer_minimal_bytes(codec.encode_h1_integer(data))
 for fmt in FORMATS:
  try:
   payload=codec.encode_format(fmt,index)
   enc_times=[]; dec_times=[]
   for _ in range(3):
    t=time.perf_counter_ns(); got=codec.encode_format(fmt,index); enc_times.append(time.perf_counter_ns()-t)
    t=time.perf_counter_ns(); back=codec.decode_format(fmt,payload); dec_times.append(time.perf_counter_ns()-t)
   roundtrip=(back==index and codec.decode_h1_integer(int.from_bytes(back,'big'))==data)
   x1_rows.append({'case':label,'input_bytes':len(data),'input_sha256':sha_bytes(data),'format':fmt,'index_bytes':len(index),'text_bytes':len(payload),'text_chars':len(payload.decode('ascii')),'payload_to_input_ratio':('' if not data else len(payload)/len(data)),'encode_median_ms':median(enc_times)/1e6,'decode_median_ms':median(dec_times)/1e6,'roundtrip':roundtrip})
  except Exception as e:
   x1_rows.append({'case':label,'input_bytes':len(data),'input_sha256':sha_bytes(data),'format':fmt,'index_bytes':len(index),'text_bytes':'','text_chars':'','payload_to_input_ratio':'','encode_median_ms':'','decode_median_ms':'','roundtrip':False,'error':type(e).__name__+': '+str(e)[:120]})
write_csv(ROOT/'x1_formats.csv',x1_rows)
print('X1_SUMMARY='+json.dumps({'records':len(x1_rows),'passed':sum(bool(r['roundtrip']) for r in x1_rows),'failed':sum(not bool(r['roundtrip']) for r in x1_rows),'formats':FORMATS},sort_keys=True))

# X2/X4: randomized nonrepetitive files, package file encoders, multiple sizes and chunk sizes.
x2_rows=[]; worker_raw=ROOT/'x2_worker_raw.txt'; worker_raw.write_text('',encoding='utf-8')
codec_worker=ROOT/'03_worker_codec.py'; sizes=[1024,65536,1048576,4194304,16777216]; chunks=[4096,65536,1048576]; repeats=3
outroot=WORK/'x2_outputs'; outroot.mkdir(exist_ok=True)
validation=WORK/'x2_validation'; validation.mkdir(exist_ok=True)
for size in sizes:
 src=FIX/f'seeded_random_{size}.bin'; group=[]
 tasks=[('monolithic',None)]+[(m,c) for m in ('segmented_reverse','segmented_two_pass') for c in chunks]
 for method,chunk in tasks:
  reps=[]
  for rep in range(1,repeats+1):
   cname='mono' if chunk is None else str(chunk)
   out=outroot/f'{size}_{method}_{cname}_r{rep}.idx'
   result,cp=run_child(codec_worker,['--package-root',PACKAGE_ROOT,'--source',src,'--output',out,'--method',method,'--chunk-size',chunk or 65536],worker_raw)
   if result is None:
    print('X2_WORKER_FAIL='+json.dumps({'size':size,'method':method,'chunk':chunk,'rep':rep,'returncode':cp.returncode,'stderr':cp.stderr[-400:]},ensure_ascii=True)); continue
   result.update({'repeat':rep,'source_file':src.name})
   reps.append(result); group.append((method,chunk,out,result))
   print('X2_RUN='+json.dumps({'size':size,'method':method,'chunk':chunk,'repeat':rep,'seconds':result['elapsed_seconds'],'peak_ws':result['peak_working_set_bytes'],'peak_commit':result['peak_commit_bytes'],'out_sha256':result['output_sha256']},sort_keys=True))
  if reps:
   x2_rows.append({'size_bytes':size,'input_sha256':sha_file(src),'method':method,'chunk_size':chunk,'repeat_count':len(reps),'median_elapsed_seconds':median([x['elapsed_seconds'] for x in reps]),'median_peak_working_set_bytes':median([x['peak_working_set_bytes'] for x in reps]),'median_peak_working_set_delta_bytes':median([x['peak_working_set_delta_bytes'] for x in reps]),'median_peak_commit_bytes':median([x['peak_commit_bytes'] for x in reps]),'median_peak_commit_delta_bytes':median([x['peak_commit_delta_bytes'] for x in reps]),'output_bytes':reps[0]['output_bytes'],'output_sha256':reps[0]['output_sha256'],'all_repeats_same_output':len({x['output_sha256'] for x in reps})==1})
 ref=next((r['output_sha256'] for m,c,o,r in group if m=='monolithic' and c is None),None)
 unique={}
 for method,chunk,out,result in group:
  unique[(method,chunk)]=out
  if result['output_sha256']!=ref: print('X2_OUTPUT_MISMATCH='+json.dumps({'size':size,'method':method,'chunk':chunk,'expected':ref,'actual':result['output_sha256']}))
 for (method,chunk),out in unique.items():
  decoded=validation/f'{size}_{method}_{chunk or 0}.bin'
  try:
   if chunk is None: codec.decode_monolithic_file(out,decoded)
   elif method=='segmented_reverse': codec.decode_segmented_reverse(out,decoded,chunk)
   else: codec.decode_segmented_two_pass(out,decoded,chunk)
   ok=equal_files(src,decoded)
  except Exception as e: ok=False; print('X2_DECODE_VALIDATION_FAIL='+json.dumps({'size':size,'method':method,'chunk':chunk,'error':type(e).__name__+': '+str(e)[:160]}))
  if not ok: print('X2_ROUNDTRIP_FAIL='+json.dumps({'size':size,'method':method,'chunk':chunk}))
 print('X2_SIZE_COMPLETE='+str(size))
write_csv(ROOT/'x2_x4_scale.csv',x2_rows)
# X4 data quality/seed register.
x4_rows=[]
for i,size in enumerate(sizes):
 p=FIX/f'seeded_random_{size}.bin'; data=p.read_bytes(); counts=collections.Counter(data); n=len(data)
 entropy=0.0 if not n else -sum((v/n)*math.log2(v/n) for v in counts.values())
 x4_rows.append({'file':p.name,'size_bytes':n,'seed':20261015+i,'sha256':sha_bytes(data),'distinct_byte_values':len(counts),'byte_entropy_bits_per_symbol':entropy,'source_kind':'random.Random(seed).randbytes; non-repeating fixture class, not a repeated-byte block'})
write_csv(ROOT/'x4_random_fixtures.csv',x4_rows)
print('X2_X4_SUMMARY='+json.dumps({'records':len(x2_rows),'sizes':sizes,'chunk_sizes':chunks,'repeats':repeats,'random_inputs':len(x4_rows),'all_roundtrip_validations_done':True},sort_keys=True))

# X3: checksum candidates and coverage choices; sizes are the same random data.
def digest(name,data):
 if name=='crc32':return zlib.crc32(data).to_bytes(4,'big')
 if name=='sha256':return hashlib.sha256(data).digest()
 if name=='sha256_128':return hashlib.sha256(data).digest()[:16]
 if name=='blake2s_128':return hashlib.blake2s(data,digest_size=16).digest()
 raise ValueError(name)
algorithms=['crc32','sha256','sha256_128','blake2s_128']; x3_rows=[]
for size in sizes:
 data=(FIX/f'seeded_random_{size}.bin').read_bytes(); index=codec.integer_minimal_bytes(codec.encode_h1_integer(data))
 text_by_format={f:codec.encode_format(f,index) for f in FORMATS}
 scopes=[('bytes',None)]+[(scope,f) for f in FORMATS for scope in ('text','both')]
 for alg in algorithms:
  for scope,fmt in scopes:
   text=b'' if fmt is None else text_by_format[fmt]
   def calculate():
    if scope=='bytes':return digest(alg,data)
    if scope=='text':return digest(alg,text)
    return digest(alg,data)+digest(alg,text)
   sample=calculate(); times=[]
   for _ in range(3):
    t=time.perf_counter_ns(); result=calculate(); times.append(time.perf_counter_ns()-t)
   assert result==sample
   x3_rows.append({'size_bytes':size,'format':fmt or 'format-independent','algorithm':alg,'coverage':scope,'index_text_bytes':len(text) if fmt else 0,'checksum_bytes':len(sample),'checksum_hex_chars':len(sample)*2,'median_checksum_ms':median(times)/1e6,'checksum_repeatable':True,'candidate_status':'measurement candidate only; no product choice'})
write_csv(ROOT/'x3_checksum_candidates.csv',x3_rows)
print('X3_SUMMARY='+json.dumps({'records':len(x3_rows),'algorithms':algorithms,'coverage_scopes':['bytes','text per format','both as two separate digests'],'repeats':3},sort_keys=True))

# X5: hostile input tests against package parser, plus separate experimental preflight wrapper.
x5dir=FIX/'x5_cases'; x5dir.mkdir(exist_ok=True); prefix=b'B1:v1:'; limit=4096
cases={
 'limit_4095':prefix+b'F'*(4095-len(prefix)),
 'limit_4096':prefix+b'F'*(4096-len(prefix)),
 'limit_4097':prefix+b'F'*(4097-len(prefix)),
 'truncated_hex':b'B1:v1:abc',
 'garbage_hex':b'B1:v1:zz',
 'wrong_prefix':b'B0:v1:ff',
 'huge_garbage_8m':b'X'*(8*1024*1024),
 'huge_valid_hex_8m':prefix+b'f'*(8*1024*1024-len(prefix)),
}
for name,b in cases.items():
 if name=='huge_valid_hex_8m' and (len(b)-len(prefix))%2: b=b[:-1]
 (x5dir/(name+'.txt')).write_bytes(b)
x5_rows=[]; x5_raw=ROOT/'x5_worker_raw.txt'; x5_raw.write_text('',encoding='utf-8'); x5worker=ROOT/'03_worker_x5.py'
for name in cases:
 inp=x5dir/(name+'.txt')
 modes=['direct'] if not name.startswith('limit_') else ['direct','preflight']
 for mode in modes:
  result,cp=run_child(x5worker,['--package-root',PACKAGE_ROOT,'--input',inp,'--mode',mode,'--limit',limit],x5_raw)
  if result is None:
   x5_rows.append({'case':name,'mode':mode,'input_bytes':inp.stat().st_size,'result':'WORKER_FAILURE','detail':cp.stderr[-300:]})
   print('X5_WORKER_FAIL='+json.dumps({'case':name,'mode':mode,'returncode':cp.returncode,'stderr':cp.stderr[-300:]},ensure_ascii=True)); continue
  result['case']=name; x5_rows.append(result); print('X5_RUN='+json.dumps(result,sort_keys=True))
write_csv(ROOT/'x5_hostile.csv',x5_rows)
preflight_4097=next((r for r in x5_rows if r.get('case')=='limit_4097' and r.get('mode')=='preflight'),{})
direct_4097=next((r for r in x5_rows if r.get('case')=='limit_4097' and r.get('mode')=='direct'),{})
print('X5_GUARD_ASSERT='+json.dumps({'experimental_limit':limit,'preflight_plus1_rejected_before_parser':preflight_4097.get('parser_calls')==0 and preflight_4097.get('format_decode_calls')==0,'package_direct_plus1_called_parser':direct_4097.get('parser_calls')==1,'package_direct_plus1_called_format_decode':direct_4097.get('format_decode_calls')==1,'guard_is_in_experiment_harness_only':True},sort_keys=True))

# X6: real user-provided documents and H1 source files, copied and hashed in input_manifest.json.
x6_rows=[]
for p in sorted(X6.iterdir()):
 if not p.is_file():continue
 data=p.read_bytes(); idx=codec.integer_minimal_bytes(codec.encode_h1_integer(data))
 for fmt in FORMATS:
  payload=codec.encode_format(fmt,idx); back=codec.decode_format(fmt,payload)
  recovered=codec.decode_h1_integer(int.from_bytes(back,'big'))
  address_chars=(len('B1:v1:')+len(payload)) if payload else len('B1:v1:EMPTY')
  x6_rows.append({'file':p.name,'input_bytes':len(data),'input_sha256':sha_bytes(data),'format':fmt,'index_bytes':len(idx),'index_text_chars':len(payload),'draft_address_chars_no_checksum':address_chars,'draft_address_to_file_ratio':address_chars/len(data) if data else '', 'roundtrip':recovered==data,'scope_note':'draft B1:v1 prefix only; no checksum or final envelope decision'})
write_csv(ROOT/'x6_real_user_files.csv',x6_rows)
print('X6_SUMMARY='+json.dumps({'real_or_derived_inputs':len(list(X6.iterdir())),'records':len(x6_rows),'passed':sum(r['roundtrip'] for r in x6_rows),'failed':sum(not r['roundtrip'] for r in x6_rows)},sort_keys=True))

summary={'edge_rows':len(edge_rows),'edge_passed':sum(r['result']=='PASS' for r in edge_rows),'edge_failed':sum(r['result']!='PASS' for r in edge_rows),'x1_records':len(x1_rows),'x1_passed':sum(bool(r['roundtrip']) for r in x1_rows),'x1_failed':sum(not bool(r['roundtrip']) for r in x1_rows),'x2_x4_records':len(x2_rows),'x3_records':len(x3_rows),'x5_records':len(x5_rows),'x6_records':len(x6_rows),'x6_passed':sum(r['roundtrip'] for r in x6_rows),'x6_failed':sum(not r['roundtrip'] for r in x6_rows)}
(ROOT/'run_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print('FINAL_SUMMARY='+json.dumps(summary,sort_keys=True))
