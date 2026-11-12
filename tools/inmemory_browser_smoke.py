"""OPTIONAL offline visual sanity check (Playwright + Chromium required).

IMPORTANT: transforms local ES modules into data: URLs, inlines CSS and REMOVES
THE CSP META ELEMENT in this temporary in-memory test harness. This checks
rendering and client behavior, NOT deployment, headers or actual CSP enforcement.
No localhost server, external network call or real user data is used.
"""
from __future__ import annotations
import base64
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


def in_memory_html() -> str:
    cache: dict[Path, str] = {}
    def module_uri(path: Path) -> str:
        path = path.resolve()
        if path in cache:
            return cache[path]
        code = path.read_text(encoding='utf-8')
        def resolve(match: re.Match[str]) -> str:
            dep = (path.parent / match.group(1)).resolve()
            if not dep.is_relative_to(DOCS):
                raise ValueError('JS module import outside docs blocked')
            return 'from "' + module_uri(dep) + '"'
        code = re.sub(r'from\s+[\'\"](\./[^\'\"]+)[\'\"]', resolve, code)
        uri = 'data:text/javascript;base64,' + base64.b64encode(code.encode()).decode()
        cache[path] = uri
        return uri
    html = (DOCS/'index.html').read_text(encoding='utf-8')
    html = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '', html)
    html = html.replace('<link rel="stylesheet" href="style.css">',
                        '<style>'+(DOCS/'style.css').read_text(encoding='utf-8')+'</style>')
    html = html.replace('<script type="module" src="app.mjs"></script>',
                        '<script type="module" src="'+module_uri(DOCS/'app.mjs')+'"></script>')
    return html


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('NOT_RUN: install optional Playwright separately', file=sys.stderr)
        return 2
    html=in_memory_html()
    chromium_path=shutil.which('chromium') or shutil.which('google-chrome')
    report_dir=ROOT/'reports'; report_dir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, executable_path=chromium_path, args=['--no-sandbox'])
        try:
            for label,w,h in [('desktop',1440,1000),('mobile',390,844)]:
                page=browser.new_page(viewport={'width':w,'height':h},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.set_content(html,wait_until='load'); page.locator('.challenge-cell').first.wait_for()
                if page.locator('.challenge-cell').count() != 100: raise AssertionError('Missing generated controls')
                page.locator('#challenge-run').click()
                if page.locator('#challenge-counter').inner_text()!='100 / 100': raise AssertionError('Challenge result mismatch')
                page.locator('#challenge-context').select_option('sales')
                if page.locator('.challenge-cell').count()!=10: raise AssertionError('Context filter failed')
                page.locator('#challenge-attack').select_option('self-approval')
                if page.locator('.challenge-cell').count()!=1: raise AssertionError('Attack filter failed')
                page.locator('.challenge-cell').first.click()
                if 'NO_SYNTHETIC_HUMAN_APPROVAL' not in page.locator('#challenge-detection').inner_text():
                    raise AssertionError('Self-approval signal absent')
                page.locator('#challenge-context').select_option('all')
                page.locator('#challenge-attack').select_option('all')
                if errors: raise AssertionError('JS page error(s): '+ '; '.join(errors))
                screenshot=report_dir/f'inmemory-challenge-{label}.png'
                page.screenshot(path=str(screenshot),full_page=True)
                print(f'{label}: IN_MEMORY_PASS 100/100, filters, detection, no page errors → {screenshot}')
                page.close()
        finally:
            browser.close()
    print('CSP_NOT_TESTED: in-memory harness explicitly removed CSP; test normal HTTP separately.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
