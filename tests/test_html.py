# tests/test_html.py
import os
from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def all_html_files():
    out = []
    for dirpath, _, filenames in os.walk(ROOT):
        for f in filenames:
            if f.endswith('.html'):
                out.append(os.path.join(dirpath, f))
    return out

def test_at_least_one_html_file():
    files = all_html_files()
    assert len(files) > 0, "No .html files found in repo root or subfolders."

def test_index_has_title_and_h1():
    idx = os.path.join(ROOT, "index.html")
    assert os.path.exists(idx), "index.html not found at repo root."
    with open(idx, encoding='utf-8') as fh:
        html = fh.read()
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    h1 = soup.find('h1')
    assert title != "", "index.html has empty or missing <title>."
    assert h1 is not None, "index.html missing <h1> element."

def test_no_broken_relative_links():
    # Simple check: for every <a href="..."> that is relative (no scheme, no leading //),
    # ensure the target file exists in repo (very basic: ignores anchors and querystrings).
    files = all_html_files()
    file_set = set([os.path.relpath(p, ROOT).replace('\\','/') for p in files])
    for path in files:
        with open(path, encoding='utf-8') as fh:
            soup = BeautifulSoup(fh.read(), "html.parser")
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            # ignore anchors, mails, tel, external, javascript
            if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:') or href.startswith('javascript:'):
                continue
            if '://' in href or href.startswith('//'):
                continue
            # remove query and fragment
            href_clean = href.split('#')[0].split('?')[0].lstrip('./')
            if href_clean == "":
                continue
            # only check for file existence if endswith .html or no extension
            if '.' in os.path.basename(href_clean) and not href_clean.endswith('.html'):
                continue
            # normalize
            target = os.path.normpath(os.path.join(os.path.dirname(path), href_clean))
            if not os.path.exists(target):
                # try relative to repo root
                alt = os.path.normpath(os.path.join(ROOT, href_clean))
                assert os.path.exists(alt), f"Broken relative link in {os.path.relpath(path, ROOT)}: {href}"
