"""One-page, selectable Arial resume. Applicant text comes only from resume.json."""
import json
import pymupdf

INK = (0.13, 0.16, 0.15)
TEAL = (0.13, 0.40, 0.37)


def build_resume(data, root):
    # The blank template embeds Arial regular and bold: no system font dependency.
    template = root / 'build_resources/resume-base.pdf'
    for size in (10.5, 10.25, 10, 9.75, 9.5, 9.25, 9):
        doc = pymupdf.open(template)
        page = doc[0]
        fonts = {f[4]: pymupdf.Font(fontbuffer=doc.extract_font(f[0])[3]) for f in page.get_fonts()}
        y = 34.0
        left, right = 36, 576
        line_height = size * 1.23

        def text(value, x=left, font='Arial', pt=None, color=INK, width=None, after=0):
            nonlocal y
            pt = pt or size
            width = width or right - x
            lines, current = [], ''
            for word in value.split():
                test = (current + ' ' + word).strip()
                if fonts[font].text_length(test, fontsize=pt) > width and current:
                    lines.append(current)
                    current = word
                else:
                    current = test
            if current:
                lines.append(current)
            for line in lines:
                y += pt
                page.insert_text((x, y), line, fontname=font, fontsize=pt, color=color)
                y += pt * .23
            y += after

        def section(label):
            nonlocal y
            y += 9
            text(label.upper(), font='ArialBold', pt=size + .5, color=TEAL, after=4)
            page.draw_line((left, y - 2), (right, y - 2), color=(.72, .75, .73), width=.45)

        def heading(title, dates, url=None):
            nonlocal y
            date_width = fonts['Arial'].text_length(dates, fontsize=size)
            baseline = y + size
            text(title, font='ArialBold', width=right-left-date_width-18)
            if dates:
                page.insert_text((right-date_width, baseline), dates, fontname='Arial', fontsize=size, color=INK)
            if url:
                title_width = min(fonts['ArialBold'].text_length(title, fontsize=size), right-left-date_width-18)
                page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(left, baseline-size, left+title_width, baseline+2), 'uri': url})

        def bullet(value):
            nonlocal y
            page.insert_text((left + 2, y + size), '•', fontname='Arial', fontsize=size, color=INK)
            text(value, x=left+11, after=1.5)

        text(data['name'], font='ArialBold', pt=23, after=1)
        text(data['role'], pt=10.5, after=4)
        contact = [(data['email'], 'mailto:' + data['email']), ('LinkedIn', data['linkedin']), ('GitHub', data['github'])]
        x = left
        for label, url in contact:
            width = fonts['Arial'].text_length(label, fontsize=size)
            page.insert_text((x, y + size), label, fontname='Arial', fontsize=size, color=TEAL)
            page.insert_link({'kind': pymupdf.LINK_URI, 'from': pymupdf.Rect(x, y, x+width, y+line_height), 'uri': url})
            x += width + 19
        y += line_height
        section('Education')
        edu = data['education']
        heading(edu['school'], edu['dates'])
        text(edu['degree'] + ' | ' + edu['location'])
        for label, entries in [('Experience', data['experience']), ('Projects', data['projects'])]:
            section(label)
            for index, entry in enumerate(entries):
                if index:
                    y += 5
                heading(entry['title'], entry['dates'], entry.get('github'))
                if 'organization' in entry:
                    text(entry['organization'], after=2)
                for item in entry['bullets']:
                    bullet(item)
        section('Award')
        text(data['award']['title'], font='ArialBold')
        text(data['award']['detail'])
        section('Skills')
        for skill in data['skills']:
            text(skill)
        if y <= 760:
            doc.set_metadata({'title': data['name'] + ' | Engineering resume', 'author': data['name'], 'subject': data['role'], 'creator': 'Portfolio static generator'})
            # Arial shares glyphs for space/NBSP, hyphen/soft hyphen and
            # semicolon/Greek question mark. Map glyphs back to the actual
            # source characters so copy/paste and text extraction stay exact.
            chars = set(json.dumps(data, ensure_ascii=False)) | set(chr(i) for i in range(32, 127)) | {'•'}
            chars -= {'\n', '\r', '\t'}
            for font in page.get_fonts():
                metrics = fonts[font[4]]
                mapping = {metrics.has_glyph(ord(c)): c.encode('utf-16-be').hex() for c in sorted(chars)}
                mapping.pop(0, None)
                pairs = [f'<{gid:04x}> <{unicode}>' for gid, unicode in sorted(mapping.items())]
                cmap = '/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo <</Registry (Adobe) /Ordering (UCS) /Supplement 0>> def\n/CMapName /ArialSourceText def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n'
                for start in range(0, len(pairs), 100):
                    chunk = pairs[start:start+100]
                    cmap += f'{len(chunk)} beginbfchar\n' + '\n'.join(chunk) + '\nendbfchar\n'
                cmap += 'endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n'
                xref = int(doc.xref_get_key(font[0], 'ToUnicode')[1].split()[0])
                doc.update_stream(xref, cmap.encode('ascii'))
            doc.subset_fonts()
            doc.save(root / 'resume.pdf', garbage=4, deflate=True, no_new_id=True)
            print(f'Resume: one page, {size:g} pt Arial body, content bottom {y:.1f} / 792 pt.')
            doc.close()
            return
        doc.close()
    raise ValueError('Resume exceeds one page at 9 pt. Edit resume.json; no text has been omitted.')
