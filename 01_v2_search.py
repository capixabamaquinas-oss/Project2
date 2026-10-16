from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p=Path('C:/Users/User PC/Downloads/Dossie_Operacional_Babel_Pura_App_v2_Revisado.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
for i,node in enumerate(root.iter('{%s}p'%ns['w'])):
 text=''.join(t.text or '' for t in node.iter('{%s}t'%ns['w']))
 ppr=node.find('w:pPr',ns); style=ppr.find('w:pStyle',ns) if ppr is not None else None; sid=style.get('{%s}val'%ns['w']) if style is not None else ''
 if sid.startswith('Heading') or any(k in text.lower() for k in ('x1','x2','x3','x4','x5','x6','7.1','experimento')): print(f'[{i}] {sid} {text}')
