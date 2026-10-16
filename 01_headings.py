from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p = Path('C:/Users/User PC/Downloads/Dossi\u00ea Operacional \u2014 Babel Pura App v3 (revisado).docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
for i,node in enumerate(root.iter('{%s}p'%ns['w'])):
    text=''.join(t.text or '' for t in node.iter('{%s}t'%ns['w']))
    ppr=node.find('w:pPr',ns); style=ppr.find('w:pStyle',ns) if ppr is not None else None
    sid=style.get('{%s}val'%ns['w']) if style is not None else ''
    if sid.startswith('Heading') or '7.1' in text or 'X1' in text.upper(): print(f'[{i}] {sid} {text}')
