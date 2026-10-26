"""Separate archive renditions and exhaustive published-record scan, not a completeness certification."""
import json,re,html
from pathlib import Path
from hashlib import sha256
from collections import Counter

MODES=[('quick-check','Quick Check','Start with a local issue, then open its source.','issues,library,reader,coverage,media'),('guided-tour','Guided Tour','Choose an issue; read a record; inspect context; select explicit excerpts.','issues,library,reader,media,coverage'),('evidence-auditor','Evidence Auditor','Inspect exact source text, provenance and limitations before making a finding.','library,reader,coverage,issues,media'),('systems-explorer','Systems Explorer','Trace candidate issue groups and identifiers; verify every relationship.','issues,library,reader,coverage,media'),('community-connector','Community Connector','Explore local concerns and prepare source-linked questions.','issues,library,reader,media,coverage'),('action-planner','Action Planner','Find the responsible body, verify current deadlines, and document follow-up.','library,reader,issues,media,coverage'),('low-stimulation','Low-Stimulation Reader','Quiet single-column reading with no animation or automatic scrolling.','library,reader,coverage,issues,media'),('professional-desk','Professional Desk','Dense record access, explicit excerpts and collection metadata.','coverage,library,reader,issues,media')]
RULES=[('invitation',r'\b(?:public comments?|public hearing|comments? from (?:the )?(?:public|audience))\b'),('possible-participation',r'\b(?:spoke in (?:support|opposition)|addressed (?:the )?(?:council|committee)|expressed concern|questioned (?:use|funding|whether)|my name is)\b'),('possible-no-response',r'\b(?:no public comments?|no one spoke|seeing none|hearing none|i see none)\b')]
TOPICS={'money':r'\b(?:budget|tax|taxes|funding|cost|overage)\b','roads':r'\b(?:road|street|traffic|overpass|transit)\b','housing':r'\b(?:housing|rent|homeless|residential)\b','land-use':r'\b(?:zoning|annexation|subdivision|land use)\b','water':r'\b(?:water|sewer|wastewater)\b','process':r'\b(?:hearing|comment|notice|deadline|petition)\b','records':r'\b(?:website|records|minutes|documents|find|search)\b'}

def esc(x):return html.escape(str(x),quote=True)
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def dump(p,x):write(p,json.dumps(x,ensure_ascii=False,separators=(',',':')))
def checked(root,rel,expected,length=None):
    p=(root/rel).resolve()
    if root not in p.parents or not p.is_file():raise ValueError('Unsafe or missing source')
    b=p.read_bytes()
    if sha256(b).hexdigest()!=expected or (length is not None and len(b)!=length):raise ValueError('Source integrity failure')
    return b

def page(title,body):
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' | Civic Newsroom</title><link rel="stylesheet" href="../style.css"><style>table{border-collapse:collapse;width:100%}td,th{padding:12px;text-align:left;border-bottom:1px solid #abb}pre{white-space:pre-wrap;overflow-wrap:anywhere}.scroll{overflow:auto}a:focus-visible{outline:3px solid #2867c0}article{padding:16px 0;border-bottom:1px solid #abb}</style></head><body><header><h1>'+esc(title)+'</h1><nav><a href="../index.html">Newsroom</a><a href="../audiences/">Layouts</a><a href="../participation/">Participation</a><a href="../participation/coverage.html">Coverage ledger</a><a href="../intelligence.html">Intelligence workbench</a></nav></header><main><p class="notice">Published-record analysis, not a representative market survey. Automatic cues are not verified public comments. Dates, speakers, source independence and historical completeness require review. No personality or political inference.</p>'+body+'</main></body></html>'

def rendition(template,title,description,order,mode):
    text=template.replace('<head>','<head><base href="../">',1)
    text=re.sub(r'<title>.*?</title>','<title>'+esc(title)+' | Civic Newsroom</title>',text,count=1)
    text=text.replace('<h1>Civic Newsroom</h1>','<h1>'+esc(title)+'</h1>',1)
    text=text.replace('<main>','<main><section><h2>'+esc(title)+'</h2><p>'+esc(description)+'</p><p>Self-selected task layout; identical evidence and limitations. <a href="audiences/">Switch layout</a> · <a href="participation/">Participation evidence</a></p></section>',1)
    sections={m.group(1):m.group(0) for m in re.finditer(r'<section id="(issues|library|reader|media|coverage)">.*?</section>',text,re.S)}
    if set(sections)!=set(order.split(',')):raise ValueError('Archive controls changed; review rendition generator')
    for section in sections.values():text=text.replace(section,'',1)
    text=text.replace('</main>',''.join(sections[k] for k in order.split(','))+'</main>',1)
    css='html{scroll-behavior:auto}a:focus-visible,button:focus-visible{outline:3px solid #2867c0}pre{overflow-wrap:anywhere}'
    if mode=='low-stimulation':css+='body{background:white;color:#111;font-size:20px;line-height:1.85}header,main{max-width:850px}*{animation:none!important;transition:none!important}'
    elif mode=='professional-desk':css+='body{font-size:16px;line-height:1.5}section{padding:14px;margin:12px 0}'
    elif mode=='guided-tour':css+='section h2{border-left:5px solid #075b78;padding-left:12px}'
    elif mode=='quick-check':css+='#issues button{padding:14px;margin:7px}'
    return text.replace('</head>','<style>'+css+'</style></head>',1)

