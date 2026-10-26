"""Normalize an approved public mirror into content-addressed, bounded partitions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

CHUNK=512*1024
BUDGET=256*1024*1024

def dump(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def build(mirror,out,producer_revision,approved_public=False,budget=BUDGET,chunk=CHUNK):
    if not approved_public: raise ValueError('Approved public input required')
    mirror,out=Path(mirror).resolve(),Path(out).resolve()
    if not (mirror/'llms.txt').is_file(): raise ValueError('Expected generated public mirror')
    if mirror==out or mirror in out.parents or out in mirror.parents: raise ValueError('Separate input/output required')
    if out.exists() and any(out.iterdir()): raise ValueError('Fresh output required')
    if chunk<1 or budget<chunk+4096: raise ValueError('Invalid size budget')
    out.mkdir(parents=True,exist_ok=True)
    partitions=[];blobs={};records=[];excluded=[];current=None;stored=0;input_bytes=0;count=0
    def put(payload):
        nonlocal current,stored
        digest=sha256(payload).hexdigest()
        if digest in blobs: return blobs[digest]
        if current is None or current['payload_bytes']+len(payload)>budget-4096:
            pid='partition-'+str(len(partitions)+1).zfill(3)
            (out/pid/'blobs').mkdir(parents=True)
            current={'id':pid,'payload_bytes':0,'blob_count':0}
            partitions.append(current)
        rel=current['id']+'/blobs/'+digest+'.bin'
        (out/rel).write_bytes(payload)
        current['payload_bytes']+=len(payload);current['blob_count']+=1;stored+=len(payload)
        blobs[digest]={'path':rel,'sha256':digest,'bytes':len(payload)}
        return blobs[digest]
    catalogs=[]
    def flush():
        if not records: return
        name='catalog-'+str(len(catalogs)+1).zfill(4)+'.json'
        dump(out/name,records)
        raw=(out/name).read_bytes()
        if len(raw)>40*1024*1024: raise ValueError('Catalog file too large; decrease batch size')
        catalogs.append({'path':name,'sha256':sha256(raw).hexdigest(),'bytes':len(raw),'records':len(records)})
        records.clear()
    for file in sorted(mirror.rglob('*.md')):
        rel=file.relative_to(mirror).as_posix()
        if file.is_symlink() or any(p.is_symlink() for p in file.parents if p!=mirror and mirror in p.parents):
            excluded.append({'path':rel,'reason':'symlink'});continue
        if not rel.startswith(('documents/','meetings/')):
            excluded.append({'path':rel,'reason':'outside approved record paths'});continue
        raw=file.read_bytes()
        try: text=raw.decode('utf-8')
        except UnicodeDecodeError:
            excluded.append({'path':rel,'reason':'invalid UTF-8'});continue
        parts=[dict(put(raw[i:i+chunk]),sequence=i//chunk) for i in range(0,len(raw),chunk)]
        identity='bartimoussmith-oss/therealwindycity:public-mirror:'+rel
        title=re.search(r'^#\s+(.+)',text,re.M)
        records.append({'schema':'civic-record-v1','record_id':sha256(identity.encode()).hexdigest(),'title':title.group(1)[:1000] if title else rel,'source':{'producer_repository':'bartimoussmith-oss/therealwindycity','producer_revision':producer_revision,'mirror_path':rel,'original_binary_identity':'not_established'},'representation':{'kind':'generated_public_markdown','sha256':sha256(raw).hexdigest(),'bytes':len(raw),'parts':parts,'encoding':'utf-8','assembly':'concatenate raw bytes in sequence, verify complete SHA-256, then decode UTF-8'},'source_family':'unresolved','publication_review':'not_independently_reviewed_in_this_build'})
        count+=1;input_bytes+=len(raw)
        if len(records)>=256: flush()
    flush()
    if count==0: raise ValueError('No eligible records')
    for part in partitions:
        dump(out/part['id']/'partition.json',part)
        part['total_bytes']=sum(f.stat().st_size for f in (out/part['id']).rglob('*') if f.is_file())
        if part['total_bytes']>budget: raise ValueError('Partition over budget')
    manifest={'schema':'civic-data-collection-v1','producer_revision':producer_revision,'records':count,'catalogs':catalogs,'partitions':partitions,'input_representation_bytes':input_bytes,'stored_unique_blob_bytes':stored,'unique_blobs':len(blobs),'excluded':excluded,'coverage':'Eligible Markdown representations in supplied public mirror only; upstream original/PDF/OCR coverage not established','full_historical_coverage':False,'publication_status':'review_artifact_not_published','data_hosts':[],'limits':{'partition_bytes':budget,'blob_bytes':chunk}}
    dump(out/'collection.json',manifest)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mirror',required=True);p.add_argument('--out',required=True);p.add_argument('--producer-revision',required=True);p.add_argument('--approved-public',action='store_true');a=p.parse_args()
    print(json.dumps(build(a.mirror,a.out,a.producer_revision,a.approved_public),indent=2))
