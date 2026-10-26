"""Static, crawlable record publication; no claim of Google indexing."""
import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote
from xml.sax.saxutils import escape as xml_escape

BASE='https://bartimoussmith-oss.github.io/civic-newsroom/'

def read(root,path):
    f=(root/path).resolve()
    if root not in f.parents or not f.is_file():raise ValueError('Invalid data path')
    return f.read_bytes()

def page(title,body,path,structured=None):
    canonical=BASE+path
    data=json.dumps(structured or {'@context':'https://schema.org','@type':'WebPage','name':title,'url':canonical},ensure_ascii=False).replace('<','\u003c')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow,max-snippet:-1"><title>'+escape(title)+' | Civic Newsroom</title><link rel="canonical" href="'+escape(canonical,quote=True)+'"><script type="application/ld+json">'+data+'</script><style>body{font:18px/1.6 system-ui;max-width:1000px;margin:auto;padding:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}nav{display:flex;gap:16px;flex-wrap:wrap}.notice{background:#fff2cc;padding:14px}li{margin:10px 0}</style></head><body><nav><a href="'+BASE+'">Newsroom</a><a href="'+BASE+'archive/">Archive</a><a href="'+BASE+'intelligence.html">Intelligence workbench</a></nav>'+body+'</body></html>'

