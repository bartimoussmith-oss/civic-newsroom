"""Evidence retrieval and explicitly unreviewed analytical candidates for public records."""
import argparse
from collections import defaultdict
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sqlite3

REF=re.compile(r'\b(ordinance|resolution|contract|PUDC)\s*(?:no\.?\s*|#\s*|-)?(\d[A-Za-z0-9]*(?:[-.]\d[A-Za-z0-9]*)*)\b',re.I)
PATTERNS={'decision_language':re.compile(r'\b(?:motion carried|motion failed|approved|adopted|postponed|referred to)\b',re.I),'commitment_language':re.compile(r'\b(?:will|shall|must|required to|agrees? to)\b',re.I),'amount_mention':re.compile(r'\$[0-9][0-9,]*(?:\.[0-9]{2})?'),'date_mention':re.compile(r'\b(?:\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December) +\d{1,2},? +\d{4})\b',re.I)}

def words(text):return sorted({w for w in re.findall(r'[^\W_]+',text.lower()) if 3<=len(w)<=80})
def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
def local(root,p):
    f=(root/p).resolve()
    if root not in f.parents or not f.is_file():raise ValueError('Invalid dataset path')
    return f.read_bytes()

def load(repo):
    repo=Path(repo).resolve();p=json.loads((repo/'published.json').read_text())
    if not re.fullmatch('build-[0-9]+',p['dataset_version']):raise ValueError('Invalid version')
    root=(repo/'datasets'/p['dataset_version']).resolve();raw=local(root,'collection.json')
    if sha256(raw).hexdigest()!=p['manifest_sha256']:raise ValueError('Manifest changed')
    m=json.loads(raw);count=0
    for c in m['catalogs']:
        raw=local(root,c['path'])
        if len(raw)!=c['bytes'] or sha256(raw).hexdigest()!=c['sha256']:raise ValueError('Catalog changed')
        for r in json.loads(raw):
            if not r['source']['mirror_path'].startswith(('documents/','meetings/')):raise ValueError('Unapproved source path')
            parts=[]
            for i,part in enumerate(r['representation']['parts']):
                b=local(root,part['path'])
                if i!=part['sequence'] or len(b)!=part['bytes'] or sha256(b).hexdigest()!=part['sha256']:raise ValueError('Blob changed')
                parts.append(b)
            raw=b''.join(parts)
            if len(raw)!=r['representation']['bytes'] or sha256(raw).hexdigest()!=r['representation']['sha256']:raise ValueError('Record changed')
            count+=1
            yield {'id':r['record_id'],'title':r['title'],'path':r['source']['mirror_path'],'version':r['representation']['sha256'],'text':raw.decode('utf-8'),'source':r['source'],'dataset_revision':p['dataset_revision']}
    if count!=m['records']:raise ValueError('Incomplete collection')

