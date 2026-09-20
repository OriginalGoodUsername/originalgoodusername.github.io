# Vraj Patel's engineering portfolio

Static site for https://originalgoodusername.github.io. Python 3.10+; no JavaScript, framework, backend, external fonts or build service required.

```sh
python -m pip install -r requirements.txt
python -B build.py
python -B validate.py
python -m http.server 8000
```

Open http://localhost:8000. Run commands from this repository. Generated HTML and assets are served directly from the root by GitHub Pages; preserve `.nojekyll`.

- `content/*.json`: authoritative public text. Edit these to update copy, captions, contacts and resume content.
- `build.py`: shared HTML generation, metadata, sitemap and responsive image sizes.
- `styles.css`: responsive layout and typography.
- `media/photo_01.webp` through `photo_15.webp`: full-frame image masters. Keep these with the source; the build derives smaller WebP variants without cropping or upscaling. `social.jpg` is derived from the actual drone photograph.
- `resume_pdf.py`: one-page PDF layout using only `content/resume.json` for applicant text. It fails if the content cannot fit at 9 pt or larger; it never drops text.
- `build_resources/resume-base.pdf`: blank letter-size template containing embedded Arial regular and bold fonts. This is a build resource, not a resume or preview; it removes any dependency on installed fonts.
- `validate.py`: checks local links, metadata, images and PDF content/size.

Rebuilding uses only repository files and the pinned Python dependencies. Original JPGs are not needed. Generated routes preserve `/projects/quadcopter/`, `/projects/robotic-arm/`, `/projects/robotic-hand/`, `/projects/pedal-pcbs/` and `/projects/spider-robot/`, plus `/resume/` and `/contact/`. `/resume.pdf` is the current download. GitHub Pages serves `404.html` for unknown routes; Python's basic preview server uses its own error response.
