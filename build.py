"""Build the public site from repository-owned content and WebP masters."""
from pathlib import Path
from html import escape
import json
import re
from PIL import Image
from resume_pdf import build_resume

ROOT = Path(__file__).resolve().parent
SITE = 'https://originalgoodusername.github.io'


def read(name):
    return json.loads((ROOT / 'content' / f'{name}.json').read_text(encoding='utf-8-sig'))


def e(value):
    return escape(str(value), quote=True)


def write(path, text):
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding='utf-8', newline='\n')


def link(url, label, **attrs):
    assert url.startswith(('/', '#', 'https://', 'mailto:')), f'Invalid URL: {url}'
    extra = ''.join(f' {key.replace("_", "-")}="{e(value)}"' for key, value in attrs.items())
    return f'<a href="{e(url)}"{extra}>{e(label)}</a>'


def paragraphs(items):
    return ''.join(f'<p>{e(item)}</p>' for item in items)


def bullets(items, cls=''):
    return f'<ul class="{cls}">' + ''.join(f'<li>{e(item)}</li>' for item in items) + '</ul>'


def prepare_media():
    dimensions = {}
    for master in sorted((ROOT / 'media').glob('photo_??.webp')):
        with Image.open(master) as image:
            dimensions[master.stem] = image.size
            for width in (480, 800, 1200):
                if width < image.width:
                    height = round(image.height * width / image.width)
                    image.resize((width, height), Image.Resampling.LANCZOS).save(
                        master.with_name(f'{master.stem}-{width}.webp'), quality=85, method=6)
    assert len(dimensions) == 15, 'Expected 15 WebP masters.'
    with Image.open(ROOT / 'media/photo_02.webp') as image:
        image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        image.save(ROOT / 'media/social.jpg', quality=88, optimize=True)
    return dimensions


def photo(item, dimensions, sizes, eager=False):
    ident = item['id']
    width, height = dimensions[ident]
    variants = [(n, f'/media/{ident}-{n}.webp') for n in (480, 800, 1200) if n < width]
    variants.append((width, f'/media/{ident}.webp'))
    src = next((url for n, url in variants if n >= 800), variants[-1][1])
    srcset = ', '.join(f'{url} {n}w' for n, url in variants)
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return (f'<img src="{src}" srcset="{srcset}" sizes="{sizes}" width="{width}" height="{height}" '
            f'alt="{e(item["alt"])}" {loading} decoding="async">')


def figure(item, dimensions, eager=False):
    width, height = dimensions[item['id']]
    screenshot = item['id'] in ('photo_03', 'photo_06', 'photo_07', 'photo_08', 'photo_11')
    cls = ' screenshot' if screenshot else (' portrait' if height > width else '')
    sizes = '(max-width: 700px) calc(100vw - 40px), (max-width: 1160px) 80vw, 900px' if screenshot else '(max-width: 700px) calc(100vw - 40px), 540px'
    return (f'<figure class="project-figure{cls}"><a class="photo-link" href="/media/{item["id"]}.webp" '
            f'aria-label="{e("Open full image: " + item["caption"])}">'
            f'{photo(item, dimensions, sizes, eager)}</a><figcaption>{e(item["caption"])}</figcaption></figure>')