def build(records,out,revision):
    out=Path(out)
    if out.exists():raise ValueError('Fresh output directory required')
    out.mkdir(parents=True);public=out/'public';public.mkdir();(public/'search').mkdir();(public/'records').mkdir()
    db=sqlite3.connect(out/'intelligence.sqlite')
    db.executescript('CREATE TABLE records(id TEXT PRIMARY KEY,title TEXT,path TEXT,version TEXT,text TEXT,date_label TEXT,source TEXT); CREATE TABLE passages(pid TEXT UNIQUE,record_id TEXT,start INTEGER,end INTEGER,section TEXT,text_family TEXT); CREATE VIRTUAL TABLE fts USING fts5(title,text,content=""); CREATE TABLE mentions(record_id TEXT,pid TEXT,kind TEXT,value TEXT,start INTEGER,end INTEGER,review TEXT); CREATE TABLE candidates(record_id TEXT,pid TEXT,kind TEXT,literal TEXT,start INTEGER,end INTEGER,review TEXT); CREATE INDEX reference_lookup ON mentions(kind,value); CREATE INDEX record_passages ON passages(record_id);')
    postings=defaultdict(list);families=defaultdict(list);summaries=[];passage_count=0;reference_count=0;candidate_count=0
    streams={k:gzip.open(public/(k+'.jsonl.gz'),'wt',encoding='utf-8') for k in ('passages','references','candidates')}
    try:
        for sequence,r in enumerate(records):
            if sha256(r['text'].encode('utf-8')).hexdigest()!=r['version']:raise ValueError('Input text/hash mismatch')
            date=re.search(r'\b\d{4}-\d{2}-\d{2}\b',r['path']);label=date.group() if date else None
            db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',(r['id'],r['title'],r['path'],r['version'],r['text'],label,json.dumps(r.get('source',{}))))
            for word in words(r['text']):postings[word].append(sequence)
            refs=[];events=[];separator=r['text'].find('\n---\n')
            for match in re.finditer(r'\S[\s\S]*?(?=\n[ \t]*\n|\Z)',r['text']):
                start,end=match.span();text=match.group();pid=sha256((r['id']+r['version']+str(start)+':'+str(end)).encode()).hexdigest()
                section='wrapper' if separator>=0 and start<separator else ('body' if separator>=0 else 'unclassified')
                family=sha256(re.sub(r'\s+',' ',text).strip().encode()).hexdigest();families[family].append(pid)
                cursor=db.execute('INSERT INTO passages VALUES(?,?,?,?,?,?)',(pid,r['id'],start,end,section,family))
                db.execute('INSERT INTO fts(rowid,title,text) VALUES(?,?,?)',(cursor.lastrowid,r['title'],text));passage_count+=1
                evidence={'passage_id':pid,'record_id':r['id'],'record_version':r['version'],'span':{'start':start,'end':end,'unit':'unicode_code_points'},'section':section,'text':text,'source_path':r['path'],'review':'unreviewed_source_passage'}
                streams['passages'].write(json.dumps(evidence,ensure_ascii=False)+'\n')
                if section=='wrapper':continue
                for ref in REF.finditer(text):
                    a,b=start+ref.start(),start+ref.end();kind=ref.group(1).lower();value=ref.group(2).lower()
                    edge={'record_id':r['id'],'record_version':r['version'],'passage_id':pid,'predicate':'mentions_identifier','kind':kind,'value':value,'literal':ref.group(),'span':{'start':a,'end':b,'unit':'unicode_code_points'},'namespace':'unresolved','review':'literal_candidate_not_verified_entity_link'}
                    refs.append(edge);streams['references'].write(json.dumps(edge,ensure_ascii=False)+'\n');reference_count+=1
                    db.execute('INSERT INTO mentions VALUES(?,?,?,?,?,?,?)',(r['id'],pid,kind,value,a,b,edge['review']))
                for kind,pattern in PATTERNS.items():
                    for candidate in pattern.finditer(text):
                        a,b=start+candidate.start(),start+candidate.end()
                        event={'record_id':r['id'],'record_version':r['version'],'passage_id':pid,'kind':kind,'literal':candidate.group(),'span':{'start':a,'end':b,'unit':'unicode_code_points'},'date_label':label,'date_status':'unverified_source_path','review':'language_candidate_not_verified_event_or_obligation'}
                        events.append(event);streams['candidates'].write(json.dumps(event,ensure_ascii=False)+'\n');candidate_count+=1
                        db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,?,?)',(r['id'],pid,kind,event['literal'],a,b,event['review']))
            graph_file=sha256(r['id'].encode()).hexdigest()+'.json'
            dump(public/'records'/graph_file,{'record_id':r['id'],'version':r['version'],'references':refs,'candidates':events,'review':'unreviewed','original_binary_identity':'not_established'})
            summaries.append({'id':r['id'],'title':r['title'],'path':r['path'],'version':r['version'],'date_label':label,'date_status':'unverified_source_path','graph_path':'records/'+graph_file})
        db.commit()
    finally:
        for stream in streams.values():stream.close()
        db.close()
    buckets=defaultdict(dict)
    for word,ids in postings.items():buckets[sha256(word.encode()).hexdigest()[:2]][word]=ids
    for bucket,value in buckets.items():dump(public/'search'/(bucket+'.json'),value)
    dump(public/'records.json',summaries)
    dump(public/'text-families.json',{k:v for k,v in families.items() if len(v)>1})
    with (out/'intelligence.sqlite').open('rb') as src,gzip.open(out/'database.sqlite.gz','wb') as dest:shutil.copyfileobj(src,dest)
    parts=[]
    with (out/'database.sqlite.gz').open('rb') as stream:
        while True:
            raw=stream.read(40*1024*1024)
            if not raw:break
            name='database-'+str(len(parts)+1).zfill(4)+'.part';(public/name).write_bytes(raw);parts.append({'path':name,'sha256':sha256(raw).hexdigest(),'bytes':len(raw)})
    report={'schema':'civic-intelligence-v1','producer_revision':revision,'records':len(summaries),'passages':passage_count,'reference_mentions':reference_count,'language_candidates':candidate_count,'search':'SQLite FTS5 passage BM25 plus static document token index','static_search_limits':{'minimum_token_characters':3,'maximum_token_characters':80,'posting_values':'indexes into records.json'},'semantic_search':False,'verified_entity_resolution':False,'verified_decision_timeline':False,'source_independence':'unresolved; exact-text families are not independent-source certification','database_parts':parts,'database_assembly':'concatenate parts, decompress gzip, open SQLite','span_units':'zero-based Unicode code points; end exclusive','record_status':'generated_public_representations_not_independently_verified'}
    dump(public/'collection.json',report)
    if any(f.stat().st_size>45*1024*1024 for f in public.rglob('*') if f.is_file()):raise ValueError('Intelligence file needs further partitioning')
    if sum(f.stat().st_size for f in public.rglob('*') if f.is_file())>256*1024*1024:raise ValueError('Intelligence output exceeds partition budget')
    return report

