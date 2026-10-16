from __future__ import annotations
import base64,binascii,ctypes,csv,hashlib,json,os,random,statistics,subprocess,sys,time
from pathlib import Path
RUN=Path(__file__).resolve().parent
COPY=RUN/"source-copy"
WORK=RUN/"work"
FIX=WORK/"fixtures"
OUT=WORK/"outputs"
SIZE16=16*1024*1024
SIZE4=4*1024*1024
SEED=20261016
ALGORITHMS=["crc32"]
CHUNKS=[64*1024,1024*1024,4*1024*1024]
NL=chr(10)

def imports():
    sys.path.insert(0,str(COPY))
    from babel_pura.codec import encode_h1_integer,integer_minimal_bytes,decode_h1_integer,encode_monolithic_file,encode_segmented_reverse,encode_segmented_two_pass,decode_monolithic_file,decode_segmented_reverse,decode_segmented_two_pass
    from babel_pura.address import encode_address,decode_address
    return locals()

class PMC(ctypes.Structure):
    _fields_=[("cb",ctypes.c_uint32),("PageFaultCount",ctypes.c_uint32),("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),("QuotaNonPagedPoolUsage",ctypes.c_size_t),("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
def peak_ws():
    ps=ctypes.WinDLL("psapi",use_last_error=True); k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.GetCurrentProcess.restype=ctypes.c_void_p
    ps.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(PMC),ctypes.c_uint32]; ps.GetProcessMemoryInfo.restype=ctypes.c_int
    p=PMC(); p.cb=ctypes.sizeof(p)
    if not ps.GetProcessMemoryInfo(k.GetCurrentProcess(),ctypes.byref(p),p.cb): raise ctypes.WinError(ctypes.get_last_error())
    return int(p.PeakWorkingSetSize)
def sha_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def prepare():
    f=imports(); FIX.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    specs={"random":random.Random(SEED).randbytes(SIZE16),"all_ff":bytes([255])*SIZE16,"all_00":bytes(SIZE16)}
    m={"seed":SEED,"size16":SIZE16,"cases":{}}
    for case,data in specs.items():
        src=FIX/f"{case}.bin"; src.write_bytes(data)
        idx=f["integer_minimal_bytes"](f["encode_h1_integer"](data)); (FIX/f"{case}.idx").write_bytes(idx)
        m["cases"][case]={"data_sha256":hashlib.sha256(data).hexdigest(),"data_bytes":len(data),"index_sha256":hashlib.sha256(idx).hexdigest(),"index_bytes":len(idx)}
    data=random.Random(SEED).randbytes(SIZE4); (FIX/"x3_4m.bin").write_bytes(data)
    idx=f["integer_minimal_bytes"](f["encode_h1_integer"](data))
    b64=base64.urlsafe_b64encode(data).rstrip(b"="); hx=data.hex().encode("ascii")
    (FIX/"x3_4m.base64url.txt").write_bytes(b64); (FIX/"x3_4m.hex.txt").write_bytes(hx)
    m["x3"]={"seed":SEED,"data_sha256":hashlib.sha256(data).hexdigest(),"data_bytes":len(data),"base64url_bytes":len(b64),"hex_bytes":len(hx),"index_sha256":hashlib.sha256(idx).hexdigest(),"index_bytes":len(idx),"crc32_bytes":binascii.crc32(data)&0xffffffff,"crc32_base64url":binascii.crc32(b64)&0xffffffff,"crc32_hex":binascii.crc32(hx)&0xffffffff}
    (RUN/"fixture_manifest.json").write_text(json.dumps(m,indent=2)+NL,encoding="utf-8")
    print(json.dumps({"prepared":True,"manifest":m},sort_keys=True))

def worker_x2(args):
    f=imports(); _,case,op,strategy,chunk_s,algo,rep=args
    m=json.loads((RUN/"fixture_manifest.json").read_text(encoding="utf-8"))
    src=FIX/f"{case}.bin"; idx=FIX/f"{case}.idx"; chunk=int(chunk_s) if chunk_s else None
    out=OUT/f"{case}_{op}_{strategy}_{chunk or 0}_{algo or 'none'}_r{rep}_pid{os.getpid()}.out"
    data=src.read_bytes() if op=="roundtrip" else None
    t=time.perf_counter()
    if op=="encode":
        if strategy=="monolithic": f["encode_monolithic_file"](src,out)
        elif strategy=="reverse": f["encode_segmented_reverse"](src,out,chunk)
        elif strategy=="two_pass": f["encode_segmented_two_pass"](src,out,chunk)
        else: raise ValueError(strategy)
        expected=m["cases"][case]["index_sha256"]
    elif op=="decode":
        if strategy=="monolithic": f["decode_monolithic_file"](idx,out)
        elif strategy=="reverse": f["decode_segmented_reverse"](idx,out,chunk)
        elif strategy=="two_pass": f["decode_segmented_two_pass"](idx,out,chunk)
        else: raise ValueError(strategy)
        expected=m["cases"][case]["data_sha256"]
    elif op=="roundtrip":
        value=f["encode_h1_integer"](data); ib=f["integer_minimal_bytes"](value)
        address=f["encode_address"](ib); parsed=f["decode_address"](address)
        restored=f["decode_h1_integer"](int.from_bytes(parsed,"big"))
        elapsed=(time.perf_counter()-t)*1000; mem=peak_ws(); actual=hashlib.sha256(restored).hexdigest(); expected=m["cases"][case]["data_sha256"]
        if actual!=expected: raise AssertionError(f"{actual} != {expected}")
        print(json.dumps({"suite":"X2","case":case,"operation":op,"strategy":strategy,"chunk_size":chunk,"checksum":algo,"repeat":int(rep),"pid":os.getpid(),"elapsed_ms":elapsed,"peak_working_set_bytes":mem,"expected_sha256":expected,"actual_sha256":actual,"identical":True},sort_keys=True)); return
    else: raise ValueError(op)
    elapsed=(time.perf_counter()-t)*1000; mem=peak_ws(); actual=sha_file(out)
    if actual!=expected: raise AssertionError(f"{actual} != {expected}")
    print(json.dumps({"suite":"X2","case":case,"operation":op,"strategy":strategy,"chunk_size":chunk,"checksum":algo or "","repeat":int(rep),"pid":os.getpid(),"elapsed_ms":elapsed,"peak_working_set_bytes":mem,"expected_sha256":expected,"actual_sha256":actual,"identical":True},sort_keys=True))

def worker_x3(args):
    f=imports(); _,metric,rep=args; m=json.loads((RUN/"fixture_manifest.json").read_text(encoding="utf-8"))["x3"]
    if metric=="baseline":
        data=(FIX/"x3_4m.bin").read_bytes(); t=time.perf_counter(); value=f["encode_h1_integer"](data); minimal=f["integer_minimal_bytes"](value); text=minimal.hex()
        elapsed=(time.perf_counter()-t)*1000; mem=peak_ws(); actual=hashlib.sha256(bytes.fromhex(text)).hexdigest()
        if actual!=m["index_sha256"]: raise AssertionError("baseline index hash mismatch")
        result={"output_bytes":len(minimal),"hex_chars":len(text),"sha256":actual,"matches_reference":True}
    else:
        p={"bytes":FIX/"x3_4m.bin","base64url_text":FIX/"x3_4m.base64url.txt","hex_text":FIX/"x3_4m.hex.txt"}[metric]
        raw=p.read_bytes(); t=time.perf_counter(); value=binascii.crc32(raw)&0xffffffff; elapsed=(time.perf_counter()-t)*1000; mem=peak_ws()
        expected=m["crc32_"+{"bytes":"bytes","base64url_text":"base64url","hex_text":"hex"}[metric]]
        if value!=expected: raise AssertionError(f"CRC {value} != {expected}")
        result={"crc32":value,"matches_reference":True}
    print(json.dumps({"suite":"X3","metric":metric,"repeat":int(rep),"pid":os.getpid(),"elapsed_ms":elapsed,"peak_working_set_bytes":mem,**result},sort_keys=True))

def summary(vals):
    xs=sorted(float(x) for x in vals); q1,_,q3=statistics.quantiles(xs,n=4,method="inclusive")
    return {"n":len(xs),"min":xs[0],"median":statistics.median(xs),"q1":q1,"q3":q3,"iqr":q3-q1,"max":xs[-1]}
def launch(mode,args,rawfile):
    av=[sys.executable,str(Path(__file__).resolve()),mode,*map(str,args)]
    env=os.environ.copy(); env["PYTHONDONTWRITEBYTECODE"]="1"
    p=subprocess.run(av,cwd=RUN,env=env,capture_output=True,text=True,encoding="utf-8",errors="replace")
    with rawfile.open("a",encoding="utf-8") as log:
        log.write("$ "+subprocess.list2cmdline(av)+NL+f"exit_code={p.returncode}"+NL+"stdout:"+NL+p.stdout)
        if p.stdout and not p.stdout.endswith(NL): log.write(NL)
        log.write("stderr:"+NL+p.stderr)
        if p.stderr and not p.stderr.endswith(NL): log.write(NL)
        log.write("---"+NL)
    if p.returncode: raise RuntimeError(f"worker failed {av}: {p.stderr}")
    return json.loads(p.stdout.strip().splitlines()[-1])
def run_x2():
    tasks=[]
    for case in ("random","all_ff","all_00"):
        for op in ("encode","decode"):
            tasks.append((case,op,"monolithic","","",""))
            for strategy in ("reverse","two_pass"):
                for chunk in CHUNKS: tasks.append((case,op,strategy,chunk,"",""))
        for algo in ALGORITHMS: tasks.append((case,"roundtrip","full_address","",algo,""))
    expanded=[(*t[:5],rep) for t in tasks for rep in range(1,8)]
    random.Random(SEED+1).shuffle(expanded)
    raw=RUN/"02_x2_worker_raw.txt"; raw.write_text("X2: one fresh Python subprocess per observation."+NL,encoding="utf-8")
    rows=[]
    for i,task in enumerate(expanded,1):
        rows.append(launch("worker-x2",task,raw))
        if i%25==0 or i==len(expanded): print(f"X2 subprocesses {i}/{len(expanded)} completed",flush=True)
    fields=["case","operation","strategy","chunk_size","checksum","repeat","pid","elapsed_ms","peak_working_set_bytes","expected_sha256","actual_sha256","identical"]
    with (RUN/"x2_repetitions.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    groups={}
    for r in rows: groups.setdefault((r["case"],r["operation"],r["strategy"],r["chunk_size"],r["checksum"]),[]).append(r)
    summ=[]
    for k,g in sorted(groups.items()):
        tm=summary([r["elapsed_ms"] for r in g]); ws=summary([r["peak_working_set_bytes"]/1048576 for r in g])
        summ.append({"case":k[0],"operation":k[1],"strategy":k[2],"chunk_size":k[3],"checksum":k[4],"repetitions":tm["n"],"time_min_ms":tm["min"],"time_median_ms":tm["median"],"time_q1_ms":tm["q1"],"time_q3_ms":tm["q3"],"time_iqr_ms":tm["iqr"],"time_max_ms":tm["max"],"peak_ws_min_mib":ws["min"],"peak_ws_median_mib":ws["median"],"peak_ws_q1_mib":ws["q1"],"peak_ws_q3_mib":ws["q3"],"peak_ws_iqr_mib":ws["iqr"],"peak_ws_max_mib":ws["max"],"all_identical":all(r["identical"] for r in g)})
    with (RUN/"x2_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
    print(f"X2 complete: {len(rows)} measurements; {len(summ)} groups; every SHA-256 matched={all(r['identical'] for r in rows)}")
def run_x3():
    tasks=[(metric,rep) for metric in ("bytes","base64url_text","hex_text","baseline") for rep in range(1,16)]
    random.Random(SEED+2).shuffle(tasks)
    raw=RUN/"03_x3_worker_raw.txt"; raw.write_text("X3: one fresh Python subprocess per observation."+NL,encoding="utf-8")
    rows=[]
    for i,task in enumerate(tasks,1):
        rows.append(launch("worker-x3",task,raw))
        if i%15==0 or i==len(tasks): print(f"X3 subprocesses {i}/{len(tasks)} completed",flush=True)
    fields=["metric","repeat","pid","elapsed_ms","peak_working_set_bytes","crc32","output_bytes","hex_chars","sha256","matches_reference"]
    with (RUN/"x3_repetitions.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    groups={}
    for r in rows: groups.setdefault(r["metric"],[]).append(r)
    summ=[]
    for k,g in sorted(groups.items()):
        tm=summary([r["elapsed_ms"] for r in g]); ws=summary([r["peak_working_set_bytes"]/1048576 for r in g])
        summ.append({"metric":k,"repetitions":tm["n"],"time_min_ms":tm["min"],"time_median_ms":tm["median"],"time_q1_ms":tm["q1"],"time_q3_ms":tm["q3"],"time_iqr_ms":tm["iqr"],"time_max_ms":tm["max"],"peak_ws_min_mib":ws["min"],"peak_ws_median_mib":ws["median"],"peak_ws_q1_mib":ws["q1"],"peak_ws_q3_mib":ws["q3"],"peak_ws_iqr_mib":ws["iqr"],"peak_ws_max_mib":ws["max"],"all_reference_checks_passed":all(r["matches_reference"] for r in g)})
    with (RUN/"x3_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
    print(f"X3 complete: {len(rows)} measurements; {len(summ)} groups; all reference checks passed={all(r['matches_reference'] for r in rows)}")
def main():
    if len(sys.argv)>1 and sys.argv[1]=="worker-x2": worker_x2(sys.argv[1:])
    elif len(sys.argv)>1 and sys.argv[1]=="worker-x3": worker_x3(sys.argv[1:])
    elif sys.argv[1:]==["prepare"]: prepare()
    elif sys.argv[1:]==["x2"]: run_x2()
    elif sys.argv[1:]==["x3"]: run_x3()
    else: raise SystemExit("usage: runner.py prepare|x2|x3|worker-x2|worker-x3")
if __name__=="__main__": main()
