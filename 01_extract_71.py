from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import re
p = Path('C:/Users/User PC/Downloads/Dossi\u00ea Operacional \u2014 Babel Pura App v3 (revisado).docx')
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with ZipFile(p) as z:
    root = ET.fromstring(z.read('word/document.xml'))
paras = []
for node in root.iter('{%s}p' % ns['w']):
    text = ''.join(t.text or '' for t in node.iter('{%s}t' % ns['w']))
    if text.strip():
        paras.append(text)
matches = [i for i, text in enumerate(paras) if re.search(r'(?<!\d)7\.1\b', text)]
print('dossier=' + str(p))
print('paragraph_count=' + str(len(paras)))
print('7.1_match_indexes=' + repr(matches))
if not matches:
    raise SystemExit('No section 7.1 heading/text found')
start = matches[0]
end = len(paras)
for i in range(start + 1, len(paras)):
    if re.match(r'^\s*(?:?\s*)?7\.2\b', paras[i]):
        end = i
        break
print('=== ?7.1 extracted text ===')
for i in range(start, end):
    print(f'[{i}] {paras[i]}')
