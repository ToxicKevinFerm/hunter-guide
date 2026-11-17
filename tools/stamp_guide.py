"""Stamps guide/index.html's script and stylesheet links with a hash of each file (?v=<hash>), so a browser never runs
a cached copy after an edit. Run after changing anything under guide/ or weave/."""
import hashlib, pathlib, re

GUIDE = pathlib.Path(__file__).resolve().parent.parent / 'guide'
page = GUIDE / 'index.html'
html = page.read_text(encoding='utf-8')

def stamp(m):
    attr, path = m.group(1), m.group(2)
    if path.startswith('http'):
        return m.group(0)
    digest = hashlib.sha1((GUIDE / path).read_bytes()).hexdigest()[:10]
    return f'{attr}="{path}?v={digest}"'

new = re.sub(r'(src|href)="([^"?#]+\.(?:js|css))(?:\?v=[0-9a-f]+)?"', stamp, html)
if new != html:
    page.write_text(new, encoding='utf-8')
print('\n'.join(re.findall(r'(?:src|href)="[^"]+\?v=[0-9a-f]+"', new)))
