from pathlib import Path
import re
p=Path(__file__).resolve().parent/'REPORT.md'
s=p.read_text(encoding='utf-8')
s=s.replace('X1 ?','X1 -').replace('X2 ?','X2 -').replace('X3 ?','X3 -').replace('X4 ?','X4 -').replace('X5 ?','X5 -').replace('X6 ?','X6 -').replace(' | ? |',' | n/a |').replace('min?sculo','min\u00fasculo')
words={
'Relatorio':'Relat\u00f3rio','execucao':'execu\u00e7\u00e3o','nucleo':'n\u00facleo','sequencias':'sequ\u00eancias','copia':'c\u00f3pia','descartavel':'descart\u00e1vel','codigo':'c\u00f3digo','tambem':'tamb\u00e9m','area':'\u00e1rea','temporaria':'tempor\u00e1ria','validacao':'valida\u00e7\u00e3o','pre-extraido':'pr\u00e9-extra\u00eddo','temporario':'tempor\u00e1rio','nao':'n\u00e3o','esta':'est\u00e1','disponivel':'dispon\u00edvel','secao':'se\u00e7\u00e3o','diferenca':'diferen\u00e7a','especificacoes':'especifica\u00e7\u00f5es','hashado':'hashado','tres':'tr\u00eas','codificacao':'codifica\u00e7\u00e3o','decodificacao':'decodifica\u00e7\u00e3o','politica':'pol\u00edtica','aleatorias':'aleat\u00f3rias','aleatorios':'aleat\u00f3rios','saidas':'sa\u00eddas','estrategias':'estrat\u00e9gias','memoria':'mem\u00f3ria','monolitico':'monol\u00edtico','sensivel':'sens\u00edveis','maximo':'m\u00e1ximo','pratico':'pr\u00e1tico','decisao':'decis\u00e3o','endereco':'endere\u00e7o','valido':'v\u00e1lido','usuario':'usu\u00e1rio','extracao':'extra\u00e7\u00e3o','razao':'raz\u00e3o','conclusao':'conclus\u00e3o','especificacao':'especifica\u00e7\u00e3o','repeticoes':'repeti\u00e7\u00f5es','contem':'cont\u00eam','inicio':'in\u00edcio','importacao':'importa\u00e7\u00e3o','diferenca':'diferen\u00e7a','Medidas':'Medidas','Metodo':'M\u00e9todo','Metodo':'M\u00e9todo','aleatorio':'aleat\u00f3rio','sao':'s\u00e3o','arquivo temporario':'arquivo tempor\u00e1rio','conteudo':'conte\u00fado','escalas':'escalas','simbolo':'s\u00edmbolo','execucao chegou':'execu\u00e7\u00e3o chegou','possivel':'poss\u00edvel','indices':'\u00edndices','versao':'vers\u00e3o','funcao':'fun\u00e7\u00e3o','incluem':'incluem','dossie':'dossi\u00ea','seeds':'seeds','saida':'sa\u00edda','endereco/arquivo':'endere\u00e7o/arquivo','Endereco':'Endere\u00e7o','endereco candidato':'endere\u00e7o candidato','hexadecimal minusculo':'hexadecimal min\u00fasculo','aceito':'aceito','aprovacao':'aprova\u00e7\u00e3o','decodificar':'decodificar','escolha':'escolha','limite':'limite','validos':'v\u00e1lidos'
}
for old,new in words.items():
 s=re.sub(r'(?<![A-Za-z_])'+re.escape(old)+r'(?![A-Za-z_])',new,s)
p.write_text(s,encoding='utf-8')
print('report_utf8='+str(p))
print('unicode_headings='+str([line for line in s.splitlines() if line.startswith('### X')]))
print('question_mark_artifacts='+str(s.count('?')))
