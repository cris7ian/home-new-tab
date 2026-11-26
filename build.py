from base64 import b64encode
from pathlib import Path
import re

root = Path(__file__).resolve().parent
src, vendor, public = (root / name for name in ('src', 'vendor', 'public'))


def text(path):
    return path.read_text(encoding='utf-8')


def font(family, file, weight, style='normal'):
    data = b64encode((vendor / file).read_bytes()).decode('ascii')
    return f"@font-face{{font-family:'{family}';src:url(data:font/woff2;base64,{data}) format('woff2');font-style:{style};font-weight:{weight};font-display:swap}}"


fonts = '\n'.join((font('Bodoni Moda', 'bodoni.woff2', 500),
                   font('Bodoni Moda', 'bodoni-italic.woff2', 500, 'italic'),
                   font('DM Mono', 'dm-mono.woff2', 400)))
replacements = {
    '/* @FONTS@ */': fonts,
    '/* @CSS@ */': text(src / 'style.css'),
    '<!-- @MAP@ -->': text(src / 'map.svg'),
    '/* @ASTRONOMY@ */': text(vendor / 'astronomy.browser.min.js'),
    '/* @APP@ */': text(src / 'app.js'),
}
licenses = '\n\n'.join(text(vendor / filename) for filename in ('bodoni-OFL.txt', 'dm-mono-OFL.txt'))
page = text(src / 'page.html')
for key, value in replacements.items():
    if page.count(key) != 1:
        raise ValueError(f'Expected one occurrence of {key}')
    if key in ('/* @ASTRONOMY@ */', '/* @APP@ */') and re.search(r'</script', value, re.I):
        raise ValueError(f'{key} contains a closing script tag')
    page = page.replace(key, value)
page += '\n<!-- Bundled font licenses\n' + licenses.replace('--', '—') + '\n-->\n'
public.mkdir(exist_ok=True)
output = public / 'index.html'
output.write_text(page, encoding='utf-8')
print(f'{output}: {output.stat().st_size:,} bytes')
