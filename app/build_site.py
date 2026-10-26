import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil

RULES={'land-use':('Land use and development',r'\b(?:annex\w*|zon(?:e|ing)|subdivision|land use)\b'),'water':('Water and wastewater',r'\b(?:water|wastewater|sewer|reclamation)\b'),'money':('Budgets and public money',r'\b(?:budget|appropriat\w*|expenditure|funding|grant)\b'),'contracts':('Contracts and procurement',r'\b(?:contract|procurement|bid|sole.source)\b'),'roads':('Roads and transportation',r'\b(?:road|street|traffic|transit|roundabout|sidewalk)\b'),'environment':('Environment and waste',r'\b(?:landfill|contamin\w*|recycl\w*|drainage|flood|stormwater)\b'),'process':('Public participation and procedure',r'\b(?:public comment|public hearing|referendum|petition|executive session)\b'),'housing':('Housing and neighborhoods',r'\b(?:housing|residential|neighborhood|affordable)\b'),'safety':('Public safety policy',r'\b(?:police|fire department|fire rescue|emergency services)\b'),'parks':('Parks and recreation',r'\b(?:parks?|recreation|greenway|trails?)\b'),'development':('Economic development',r'\b(?:economic development|business park|data.center|LEADS)\b'),'utilities':('Utilities and franchises',r'\b(?:electricity|franchise|utility|utilities|gas service)\b')}
IDENT=re.compile(r'\b(ordinance|resolution|contract|PUDC)\s*(?:no\.?\s*|#\s*|-)?(\d[A-Za-z0-9]*(?:[-.]\d[A-Za-z0-9]*)*)\b',re.I)

def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def read(root,relative):
    path=(root/relative).resolve()
    if root not in path.parents or not path.is_file():raise ValueError('Invalid dataset path')
    return path.read_bytes()

def build(repo,out,revision):
    repo=Path(repo).resolve();out=Path(out)
    pointer=json.loads((repo/'published.json').read_text())
    if pointer['schema']!='civic-data-publication-v1' or not re.fullmatch('[a-f0-9]{40}',pointer['dataset_revision']):raise ValueError('Invalid publication pointer')
    if not re.fullmatch('build-[0-9]+',pointer['dataset_version']):raise ValueError('Invalid version')
    root=(repo/'datasets'/pointer['dataset_version']).resolve()
    prefix='https://raw.githubusercontent.com/bartimoussmith-oss/civic-newsroom-data-001/'+pointer['dataset_revision']+'/datasets/'+pointer['dataset_version']+'/'
    if pointer['data_base_url']!=prefix or pointer['manifest_url']!=prefix+'collection.json':raise ValueError('Unexpected data host')
    raw=read(root,'collection.json')
    if sha256(raw).hexdigest()!=pointer['manifest_sha256']:raise ValueError('Manifest hash mismatch')
    manifest=json.loads(raw);records=[];topics={};catalogs=[];unassigned=[]
    compiled={k:(v[0],re.compile(v[1],re.I)) for k,v in RULES.items()}
    for index,c in enumerate(manifest['catalogs']):
        raw=read(root,c['path'])
        if len(raw)!=c['bytes'] or sha256(raw).hexdigest()!=c['sha256']:raise ValueError('Catalog hash mismatch')
        catalog=json.loads(raw)
        if len(catalog)!=c['records']:raise ValueError('Catalog count mismatch')
        catalogs.append(dict(c,url=prefix+c['path']))
        for r in catalog:
            payload=[]
            for seq,p in enumerate(r['representation']['parts']):
                b=read(root,p['path'])
                if p['sequence']!=seq or len(b)!=p['bytes'] or sha256(b).hexdigest()!=p['sha256']:raise ValueError('Blob mismatch')
                payload.append(b)
            raw=b''.join(payload)
            if len(raw)!=r['representation']['bytes'] or sha256(raw).hexdigest()!=r['representation']['sha256']:raise ValueError('Record mismatch')
            text=raw.decode('utf-8');lines=text.splitlines();memberships=[]
            for key,(title,rx) in compiled.items():
                positions=[i+1 for i,line in enumerate(lines) if rx.search(line)]
                if positions:
                    topics.setdefault(key,{'title':title,'kind':'reporting_desk','members':[]})['members'].append({'id':r['record_id'],'lines':positions});memberships.append(key)
            for kind,number in sorted({(m.group(1).lower(),m.group(2).lower()) for m in IDENT.finditer(text)}):
                key=kind+':'+number
                rx=re.compile(r'\b'+re.escape(kind)+r'\s*(?:no\.?\s*|#\s*|-)?'+re.escape(number)+r'\b',re.I)
                positions=[i+1 for i,line in enumerate(lines) if rx.search(line)]
                topics.setdefault(key,{'title':kind.title()+' '+number.upper(),'kind':'identifier_candidate','members':[]})['members'].append({'id':r['record_id'],'lines':positions});memberships.append(key)
            records.append({'id':r['record_id'],'title':r['title'],'path':r['source']['mirror_path'],'catalog':index})
            if not memberships:unassigned.append(r['record_id'])
    if len(records)!=manifest['records'] or len({r['id'] for r in records})!=len(records):raise ValueError('Record identity/count mismatch')
    out.mkdir(parents=True,exist_ok=True);shutil.copytree('web',out,dirs_exist_ok=True);(out/'data/topics').mkdir(parents=True,exist_ok=True)
    listing=[]
    for key,t in topics.items():
        tid=sha256(key.encode()).hexdigest()
        dump(out/'data/topics'/ (tid+'.json'),dict(t,id=tid,status='unreviewed_candidate'))
        listing.append({'id':tid,'title':t['title'],'kind':t['kind'],'count':len(t['members'])})
    listing.sort(key=lambda t:(t['kind']!='reporting_desk',t['title']))
    dump(out/'data/records.json',records);dump(out/'data/topics.json',listing);dump(out/'data/unassigned.json',unassigned)
    boot={'schema':'newsroom-browser-v1','app_revision':revision,'publication':pointer,'catalogs':catalogs,'records':len(records),'candidate_groups':len(topics),'unassigned':len(unassigned),'classification':'Finite lexical and identifier candidates, not verified relationships or exhaustive issue discovery','source_independence':'unresolved','full_historical_coverage':False}
    dump(out/'data/boot.json',boot)
    if sum(f.stat().st_size for f in out.rglob('*') if f.is_file())>256*1024*1024:raise ValueError('App artifact exceeds 256 MiB budget; partition metadata')
    print(json.dumps(boot,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-repo',required=True);p.add_argument('--out',required=True);p.add_argument('--revision',required=True);a=p.parse_args();build(a.dataset_repo,a.out,a.revision)
