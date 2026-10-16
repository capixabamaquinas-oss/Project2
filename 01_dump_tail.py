from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p = Path('C:/Users/User PC/Downloads/Dossi\u00ea Operacional \u2014 Babel Pura App v3 (revisado).docx')
ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z:
    root = ET.fromstring(z.read('word/document.xml'))
for i, node in enumerate(root.iter('{%s}p' % ns['w'])):
    if i < 300: continue
    text = ''.join(t.text or '' for t in node.iter('{%s}t' % ns['w']))
    ppr = node.find('w:pPr', ns)
    style = ppr.find('w:pStyle', ns) if ppr is not None else None
    numpr = ppr.find('w:numPr', ns) if ppr is not None else None
    style_id = style.get('{%s}val' % ns['w']) if style is not None else ''
    nums = ''
    if numpr is not None:
        ilvl = numpr.find('w:ilvl',ns); numid = numpr.find('w:numId',ns)
        nums = f" numId={numid.get('{%s}val'%ns['w']) if numid is not None else ''} ilvl={ilvl.get('{%s}val'%ns['w']) if ilvl is not None else ''}"
    if text.strip(): print(f'[{i}] style={style_id}{nums} {text}')
