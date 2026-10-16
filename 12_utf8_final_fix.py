from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent/'REPORT.md'; s=p.read_text(encoding='utf-8')
s=s.replace('extra?do','extra\u00eddo').replace('n?o e contrato final','n\u00e3o \u00e9 contrato final')
p.write_text(s,encoding='utf-8')
print('report_sha256='+hashlib.sha256(p.read_bytes()).hexdigest())
print('question_marks='+str(s.count('?')))
