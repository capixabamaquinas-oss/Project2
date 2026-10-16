from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent/'REPORT.md'; s=p.read_text(encoding='utf-8')
s=s.replace('n?o e contrato final','n?o ? contrato final')
s=s.replace('?ndice nos tr?s formatos','?ndice nos tr?s formatos')
s=s.replace('O DOCX v3 atualmente dispon?vel em Downloads n?o cont?m','O DOCX v3 atualmente dispon?vel em Downloads n?o cont?m')
s=s.replace('Foram processados 7 arquivos reais ou texto derivado de documento real','Foram processadas 7 entradas, entre arquivos reais e texto extra?do de documento real')
p.write_text(s,encoding='utf-8')
print('report_sha256='+hashlib.sha256(p.read_bytes()).hexdigest())
print('question_marks='+str(s.count('?')))
