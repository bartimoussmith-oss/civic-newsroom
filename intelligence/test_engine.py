from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import engine

class IntelligenceTests(unittest.TestCase):
    def test_retrieval_spans_candidates_and_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            text='# Synthetic fixture\n\n---\n\nCouncil discussed Ordinance No. 1234. The motion carried.\n\nThe agreement shall require a report. Proposed amount: $12,000. June 25, 2012.'
            record={'id':'fixture-record','title':'Synthetic council record','path':'documents/2012/city-council-2012-06-25/test.md','version':sha256(text.encode()).hexdigest(),'text':text,'source':{'kind':'synthetic_fixture'}}
            out=Path(tmp)/'engine';report=engine.build([record],out,'fixture')
            self.assertEqual(report['records'],1)
            self.assertFalse(report['verified_entity_resolution'])
            results=engine.search(out/'intelligence.sqlite','ordinance 1234')
            self.assertTrue(results)
            match=results[0];span=match['span'];self.assertEqual(match['text'],text[span['start']:span['end']])
            evidence=engine.packet(out/'intelligence.sqlite',[match['passage_id']])
            self.assertEqual(evidence['evidence'][0]['record_version'],record['version'])
            self.assertIsNone(evidence['finding'])
            self.assertGreater(report['reference_mentions'],0);self.assertGreater(report['language_candidates'],0)
            graph=json.loads(next((out/'public/records').glob('*.json')).read_text())
            self.assertTrue(all(x['namespace']=='unresolved' for x in graph['references']))
            self.assertTrue(all(x['review'].startswith('language_candidate') for x in graph['candidates']))
            self.assertEqual(engine.search(out/'intelligence.sqlite','unfindabletoken'),[])
            with self.assertRaises(ValueError):engine.packet(out/'intelligence.sqlite',['unknown'])

if __name__=='__main__':unittest.main()