def build(repo,site):
    repo=Path(repo).resolve();site=Path(site);pointer=json.loads((repo/'published.json').read_text())
    if not re.fullmatch('build-[0-9]+',pointer['dataset_version']):raise ValueError('Invalid version')
    root=(repo/'datasets'/pointer['dataset_version']).resolve();raw=read(root,'collection.json')
    if sha256(raw).hexdigest()!=pointer['manifest_sha256']:raise ValueError('Manifest mismatch')
    manifest=json.loads(raw);summaries={};years={};urls=[BASE,BASE+'archive/']
    def write(path,title,body,data=None):
        destination=site/path/'index.html';destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(page(title,body,path+'/',data),encoding='utf-8')
        urls.append(BASE+path+'/')
    for catalog in manifest['catalogs']:
        raw=read(root,catalog['path'])
        if sha256(raw).hexdigest()!=catalog['sha256']:raise ValueError('Catalog mismatch')
        for record in json.loads(raw):
            rid=record['record_id']
            if not re.fullmatch('[a-f0-9]{64}',rid) or rid in summaries:raise ValueError('Invalid record identity')
            parts=[]
            for i,p in enumerate(record['representation']['parts']):
                b=read(root,p['path'])
                if i!=p['sequence'] or len(b)!=p['bytes'] or sha256(b).hexdigest()!=p['sha256']:raise ValueError('Blob mismatch')
                parts.append(b)
            raw=b''.join(parts)
            if len(raw)!=record['representation']['bytes'] or sha256(raw).hexdigest()!=record['representation']['sha256']:raise ValueError('Record mismatch')
            text=raw.decode('utf-8');title=record['title'];source_path=record['source']['mirror_path']
            year_match=re.search(r'/(\d{4})/',source_path);year=year_match.group(1) if year_match else 'unknown'
            summaries[rid]={'title':title,'year':year};years.setdefault(year,[]).append(rid)
            body='<article><h1>'+escape(title)+'</h1><p class="notice">Generated public-record text representation. Check the original source for layout, OCR/caption errors, dates and legal effect. This is not internal research or an independently certified transcript.</p><p>Source path: '+escape(source_path)+'</p><p>Representation SHA-256: '+record['representation']['sha256']+'</p><p><a href="'+BASE+'?record='+rid+'#reader">Open in evidence and media workspace</a> · <a href="metadata.json">Structured metadata</a></p><h2>Complete published text representation</h2><pre>'+escape(text)+'</pre></article>'
            structured={'@context':'https://schema.org','@type':'DigitalDocument','name':title,'identifier':rid,'url':BASE+'records/'+rid+'/','description':'Complete generated public Markdown representation; original binary identity and factual certification are not established.'}
            write('records/'+rid,title,body,structured)
            (site/'records'/rid/'metadata.json').write_text(json.dumps({'record_id':rid,'representation':record['representation'],'source':record['source'],'canonical_url':BASE+'records/'+rid+'/','dataset_revision':pointer['dataset_revision'],'date_status':'unverified_path_label','original_binary_identity':'not_established'},ensure_ascii=False,indent=2),encoding='utf-8')
    if len(summaries)!=manifest['records']:raise ValueError('Lost record pages')
    archive='<h1>Cheyenne public-record archive</h1><p class="notice">'+str(len(summaries))+' generated public representations, not independent-source counts or certified complete historical coverage. Internal research is not imported by this adapter. Year groups are path labels, not verified event dates.</p><h2>Browse by year</h2><ul>'
    for year,ids in sorted(years.items()):
        archive+='<li><a href="years/'+year+'/">'+year+'</a> — '+str(len(ids))+' representations</li>'
        body='<h1>'+year+' public representations</h1><p>Year is an unverified source-path label.</p><ul>'
        for rid in ids:body+='<li><a href="'+BASE+'records/'+rid+'/">'+escape(summaries[rid]['title'])+'</a></li>'
        write('archive/years/'+year,year+' public records',body+'</ul>')
    archive+='</ul><h2>Candidate issue and reference groups</h2><ul>'
    listing=json.loads((site/'data/topics.json').read_text(encoding='utf-8'))
    for topic in listing:
        tid=topic['id']
        if not re.fullmatch('[a-f0-9]{64}',tid):raise ValueError('Invalid topic ID')
        members=json.loads((site/'data/topics'/(tid+'.json')).read_text(encoding='utf-8'))['members']
        body='<h1>'+escape(topic['title'])+' — candidate record group</h1><p class="notice">Lexical/identifier grouping only. This is not a verified entity relationship, legal history, financial connection or causal finding.</p><ul>'
        for member in members:
            rid=member['id']
            if rid not in summaries:raise ValueError('Broken issue membership')
            body+='<li><a href="'+BASE+'records/'+rid+'/">'+escape(summaries[rid]['title'])+'</a></li>'
        write('issues/'+tid,topic['title']+' record references',body+'</ul>')
        archive+='<li><a href="'+BASE+'issues/'+tid+'/">'+escape(topic['title'])+'</a> — '+str(len(members))+' candidate representations</li>'
    write('archive','Cheyenne public-record archive',archive+'</ul>')
    home=site/'index.html';home.write_text(home.read_text(encoding='utf-8').replace('<nav>','<nav><a href="archive/">Full-text public archive</a>',1),encoding='utf-8')
    urls=sorted(set(urls))
    sitemap='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xml_escape(url)+'</loc></url>' for url in urls)+'</urlset>'
    if len(urls)>45000 or len(sitemap.encode())>45*1024*1024:raise ValueError('Split sitemap before publication')
    (site/'sitemap.xml').write_text(sitemap,encoding='utf-8')
    (site/'llms.txt').write_text('# Civic Newsroom public archive\n\nStart at '+BASE+'archive/ and '+BASE+'sitemap.xml. Full record text is statically rendered under records/ with per-record metadata.json. Candidate issue groups are under issues/. No JavaScript is required for these record pages. Full historical coverage, independent source verification and legal conclusions are not certified. These files do not guarantee search-engine or AI inclusion.\n',encoding='utf-8')
    readiness={'schema':'search-publication-readiness-v1','static_record_pages':len(summaries),'static_candidate_group_pages':len(listing),'sitemap_urls':len(urls),'intended_base_url':BASE,'no_javascript_required_for_record_text':True,'google_indexing_verified':False,'google_ai_mode_inclusion_verified':False,'full_historical_coverage':False,'origin_robots_policy':'Must be checked at origin /robots.txt; a project-level robots.txt does not control the origin'}
    (site/'data/search-readiness.json').write_text(json.dumps(readiness,indent=2),encoding='utf-8')
    total=sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
    if total>256*1024*1024:raise ValueError('App exceeds 256 MiB budget after static publication; partition pages without truncating source text')
    print(json.dumps(readiness,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset-repo',required=True);p.add_argument('--site',required=True);a=p.parse_args();build(a.dataset_repo,a.site)
