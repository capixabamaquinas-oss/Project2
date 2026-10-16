import csv,importlib.util,json,random,statistics,sys
from pathlib import Path
run=Path(__file__).resolve().parent
runner=run/"runner.py"
spec=importlib.util.spec_from_file_location("measure_runner",runner)
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
rawmain=run/"02_x2_worker_raw.txt"
rows=[]
for line in rawmain.read_text(encoding="utf-8").splitlines():
    if line.startswith("{"):
        try: obj=json.loads(line)
        except json.JSONDecodeError: continue
        if obj.get("suite")=="X2": rows.append(obj)
if len(rows)!=315: raise SystemExit(f"expected 315 original records, got {len(rows)}")
rows=[r for r in rows if r["operation"]!="roundtrip"]
tasks=[(case,"roundtrip","full_address","","crc32",rep) for case in ("random","all_ff","all_00") for rep in range(1,8)]
random.Random(20261017).shuffle(tasks)
raw=run/"02_x2_roundtrip_recheck_worker_raw.txt"
raw.write_text("Authoritative X2 full-address rows; timer stops before SHA-256 verification; one fresh worker process per observation.\n",encoding="utf-8")
new=[]
for i,t in enumerate(tasks,1):
    new.append(mod.launch("worker-x2",t,raw))
    if i%7==0: print(f"full-address recheck {i}/21 completed",flush=True)
if any(not r["identical"] for r in new): raise SystemExit("hash mismatch")
with (run/"x2_full_path_recheck.csv").open("w",newline="",encoding="utf-8") as f:
    fields=list(new[0]); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(new)
rows.extend(new)
fields=["case","operation","strategy","chunk_size","checksum","repeat","pid","elapsed_ms","peak_working_set_bytes","expected_sha256","actual_sha256","identical"]
with (run/"x2_repetitions.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
def stats(vals):
    x=sorted(float(v) for v in vals); q1,_,q3=statistics.quantiles(x,n=4,method="inclusive")
    return (x[0],statistics.median(x),q1,q3,q3-q1,x[-1])
groups={}
for r in rows: groups.setdefault((r["case"],r["operation"],r["strategy"],r["chunk_size"],r["checksum"]),[]).append(r)
summary=[]
for k,g in sorted(groups.items()):
    t=stats([r["elapsed_ms"] for r in g]); m=stats([r["peak_working_set_bytes"]/1048576 for r in g])
    summary.append({"case":k[0],"operation":k[1],"strategy":k[2],"chunk_size":k[3],"checksum":k[4],"repetitions":len(g),"time_min_ms":t[0],"time_median_ms":t[1],"time_q1_ms":t[2],"time_q3_ms":t[3],"time_iqr_ms":t[4],"time_max_ms":t[5],"peak_ws_min_mib":m[0],"peak_ws_median_mib":m[1],"peak_ws_q1_mib":m[2],"peak_ws_q3_mib":m[3],"peak_ws_iqr_mib":m[4],"peak_ws_max_mib":m[5],"all_identical":all(r["identical"] for r in g)})
with (run/"x2_summary.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
print(json.dumps({"final_repetitions":len(rows),"groups":len(groups),"roundtrip_rechecked":len(new),"group_sizes_ok":all(len(g)==7 for g in groups.values()),"hashes_all_match":all(r["identical"] for r in rows)},sort_keys=True))
