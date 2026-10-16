from pathlib import Path
p=Path(r"C:\OllamaLimit\Sei lá\Projeto TTC\Babel Pura TTC\experiments\X2-X3_repeat_dispersion_20261016\build_report.py")
lines=p.read_text(encoding="utf-8").splitlines()
found=False
for i,line in enumerate(lines):
    if line.strip()=='if line.startswith("original/"):':
        lines[i]='    if "  original/" in line:'
        found=True
if not found: raise SystemExit("hash table condition not found")
p.write_text("\n".join(lines)+"\n",encoding="utf-8",newline="")
print("hash condition fixed")