def search(path,query,limit=10):
    tokens=words(query)
    if not tokens:return []
    expression=' AND '.join('"'+t.replace('"','""')+'"' for t in tokens)
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    try:
        matches=db.execute('SELECT p.pid,p.record_id,p.start,p.end,p.section,bm25(fts) AS score FROM fts JOIN passages p ON p.rowid=fts.rowid WHERE fts MATCH ? ORDER BY score LIMIT ?',(expression,max(1,min(int(limit),50)))).fetchall()
        results=[]
        for m in matches:
            r=db.execute('SELECT * FROM records WHERE id=?',(m['record_id'],)).fetchone()
            results.append({'passage_id':m['pid'],'record_id':r['id'],'record_version':r['version'],'title':r['title'],'source_path':r['path'],'span':{'start':m['start'],'end':m['end'],'unit':'unicode_code_points'},'text':r['text'][m['start']:m['end']],'section':m['section'],'score':m['score'],'score_kind':'FTS5_BM25_not_factual_confidence'})
        return results
    finally:db.close()

def packet(path,ids):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row;items=[]
    try:
        for pid in ids:
            p=db.execute('SELECT * FROM passages WHERE pid=?',(pid,)).fetchone()
            if p is None:raise ValueError('Unknown passage ID')
            r=db.execute('SELECT * FROM records WHERE id=?',(p['record_id'],)).fetchone()
            items.append({'passage_id':pid,'record_id':r['id'],'record_version':r['version'],'source':json.loads(r['source']),'source_path':r['path'],'span':{'start':p['start'],'end':p['end'],'unit':'unicode_code_points'},'text':r['text'][p['start']:p['end']],'review':'unreviewed'})
        return {'schema':'intelligence-evidence-packet-v1','evidence':items,'finding':None,'limitations':'Selected source passages only; no automatic factual or legal conclusion. Check originals, context, dates, independence and later developments.'}
    finally:db.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();commands=p.add_subparsers(dest='command',required=True)
    b=commands.add_parser('build');b.add_argument('--dataset-repo',required=True);b.add_argument('--out',required=True);b.add_argument('--revision',required=True)
    s=commands.add_parser('search');s.add_argument('--db',required=True);s.add_argument('--query',required=True);s.add_argument('--limit',type=int,default=10)
    e=commands.add_parser('packet');e.add_argument('--db',required=True);e.add_argument('--passage-id',action='append',required=True)
    a=p.parse_args()
    result=build(load(a.dataset_repo),a.out,a.revision) if a.command=='build' else (search(a.db,a.query,a.limit) if a.command=='search' else packet(a.db,a.passage_id))
    print(json.dumps(result,ensure_ascii=False,indent=2))
