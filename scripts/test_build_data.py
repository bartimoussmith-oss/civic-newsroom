from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import build_data

class PartitionTests(unittest.TestCase):
    def test_roundtrip_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);mirror=root/'mirror';out=root/'out'
            (mirror/'documents').mkdir(parents=True)
            (mirror/'llms.txt').write_text('Synthetic public fixture')
            raw=('# Water fixture\n'+'multibyte café water '*800).encode()
            for name in ('one.md','two.md'): (mirror/'documents'/name).write_bytes(raw)
            result=build_data.build(mirror,out,'fixture',True,budget=8192,chunk=1024)
            self.assertEqual(result['records'],2)
            records=json.loads((out/result['catalogs'][0]['path']).read_text())
            self.assertNotEqual(records[0]['record_id'],records[1]['record_id'])
            for r in records:
                assembled=b''.join((out/p['path']).read_bytes() for p in r['representation']['parts'])
                self.assertEqual(assembled,raw)
                self.assertEqual(sha256(assembled).hexdigest(),r['representation']['sha256'])
            self.assertLess(result['stored_unique_blob_bytes'],result['input_representation_bytes'])
            self.assertTrue(all(p['total_bytes']<=8192 for p in result['partitions']))
            self.assertFalse(result['full_historical_coverage'])
            with self.assertRaises(ValueError): build_data.build(mirror,out,'fixture',True)

if __name__=='__main__': unittest.main()