def build(repo,out):
    repo=Path(repo).resolve();out=Path(out);boot=json.loads((out/'data/boot.json').read_text());pointer=boot['publication'];root=(repo/'datasets'/pointer['dataset_version']).resolve()
    if repo not in root.parents:raise ValueError('Unsafe dataset root')
    manifest=json.loads(checked(root,'collection.json',pointer['manifest_sha256']))
    coverage=[];candidates=[];counts=Counter();topic_records={k:set() for k in TOPICS};seen=set();rules=[(k,re.compile(v,re.I)) for k,v in RULES];topics={k:re.compile(v,re.I) for k,v in TOPICS.items()}
    for cat in manifest['catalogs']:
        records=json.loads(checked(root,cat['path'],cat['sha256'],cat['bytes']))
        if len(records)!=cat['records']:raise ValueError('Catalog count mismatch')
        for r in records:
            rid=r['record_id']
            if rid in seen:raise ValueError('Duplicate record identity')
            seen.add(rid);parts=[]
            for i,p in enumerate(r['representation']['parts']):
                if p['sequence']!=i:raise ValueError('Part order mismatch')
                parts.append(checked(root,p['path'],p['sha256'],p['bytes']))
            raw=b''.join(parts);rep=r['representation']
            if len(raw)!=rep['bytes'] or sha256(raw).hexdigest()!=rep['sha256']:raise ValueError('Complete record mismatch')
            text=raw.decode('utf-8');path=r['source']['mirror_path'];kind='captions' if path.endswith('/captions.md') else 'minute-related' if re.search(r'\bminutes\b',(r['title']+' '+path).replace('-',' '),re.I) else 'meeting-index' if path.startswith('meetings/') else 'other'
            eligible=kind in ('captions','minute-related');counts[kind]+=1;start=len(candidates);sep=re.search(r'^---\s*$',text,re.M);offset=sep.end() if sep else 0
            if eligible:
                for category,rx in rules:
                    for m in rx.finditer(text,offset):
                        a=max(offset,m.start()-180);b=min(len(text),m.end()+500);context=text[a:b];tags=[k for k,t in topics.items() if t.search(context)]
                        for k in tags:topic_records[k].add(rep['sha256'])
                        candidates.append({'id':sha256((rep['sha256']+':'+str(m.start())+':'+category).encode()).hexdigest(),'record_id':rid,'title':r['title'],'path':path,'category':category,'cue':m.group(),'representation_sha256':rep['sha256'],'context_start_char':a,'context_end_char_exclusive':b,'start_line':len(re.split(r'\r\n|\r|\n',text[:a])),'end_line':len(re.split(r'\r\n|\r|\n',text[:b])),'topics':tags,'status':'unreviewed','event_date':None,'speaker_role':'unknown','timestamp':None})
            coverage.append({'record_id':rid,'path':path,'kind':kind,'integrity':'verified','eligible':eligible,'candidate_count':len(candidates)-start,'historical_completeness':'not_established'})
    if len(seen)!=manifest['records']:raise ValueError('Scan incomplete against published manifest')
    dest=out/'participation';dest.mkdir(exist_ok=True)
    summary={'dataset_revision':pointer['dataset_revision'],'records_verified':len(seen),'source_kinds':dict(counts),'candidates':len(candidates),'categories':dict(Counter(c['category'] for c in candidates)),'reviewed_comments':0,'full_historical_coverage':False,'source_families':'unresolved','fireflies_coverage':'not_imported_account_reported_inactive','topic_text_versions':{k:len(v) for k,v in topic_records.items()},'offset_convention':'zero-based Unicode code points; end exclusive; lines one-based'}
    dump(dest/'summary.json',summary);write(dest/'coverage.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in coverage));write(dest/'candidates.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in candidates))
    chunk=75;pages=max(1,(len(candidates)+chunk-1)//chunk)
    for n in range(pages):
        body='<p>Page '+str(n+1)+' of '+str(pages)+'. Candidates may overlap and include official speech.</p><nav>'
        if n:body+='<a href="candidates-'+str(n)+'.html">Previous</a> '
        if n+1<pages:body+='<a href="candidates-'+str(n+2)+'.html">Next</a>'
        body+='</nav>'
        for c in candidates[n*chunk:(n+1)*chunk]:
            body+='<article><h2>'+esc(c['title'])+'</h2><p>'+esc(c['category'])+': '+esc(c['cue'])+'</p><p>Topics: '+esc(', '.join(c['topics']))+'. Speaker, event date and timestamp unresolved.</p><p>Context lines '+str(c['start_line'])+'–'+str(c['end_line'])+'; '+esc(c['path'])+'</p><a href="../index.html?record='+c['record_id']+'#reader">Read complete verified record and inspect these lines</a><p>Representation SHA-256: <code>'+c['representation_sha256']+'</code></p></article>'
        write(dest/('candidates-'+str(n+1)+'.html'),page('Public-comment candidates',body))
    body='<h2>Scan results</h2><pre>'+esc(json.dumps(summary,indent=2))+'</pre><p><a href="candidates-1.html">Inspect every candidate, paginated</a> · <a href="candidates.jsonl">Download complete candidate references</a> · <a href="coverage.jsonl">Download every record scan result</a> · <a href="summary.json">Summary JSON</a> · <a href="../audiences/metrics-first.html">Metrics-first layout</a></p><h2>Interpretation and review requirements</h2><p>Invitations are not comments; no-response cues can be unrelated procedure; possible participation may be staff or officials. A reviewer must resolve speaker role, meeting identity/date, exact source context and duplicate events before confirming an actual public comment. This release does not import or claim the earlier two-event review. No verbatim speech or timestamps are invented.</p><p>Historical completeness requires an independently enumerated official meeting calendar and reconciliation of missing minutes, recordings, cancellations and attachments. This scan covers the complete published manifest only. Fireflies is not included. A zero-cue record is not proof of no comments.</p>'
    write(dest/'index.html',page('Participation evidence',body))
    body='<h2>Every published record accounted for</h2><p>'+str(len(coverage))+' record representations reconstructed and verified. Minutes-related classification can include approval-folder date mismatches. Original event dates remain unverified.</p><p><a href="coverage.jsonl">Complete per-record ledger</a></p><h2>Not yet established</h2><ul><li>Official-calendar reconciliation and all missing meetings</li><li>Full jurisdiction/year coverage</li><li>Cross-source duplicate-event resolution</li><li>Public-versus-official speaker attribution</li><li>Recording-aligned timestamps and exact speech</li><li>Human-reviewed public-comment totals</li></ul>'
    write(dest/'coverage.html',page('Meeting and minute coverage',body))
    template=(out/'index.html').read_text();links=[]
    for mode,title,description,order in MODES:
        write(out/'audiences'/(mode+'.html'),rendition(template,title,description,order,mode));links.append('<li><a href="'+mode+'.html">'+esc(title)+'</a> — '+esc(description)+'</li>')
    ranking=sorted(summary['topic_text_versions'].items(),key=lambda x:(-x[1],x[0]));top=', '.join(k+' ('+str(v)+' eligible text versions)' for k,v in ranking)
    description='Exploratory candidate-topic coverage: '+top+'. These are not actual-comment counts, population demand or GUI preferences. Use this layout to test evidence-navigation priorities; all source records remain available.'
    text=rendition(template,'Metrics-first archive',description,'issues,library,reader,coverage,media','metrics-first')
    text=text.replace('<section id="issues">','<section><h2>Inspect the evidence behind this rendition</h2><p><a href="participation/">Participation metrics</a> · <a href="participation/coverage.html">Completeness ledger</a></p><p>Ranking counts distinct representation hashes near any cue, not independent meetings. Historical frequency and archive availability may distort apparent prominence. No automatic political or personality targeting.</p></section><section id="issues">',1)
    write(out/'audiences/metrics-first.html',text);links.append('<li><a href="metrics-first.html">Metrics-first archive</a> — exploratory archive-derived topic coverage, explicitly unreviewed.</li>')
    write(out/'audiences/index.html',page('Choose your archive layout','<ul>'+''.join(links)+'</ul><p>Every rendition retains the existing archive reader and media tools. JavaScript is required for those interactive tools; the <a href="../archive/">complete static archive</a> remains available without JavaScript. Layouts do not diagnose personality or change evidence.</p>'))
    home=out/'index.html';write(home,home.read_text().replace('<nav>','<nav><a href="audiences/">Site renditions</a><a href="participation/">Public-comment analysis</a><a href="participation/coverage.html">Meeting coverage</a>',1))
    for mode,_,_,_ in MODES:
        s=(out/'audiences'/(mode+'.html')).read_text()
        for required in ('id="record-text"','id="add-evidence"','id="generate"','src="app.js"','<base href="../">'):
            if required not in s:raise ValueError('Missing rendition control: '+required)
    size=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if size>256*1024*1024:raise ValueError('Complete site exceeds size budget; partition before publication')
    print(json.dumps({'renditions':9,'records_scanned':len(seen),'candidate_cues':len(candidates),'artifact_bytes':size,'historical_completeness':False,'reviewed_comments':0}))
