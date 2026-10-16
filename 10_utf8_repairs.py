from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent/'REPORT.md'; s=p.read_text(encoding='utf-8')
repls={
'Mem?ria':'Mem\u00f3ria','tr?s formatos':'tr\u00eas formatos','`Ambos` ? o dobro':'`Ambos` \u00e9 o dobro','sup?em checksum':'sup\u00f5em checksum','cont\u00eam os casos':'cont\u00e9m os casos','Razao endere\u00e7o/arquivo':'Raz\u00e3o endere\u00e7o/arquivo','reais j? presentes':'reais j\u00e1 presentes','nao e contrato final':'n\u00e3o \u00e9 contrato final'
}
for a,b in repls.items():s=s.replace(a,b)
p.write_text(s,encoding='utf-8')
print('report_sha256='+hashlib.sha256(p.read_bytes()).hexdigest())
print('question_marks='+str(s.count('?')))
print('suspect='+repr([x for x in s.splitlines() if '?' in x or 'cont\u00eam os casos' in x or 'Razao' in x]))
