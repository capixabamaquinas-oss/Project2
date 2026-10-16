from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
p=Path('C:/Users/User PC/Downloads/Dossie_Operacional_Babel_Pura_App_v2_Revisado.docx')
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z: root=ET.fromstring(z.read('word/document.xml'))
for i,node in enumerate(root.iter('{%s}p'%ns['w'])):
 text=''.join(t.text or '' for t in node.iter('{%s}t'%ns['w']))
 if 180 <= i <= 198: print(f'[{i}] {text}')
