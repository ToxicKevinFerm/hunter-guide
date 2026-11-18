"""Stamps the script and stylesheet links of guide/index.html and prebis-new/index.html with a hash of each file
(?v=<hash>), so a browser never runs a cached copy after an edit. Run after changing anything under guide/, weave/,
prebis-new/ or data.js."""
import hashlib, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent

for name in ('guide', 'prebis-new'):
    folder = ROOT / name
    page = folder / 'index.html'
    if not page.exists():
        continue
    html = page.read_text(encoding='utf-8')

    def stamp(m):
        attr, path = m.group(1), m.group(2)
        if path.startswith('http'):
            return m.group(0)
        digest = hashlib.sha1((folder / path).read_bytes()).hexdigest()[:10]
        return f'{attr}="{path}?v={digest}"'

    new = re.sub(r'(src|href)="([^"?#]+\.(?:js|css))(?:\?v=[0-9a-f]+)?"', stamp, html)
    if new != html:
        page.write_text(new, encoding='utf-8')
    print(name + ':')
    print('\n'.join('  ' + s for s in re.findall(r'(?:src|href)="[^"]+\?v=[0-9a-f]+"', new)))
