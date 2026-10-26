import gzip
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
import file_parts

class FilePartTests(unittest.TestCase):
    def test_lossless_json_and_binary_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original={'large.json':json.dumps({'values':['Ordinance 1234 café']*3000},ensure_ascii=False).encode(),'payload.jsonl.gz':gzip.compress(bytes(range(256))*1000,mtime=0),'uncompressed.bin':bytes(range(256))*100,'small.json':b'{"count":1}'}
            for name,raw in original.items():(root/name).write_bytes(raw)
            result=file_parts.pack(root,chunk_size=4096,compress_threshold=512)
            manifest=json.loads((root/'files.json').read_text())
            self.assertEqual(result['logical_files'],len(original))
            for name,raw in original.items():
                self.assertEqual(file_parts.reconstruct(root,manifest,name),raw)
                self.assertEqual(manifest['files'][name]['decoded_sha256'],sha256(raw).hexdigest())
            self.assertEqual(manifest['files']['large.json']['encoding'],'gzip')
            self.assertTrue(all(p.stat().st_size<=4096 for p in (root/'parts').glob('*')))
            part=root/manifest['files']['uncompressed.bin']['parts'][0]['path'];part.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):file_parts.reconstruct(root,manifest,'uncompressed.bin')
            with self.assertRaises(ValueError):file_parts.pack(root)

if __name__=='__main__':unittest.main()
