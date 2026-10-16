from pathlib import Path
p=Path(__file__).resolve().parent/"final_integrity_check.py"
s=p.read_text(encoding="utf-8")
old='sha,rel=line.split("  ",1); name=rel.split("/",1)[1]'
new='sha,rel=line.split("  ",1); name=Path(rel).name'
if old not in s:raise SystemExit("context missing")
p.write_text(s.replace(old,new,1),encoding="utf-8",newline="")
print("integrity hash path fixed")
