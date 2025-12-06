import os
from bs4 import BeautifulSoup

def load_index():
    # Prefer workspace file (index.html) — adapt path if your html is in different dir
    possible = ['index.html', 'dist/index.html', 'public/index.html']
    for p in possible:
        if os.path.exists(p):
            return p
    # nothing found — fail deliberately
    assert False, "index.html not found in repo root or common build dirs"

def test_index_contains_html():
    path = load_index()
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    assert '<html' in content.lower() and '</html>' in content.lower()

def test_index_has_title():
    path = load_index()
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    t = soup.title.string if soup.title else ''
    assert t is not None and len(t.strip()) > 0, "index.html title missing or empty"

def test_index_has_main_content():
    path = load_index()
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    # a lightweight check for some content — change to match your site
    body_text = (soup.body.get_text() if soup.body else '').strip()
    assert len(body_text) > 10, "index.html body seems empty"
