import csv,json,statistics
from pathlib import Path
run=Path(__file__).resolve().parent
raw=run/"02_x2_worker_raw.txt"
rows=[]
for line in raw.read_text(encoding="utf-8").splitlines():
    if line.startswith("{"):
        try:
            obj=json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("suite")=="X2": rows.append(obj)
def stats(vals):
    xs=sorted(float(v) for v in vals)
    q1,_,q3=statistics.quantiles(xs,n=4,method="inclusive")
    return {"n":len(xs),"min":xs[0],"median":statistics.median(xs),"q1":q1,"q3":q3,"iqr":q3-q1,"max":xs[-1]}
fields=["case","operation","strategy","chunk_size","checksum","repeat","pid","elapsed_ms","peak_working_set_bytes","expected_sha256","actual_sha256","identical"]
with (run/"x2_repetitions.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
groups={}
for r in rows: groups.setdefault((r["case"],r["operation"],r["strategy"],r["chunk_size"],r["checksum"]),[]).append(r)
summary=[]
for k,g in sorted(groups.items()):
    t=stats([r["elapsed_ms"] for r in g]); m=stats([r["peak_working_set_bytes"]/1048576 for r in g])
    summary.append({"case":k[0],"operation":k[1],"strategy":k[2],"chunk_size":k[3],"checksum":k[4],"repetitions":t["n"],"time_min_ms":t["min"],"time_median_ms":t["median"],"time_q1_ms":t["q1"],"time_q3_ms":t["q3"],"time_iqr_ms":t["iqr"],"time_max_ms":t["max"],"peak_ws_min_mib":m["min"],"peak_ws_median_mib":m["median"],"peak_ws_q1_mib":m["q1"],"peak_ws_q3_mib":m["q3"],"peak_ws_iqr_mib":m["iqr"],"peak_ws_max_mib":m["max"],"all_identical":all(r["identical"] for r in g)})
with (run/"x2_summary.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
failed=[r for r in rows if not r["identical"]]
wrong_groups=[(k,len(g)) for k,g in groups.items() if len(g)!=7]
print(json.dumps({"raw_workers":len(rows),"groups":len(groups),"groups_not_7":wrong_groups,"hash_mismatches":len(failed),"distinct_pids":len({r["pid"] for r in rows}),"repetitions_csv_rows":sum(1 for _ in (run/"x2_repetitions.csv").open(encoding="utf-8"))-1,"summary_csv_rows":len(summary)},sort_keys=True))
