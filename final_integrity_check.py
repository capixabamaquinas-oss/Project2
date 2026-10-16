import csv,hashlib,json
from pathlib import Path
run=Path(__file__).resolve().parent
root=run.parent.parent
def readcsv(name):
    with (run/name).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
hashes={}
for line in (run/"00_measured_package_sha256.txt").read_text(encoding="utf-8-sig").splitlines():
    if "  original/" in line:
        sha,rel=line.split("  ",1); name=Path(rel).name
        hashes[name]=sha
checks={}
for name,expected in hashes.items():
    a=hashlib.sha256((root/"babel_pura"/name).read_bytes()).hexdigest()
    b=hashlib.sha256((run/"source-copy"/"babel_pura"/name).read_bytes()).hexdigest()
    checks[name]={"original_matches":a==expected,"copy_matches":b==expected}
x2=readcsv("x2_repetitions.csv"); x2s=readcsv("x2_summary.csv")
x3=readcsv("x3_repetitions.csv"); x3s=readcsv("x3_summary.csv")
groups={}
for r in x2: groups.setdefault((r["case"],r["operation"],r["strategy"],r["chunk_size"],r["checksum"]),[]).append(r)
g3={}
for r in x3:g3.setdefault(r["metric"],[]).append(r)
report=(run/"REPORT.md").read_text(encoding="utf-8")
result={
 "package_files":len(hashes),
 "package_hashes_unchanged":all(v["original_matches"] and v["copy_matches"] for v in checks.values()),
 "x2_observations":len(x2),"x2_groups":len(groups),"x2_each_group_7":all(len(v)==7 for v in groups.values()),
 "x2_all_hashes_match":all(r["identical"]=="True" for r in x2),
 "x2_summary_groups":len(x2s),"x2_summary_all_hashes_match":all(r["all_identical"]=="True" for r in x2s),
 "x3_observations":len(x3),"x3_metric_counts":{k:len(v) for k,v in g3.items()},
 "x3_all_references_match":all(r["matches_reference"]=="True" for r in x3),
 "x3_summary_groups":len(x3s),"x3_summary_all_references_match":all(r["all_reference_checks_passed"]=="True" for r in x3s),
 "report_has_4_package_hash_rows":sum(1 for n in hashes if f"| babel_pura/{n} |" in report)==4,
 "generated_outputs_deleted":not (run/"work"/"outputs").exists(),
 "source_copy_cache_removed":not (run/"source-copy"/"babel_pura"/"__pycache__").exists(),
}
failed=[k for k,v in result.items() if (isinstance(v,bool) and not v)]
if result["x2_observations"]!=315 or result["x2_groups"]!=45 or not result["x2_each_group_7"]:failed.append("x2_counts")
if result["x3_observations"]!=60 or sorted(result["x3_metric_counts"].values())!=[15,15,15,15]:failed.append("x3_counts")
result["status"]="PASS" if not failed else "FAIL"
result["failed_checks"]=failed
text=json.dumps(result,indent=2,sort_keys=True)+"\n"
(run/"final_integrity.json").write_text(text,encoding="utf-8")
print(json.dumps(result,sort_keys=True))
if failed:raise SystemExit(1)
