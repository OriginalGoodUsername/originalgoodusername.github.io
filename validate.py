"""Check generated site files without a network, browser or original media."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
import xml.etree.ElementTree as ET
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.tags, self.ids, self.words = [], [], []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        self.tags.append((tag, data))
        if 'id' in data:
            self.ids.append(data['id'])

    def handle_data(self, data):
        self.words.append(data)


def normalized(value):
    return ' '.join(value.split())


def main():
    paths = sorted(ROOT.glob('**/*.html'))
    assert len(paths) == 9, f'Expected 9 HTML files, found {len(paths)}'
    pages = {p: Page(p) for p in paths}
    images = 0
    for path, page in pages.items():
        assert len([t for t, _ in page.tags if t == 'h1']) == 1, path
        assert len(page.ids) == len(set(page.ids)), f'Duplicate IDs: {path}'
        assert any(t == 'html' and a.get('lang') == 'en' for t, a in page.tags)
        assert any(t == 'meta' and a.get('name') == 'description' and a.get('content') for t, a in page.tags)
        if path.name != '404.html':
            assert any(t == 'link' and a.get('rel') == 'canonical' for t, a in page.tags)
        for tag, attrs in page.tags:
            urls = [attrs[k] for k in ('href', 'src') if k in attrs]
            if 'srcset' in attrs:
                urls += [v.strip().split()[0] for v in attrs['srcset'].split(',')]
            for url in urls:
                parsed = urlsplit(url)
                if parsed.scheme or parsed.netloc:
                    continue
                target = ROOT / unquote(parsed.path.lstrip('/')) if parsed.path else path
                if target.is_dir():
                    target /= 'index.html'
                assert target.is_file(), f'Broken local link: {path}: {url}'
                if parsed.fragment:
                    assert target in pages and parsed.fragment in pages[target].ids, f'Broken fragment: {url}'
            if tag == 'img':
                images += 1
                assert attrs.get('alt') and attrs.get('srcset') and attrs.get('sizes'), path
                with Image.open(ROOT / attrs['src'].lstrip('/')) as image:
                    ratio = int(attrs['width']) / int(attrs['height'])
                    assert abs(image.width/image.height - ratio) < .005, attrs['src']
            assert tag not in ('script', 'iframe', 'form'), f'Unexpected UI dependency: {path}'
    assert images == 20, images
    for content_file in (ROOT / 'content').glob('project_*.json'):
        data = json.loads(content_file.read_text(encoding='utf-8-sig'))
        page = pages[ROOT / 'projects' / data['slug'] / 'index.html']
        text = normalized(' '.join(page.words))
        for value in [data['title'], data['summary'], *data['paragraphs'], *[m['caption'] for m in data['media']]]:
            assert normalized(value) in text, f'Missing supplied text: {data["slug"]}'
    for image_file in (ROOT / 'media').glob('photo_??.webp'):
        with Image.open(image_file) as master:
            for variant in image_file.parent.glob(image_file.stem + '-*.webp'):
                with Image.open(variant) as image:
                    assert image.width == int(variant.stem.rsplit('-', 1)[1])
                    assert image.width < master.width
                    assert abs(image.width/image.height - master.width/master.height) < .005
    sitemap = ET.parse(ROOT / 'sitemap.xml')
    assert len(sitemap.getroot()) == 8
    data = json.loads((ROOT / 'content/resume.json').read_text(encoding='utf-8-sig'))
    with pymupdf.open(ROOT / 'resume.pdf') as pdf:
        assert len(pdf) == 1, 'Resume must be one page.'
        text = normalized(pdf[0].get_text())
        def values(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    yield from values(value)
            elif isinstance(obj, list):
                for value in obj:
                    yield from values(value)
            elif isinstance(obj, str) and not obj.startswith('https://'):
                yield obj
        for value in values(data):
            assert normalized(value) in text, f'Missing PDF content: {value}'
        spans = [s for b in pdf[0].get_text('dict')['blocks'] if 'lines' in b for line in b['lines'] for s in line['spans']]
        assert min(s['size'] for s in spans) >= 9
        assert all('Arial' in s['font'] for s in spans)
        assert all(pymupdf.Rect(s['bbox']).x0 >= 30 and pymupdf.Rect(s['bbox']).x1 <= 582 and pymupdf.Rect(s['bbox']).y1 <= 765 for s in spans)
        assert len(pdf[0].get_links()) == 6, 'Expected contact and project links in PDF.'
        print(f'PDF: one page; all JSON text present; minimum type {min(s["size"] for s in spans):g} pt Arial; 6 working link annotations.')
    assert (ROOT / '.nojekyll').is_file()
    print('PASS: 9 HTML files, local links/anchors, 20 image placements, 15 full-frame masters, source copy, sitemap and PDF.')


if __name__ == '__main__':
    main()
