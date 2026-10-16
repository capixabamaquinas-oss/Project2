from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p = Path('C:/Users/User PC/Downloads/Dossi\u00ea Operacional \u2014 Babel Pura App v3 (revisado).docx')
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z:
    root = ET.fromstring(z.read('word/document.xml'))
for i, node in enumerate(root.iter('{%s}p' % ns['w'])):
    text = ''.join(t.text or '' for t in node.iter('{%s}t' % ns['w']))
    low = text.lower()
    if any(token in low for token in ('x1','x2','x3','x4','x5','x6','chunk_size','checksum','endere?o enorme','truncado','hostil','escala')):
        print(f'[{i}] {text}')
