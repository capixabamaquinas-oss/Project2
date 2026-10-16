from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent/'REPORT.md'; s=p.read_text(encoding='utf-8')
repls={
'O DOCX v3 atualmente dispon?vel em Downloads n?o cont?m a tabela':'O DOCX v3 atualmente dispon?vel em Downloads n?o cont?m a tabela',
'- Memoria:':'- Mem?ria:',
'nos tres formatos':'nos tr?s formatos',
'O overhead total de `Ambos` e o dobro':'O overhead total de `Ambos` ? o dobro',
'Tamanhos mostrados supoem':'Tamanhos mostrados sup?em',
'`x3_checksum_candidates.csv` cont?m':'`x3_checksum_candidates.csv` cont?m',
'Foram medidos 7 entradas reais':'Foram processados 7 arquivos reais',
'n?o e contrato final':'n?o ? contrato final',
'Razao endere?o/arquivo':'Raz?o endere?o/arquivo',
'arquivos reais ja presentes':'arquivos reais j? presentes',
'?ndice nos tres formatos':'?ndice nos tr?s formatos',
'X2 - soma monol?tica':'X2 - soma monol?tica',
'monolitica':'monol?tica','monolitico':'monol?tico',
'sens?veis ao chunk':'sens?veis ao tamanho do chunk',
'nao pode ser revalidado':'n?o pode ser revalidado'
}
for a,b in repls.items(): s=s.replace(a,b)
p.write_text(s,encoding='utf-8')
print('report_sha256='+hashlib.sha256(p.read_bytes()).hexdigest())
print('question_marks='+str(s.count('?')))
print('suspect_grammar='+str([x for x in s.splitlines() if 'n?o cont?m' in x or 'supoe' in x or 'Razao' in x or 'n?o e ' in x]))
