"""Lossless logical-file packaging; preserves source records and all derived content."""
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import engine

def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def pack(root,chunk_size=40*1024*1024,compress_threshold=1024*1024):
    root=Path(root);manifest_path=root/'files.json'
    if manifest_path.exists() or (root/'parts').exists():raise ValueError('Fresh logical-file package required')
    files=[p for p in sorted(root.rglob('*')) if p.is_file() and p.name!='collection.json']
    (root/'parts').mkdir();mapping={};logical_bytes=0
    for file in files:
        if file.is_symlink():raise ValueError('Unexpected output symlink')
        name=file.relative_to(root).as_posix();raw=file.read_bytes();encoded=raw;encoding='identity'
        if name.endswith('.json') and len(raw)>=compress_threshold:
            compressed=gzip.compress(raw,compresslevel=6,mtime=0)
            if len(compressed)<len(raw):encoded=compressed;encoding='gzip'
        parts=[]
        if encoding=='identity' and len(encoded)<=chunk_size:
            parts=[{'path':name,'bytes':len(encoded),'sha256':sha256(encoded).hexdigest()}]
        else:
            for start in range(0,len(encoded),chunk_size):
                part=encoded[start:start+chunk_size];digest=sha256(part).hexdigest();relative='parts/'+digest+'.part';target=root/relative
                if target.exists():
                    if target.read_bytes()!=part:raise ValueError('Part identity collision')
                else:target.write_bytes(part)
                parts.append({'path':relative,'bytes':len(part),'sha256':digest})
            # Only newly generated derived files are replaced; no source repository is touched.
            file.unlink()
        mapping[name]={'decoded_bytes':len(raw),'decoded_sha256':sha256(raw).hexdigest(),'encoded_bytes':len(encoded),'encoded_sha256':sha256(encoded).hexdigest(),'encoding':encoding,'parts':parts}
        logical_bytes+=len(raw)
    manifest={'schema':'intelligence-files-v1','files':mapping,'assembly':'verify parts, concatenate encoded bytes, verify encoded hash, decode gzip if specified, verify decoded hash'}
    dump(manifest_path,manifest)
    total=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    return {'path':'files.json','sha256':sha256(manifest_path.read_bytes()).hexdigest(),'logical_files':len(mapping),'logical_bytes':logical_bytes,'stored_bytes_before_collection_update':total,'maximum_part_bytes':chunk_size}

def reconstruct(root,manifest,name):
    root=Path(root).resolve();item=manifest['files'][name];chunks=[]
    for part in item['parts']:
        file=(root/part['path']).resolve()
        if root not in file.parents:raise ValueError('Escaping part path')
        raw=file.read_bytes()
        if len(raw)!=part['bytes'] or sha256(raw).hexdigest()!=part['sha256']:raise ValueError('Part integrity failure')
        chunks.append(raw)
    encoded=b''.join(chunks)
    if len(encoded)!=item['encoded_bytes'] or sha256(encoded).hexdigest()!=item['encoded_sha256']:raise ValueError('Encoded integrity failure')
    raw=gzip.decompress(encoded) if item['encoding']=='gzip' else encoded
    if len(raw)!=item['decoded_bytes'] or sha256(raw).hexdigest()!=item['decoded_sha256']:raise ValueError('Decoded integrity failure')
    return raw

def build_release(dataset,out,revision):
    out=Path(out);recovered_guard=None
    try:engine.build(engine.load(dataset),out,revision)
    except ValueError as error:
        allowed=('Intelligence file needs further partitioning','Intelligence output exceeds partition budget')
        if str(error) not in allowed or not (out/'public/collection.json').is_file():raise
        recovered_guard=str(error)
    public=out/'public';report=json.loads((public/'collection.json').read_text(encoding='utf-8'))
    with sqlite3.connect(out/'intelligence.sqlite') as db:
        if db.execute('SELECT count(*) FROM records').fetchone()[0]!=report['records']:raise ValueError('Incomplete build; packaging refused')
    report['file_manifest']=pack(public)
    report['packaging_note']='Logical content retained exactly; only generated storage encodings changed.'
    report['previous_size_guard']=recovered_guard
    dump(public/'collection.json',report)
    manifest=json.loads((public/'files.json').read_text(encoding='utf-8'))
    for name in manifest['files']:reconstruct(public,manifest,name)
    total=sum(p.stat().st_size for p in public.rglob('*') if p.is_file())
    largest=sorted(((p.stat().st_size,p.relative_to(public).as_posix()) for p in public.rglob('*') if p.is_file()),reverse=True)[:5]
    if any(size>45*1024*1024 for size,name in largest):raise ValueError('Physical file still exceeds 45 MiB: '+str(largest))
    if total>256*1024*1024:raise ValueError('Packed intelligence needs additional approved host: '+str(total)+' bytes; largest files '+str(largest))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-repo',required=True);p.add_argument('--out',required=True);p.add_argument('--revision',required=True);a=p.parse_args()
    try:print(json.dumps(build_release(a.dataset_repo,a.out,a.revision),indent=2))
    except Exception as error:
        print('::error file=intelligence/file_parts.py::'+type(error).__name__+': '+str(error).replace('\n',' ')[:1500])
        raise