def shell(title, description, route, body, home, contact, active='Projects', noindex=False):
    navigation = ''.join(link(url, label, **({'aria_current': 'page'} if label == active else {}))
                         for url, label in [('/#projects', 'Projects'), ('/resume/', 'Resume'), ('/contact/', 'Contact')])
    robots = '<meta name="robots" content="noindex,follow">' if noindex else ''
    canonical = '' if noindex else f'<link rel="canonical" href="{SITE}{route}">'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
{canonical}{robots}
<meta name="theme-color" content="#f8f7f3">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(home['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{SITE}{route}">
<meta property="og:image" content="{SITE}/media/social.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="900">
<meta property="og:image:alt" content="{e(SOCIAL_ALT)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{SITE}/media/social.jpg">
<meta name="twitter:image:alt" content="{e(SOCIAL_ALT)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/styles.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header wrap">
{link('/', home['name'], **{'class': 'wordmark'})}
<nav aria-label="Main navigation">{navigation}</nav>
</header>
<main id="main" class="wrap" tabindex="-1">{body}</main>
<footer class="site-footer wrap"><span>{e(home['name'])}</span><nav aria-label="Contact links">
{link('mailto:' + contact['email'], 'Email')}{link(contact['github'], 'GitHub')}{link(contact['linkedin'], 'LinkedIn')}
</nav></footer>
</body></html>
'''


def home_body(home, projects, dimensions):
    cards = []
    for i, project in enumerate(projects):
        cover = next(m for m in project['media'] if m['id'] == project['cover'])
        path = f'/projects/{project["slug"]}/'
        cards.append(f'''<article class="project-card {'featured' if i == 0 else ''}">
<a class="photo-link" href="{path}" aria-label="{e('View project: ' + project['title'])}">
{photo(cover, dimensions, '(max-width: 700px) calc(100vw - 40px), (max-width: 1160px) calc((100vw - 80px) / 2), 540px', i == 0)}</a>
<div class="project-info"><span class="project-number" aria-hidden="true">{i + 1:02d}</span>
<h3>{link(path, project['title'])}</h3><p>{e(project['summary'])}</p>
<p class="tools-line">{e(' / '.join(project['tools']))}</p>
<div class="text-links">{link(path, 'View project', aria_label='View project: ' + project['title'])}{link(project['github'], 'GitHub', aria_label=project['title'] + ' on GitHub')}</div>
</div></article>''')
    return f'''<section class="intro" aria-labelledby="name"><div><p class="eyebrow">Portfolio</p>
<h1 id="name">{e(home['name'])}</h1><p class="role">{e(home['role'])}</p></div>
<div class="intro-copy"><p>{e(home['intro'])}</p><div class="text-links">{link('/resume/', 'Resume')}{link('/contact/', 'Contact')}</div></div></section>
<section id="projects" aria-labelledby="projects-title"><div class="section-heading"><h2 id="projects-title">Selected projects</h2><span>5 projects</span></div>
<div class="project-grid">{''.join(cards)}</div></section>
<section class="about section-rule" aria-labelledby="about-title"><h2 id="about-title">About</h2><div><p>{e(home['about'])}</p>
<div class="text-links">{link('/resume/', 'View resume')}{link('mailto:' + CONTACT['email'], 'Email me')}</div></div></section>'''


def project_body(project, projects, dimensions):
    cover = next(m for m in project['media'] if m['id'] == project['cover'])
    other_media = [m for m in project['media'] if m['id'] != project['cover']]
    next_project = projects[(projects.index(project) + 1) % len(projects)]
    gallery = ''
    if other_media:
        gallery = f'''<section class="gallery-section" aria-labelledby="gallery-title"><div class="section-heading"><h2 id="gallery-title">Photos &amp; details</h2><p>Open an image for a closer look.</p></div>
<div class="gallery">{''.join(figure(m, dimensions) for m in other_media)}</div></section>'''
    return f'''<div class="breadcrumb">{link('/#projects', 'All projects')}</div>
<article><header class="project-intro"><div class="project-heading"><p class="eyebrow">Project {projects.index(project)+1:02d} / 05</p>
<h1>{e(project['title'])}</h1><p class="lead">{e(project['summary'])}</p>
{bullets(project['tools'], 'tool-list')}<div class="text-links">{link(project['github'], 'GitHub')}</div></div>
{figure(cover, dimensions, True)}</header>
<section class="project-notes section-rule" aria-labelledby="notes-title"><h2 id="notes-title">Project notes</h2><div class="prose">{paragraphs(project['paragraphs'])}</div></section>
{gallery}</article>
<nav class="next-project section-rule" aria-label="Project navigation"><div><span class="eyebrow">Next project</span><h2>{link('/projects/' + next_project['slug'] + '/', next_project['title'])}</h2></div>{link('/#projects', 'All projects')}</nav>'''


def resume_body(resume):
    edu = resume['education']
    education = f'<div class="entry-heading"><h3>{e(edu["school"])}</h3><p>{e(edu["dates"])}</p></div><p>{e(edu["degree"])}<br>{e(edu["location"])}</p>'
    sections = []
    for name, entries in [('Experience', resume['experience']), ('Projects', resume['projects'])]:
        content = ''
        for entry in entries:
            subtitle = f'<p class="organization">{e(entry["organization"])}</p>' if 'organization' in entry else ''
            github = f'<p>{link(entry["github"], "GitHub", aria_label=entry["title"] + " on GitHub")}</p>' if 'github' in entry else ''
            content += f'<article class="resume-entry"><div class="entry-heading"><h3>{e(entry["title"])}</h3><p>{e(entry["dates"])}</p></div>{subtitle}{bullets(entry["bullets"])}{github}</article>'
        sections.append(f'<section class="resume-section section-rule"><h2>{name}</h2><div>{content}</div></section>')
    return f'''<header class="page-heading resume-heading"><div><p class="eyebrow">Resume</p><h1>{e(resume['name'])}</h1><p class="lead">{e(resume['role'])}</p></div>
{link('/resume.pdf', 'Download resume (PDF)', **{'class':'button-link', 'download':'Vraj-Patel-Resume.pdf'})}</header>
<div class="resume-contact text-links">{link('mailto:' + resume['email'], resume['email'])}{link(resume['linkedin'], 'LinkedIn')}{link(resume['github'], 'GitHub')}</div>
<section class="resume-section section-rule"><h2>Education</h2><div>{education}</div></section>
{''.join(sections)}
<section class="resume-section section-rule"><h2>Award</h2><div><h3>{e(resume['award']['title'])}</h3><p>{e(resume['award']['detail'])}</p></div></section>
<section class="resume-section section-rule"><h2>Skills</h2>{bullets(resume['skills'], 'skills-list')}</section>'''


def main():
    global CONTACT, SOCIAL_ALT
    home, CONTACT, resume = read('home'), read('contact'), read('resume')
    project_map = {p['slug']: p for p in [read('project_' + name) for name in ('drone', 'arm', 'hand', 'pedals', 'hybrid')]}
    projects = [project_map[slug] for slug in home['project_order']]
    assert len(projects) == 5
    assert all(re.fullmatch(r'[a-z0-9-]+', p['slug']) for p in projects)
    dimensions = prepare_media()
    used = [m['id'] for p in projects for m in p['media']]
    assert len(used) == len(set(used)) == 15 and set(used) == set(dimensions)
    SOCIAL_ALT = next(m['alt'] for p in projects for m in p['media'] if m['id'] == 'photo_02')
    write('index.html', shell(home['name'] + ' | Engineering portfolio', home['intro'], '/', home_body(home, projects, dimensions), home, CONTACT))
    routes = ['/']
    for project in projects:
        route = '/projects/' + project['slug'] + '/'
        write(route.strip('/') + '/index.html', shell(project['title'] + ' | ' + home['name'], project['summary'], route, project_body(project, projects, dimensions), home, CONTACT))
        routes.append(route)
    contact_body = f'''<header class="page-heading"><p class="eyebrow">{e(home['name'])}</p><h1>{e(CONTACT['title'])}</h1><p class="lead">{e(CONTACT['intro'])}</p></header>
<dl class="contact-list"><div><dt>Email</dt><dd>{link('mailto:' + CONTACT['email'], CONTACT['email'])}</dd></div><div><dt>LinkedIn</dt><dd>{link(CONTACT['linkedin'], 'View LinkedIn profile')}</dd></div><div><dt>GitHub</dt><dd>{link(CONTACT['github'], 'View GitHub profile')}</dd></div></dl>
<div class="text-links contact-resume">{link('/resume/', 'View resume')}{link('/resume.pdf', 'Download resume (PDF)', download='Vraj-Patel-Resume.pdf')}</div>'''
    write('contact/index.html', shell('Contact | ' + home['name'], CONTACT['intro'], '/contact/', contact_body, home, CONTACT, 'Contact'))
    write('resume/index.html', shell('Resume | ' + resume['name'], resume['role'], '/resume/', resume_body(resume), home, CONTACT, 'Resume'))
    write('404.html', shell('Page not found | ' + home['name'], 'This page could not be found.', '/404.html', '<section class="page-heading"><p class="eyebrow">404</p><h1>Page not found</h1><p class="lead">This page could not be found.</p><div class="text-links">' + link('/', 'Return to projects') + link('/contact/', 'Contact') + '</div></section>', home, CONTACT, '', True))
    routes.extend(['/resume/', '/contact/'])
    write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE}{route}</loc></url>\n' for route in routes) + '</urlset>\n')
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')
    build_resume(resume, ROOT)
    print(f'Built {len(routes)} pages, 404, responsive media, metadata and resume.pdf.')


if __name__ == '__main__':
    main()
