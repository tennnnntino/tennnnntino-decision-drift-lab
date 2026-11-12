import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PublicationContractTests(unittest.TestCase):
    def test_browser_no_third_party_network_import(self):
        html=(ROOT/'docs'/'index.html').read_text(encoding='utf-8')
        js=(ROOT/'docs'/'app.mjs').read_text(encoding='utf-8')
        self.assertIn("connect-src 'none'",html)
        self.assertNotIn('https://',html)
        self.assertNotIn('fetch(',js)
        self.assertNotIn('XMLHttpRequest',js)

    def test_technology_radar_has_10_explicit_decisions(self):
        radar=json.loads((ROOT/'docs'/'technology-radar.json').read_text(encoding='utf-8'))
        self.assertEqual(len(radar['items']),10)
        self.assertEqual({x['ring'] for x in radar['items']},{'ADOPT','TRIAL','ASSESS','HOLD'})

    def test_public_review_has_exact_20_lenses(self):
        rows=(ROOT/'docs'/'ENGINEERING_LENSES.md').read_text(encoding='utf-8')
        for i in range(1,21):
            self.assertIn(f'| E{i:02} |',rows)
        self.assertNotIn('| E21 |',rows)

    def test_20_lens_review_is_honest(self):
        review=json.loads((ROOT/'docs'/'engineering-review.json').read_text(encoding='utf-8'))
        self.assertEqual(len(review['items']),20)
        self.assertEqual(sum(x['status']=='PASS' for x in review['items']),10)
        self.assertEqual(sum(x['status']=='FAIL' for x in review['items']),3)

    def test_all_demo_cases_stated_synthetic(self):
        for file in (ROOT/'examples').glob('*.json'):
            text=file.read_text(encoding='utf-8')
            self.assertIn('synthetic://',text,file.name)
