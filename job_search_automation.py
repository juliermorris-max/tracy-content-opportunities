#!/usr/bin/env python3
"""Personal job discovery using public structured feeds. Python 3.11+, no packages.
No login, browser scraping, CAPTCHA workarounds, paid API, or private resume data.
"""
from __future__ import annotations
import argparse, csv, hashlib, html, json, re, sys, time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
USER_AGENT = 'TracyJobSearch/2.0 (personal job discovery; public APIs only)'

class TextParser(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.hidden += 1
        if tag in ('p','li','div','br','h1','h2','h3'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def text(value):
    p=TextParser(); p.feed(html.unescape(str(value or '')))
    return re.sub(r'[ \t]+',' ',''.join(p.parts)).strip()

def fetch(url, *, as_json=True):
    if urlparse(url).scheme != 'https': raise ValueError('Only HTTPS URLs are allowed')
    # No retries for forbidden/unauthorized responses; never bypass restrictions.
    for attempt in range(2):
        try:
            with urlopen(Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/json' if as_json else 'text/html'}),timeout=30) as r:
                raw=r.read(16_000_001)
                if len(raw)>16_000_000: raise ValueError('Response exceeds 16 MB')
                if as_json: return json.loads(raw)
                return r.geturl(), raw.decode('utf-8',errors='replace')
        except HTTPError as e:
            if attempt==0 and e.code in (429,500,502,503,504):
                delay=e.headers.get('Retry-After','3')
                # Large delays fail this source instead of hammering it.
                if not delay.isdigit() or int(delay)>30: raise
                time.sleep(max(3,int(delay))); continue
            raise
        except (TimeoutError,ConnectionError):
            if attempt: raise
            time.sleep(3)
    raise RuntimeError('Request did not complete')

def canonical(url):
    u=urlparse(url)
    query=urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith(('utm_','ref','source'))])
    return urlunparse((u.scheme.lower(),u.netloc.lower(),u.path.rstrip('/'),'',query,''))

def safe_job_url(url):
    u=urlparse(url)
    if u.scheme!='https' or not u.hostname or u.username: return False
    if u.path.rstrip('/') in ('','/jobs','/careers','/search','/jobs/search'): return False
    return not re.search(r'/(?:search|categories|tags)(?:/|$)',u.path)

def normalize(source, payload):
    kind=source['kind']; out=[]
    if kind in ('greenhouse','ashby','remotive'):
        if not isinstance(payload,dict) or not isinstance(payload.get('jobs'),list): raise ValueError('Missing jobs array')
        rows=payload['jobs']
    elif kind=='arbeitnow':
        if not isinstance(payload,dict) or not isinstance(payload.get('data'),list): raise ValueError('Missing data array')
        rows=payload['data']
    else:
        if not isinstance(payload,list): raise ValueError('Expected postings array')
        rows=payload
    for x in rows:
        if kind=='greenhouse':
            title=x['title']; location=x.get('location',{}).get('name','')
            description=text(x.get('content','')); url=x['absolute_url']; company=source['name']; remote=bool(re.search(r'remote|home.based',location,re.I)); employment=''; salary=''; published=''
        elif kind=='lever':
            title=x['text']; c=x.get('categories',{}); location='; '.join(dict.fromkeys([c.get('location','')]+c.get('allLocations',[])))
            description=text(x.get('descriptionPlain',x.get('description','')))+'\n'+'\n'.join(text(y.get('text',''))+' '+text(y.get('content','')) for y in x.get('lists',[]))+'\n'+text(x.get('additionalPlain',''))
            url=x.get('applyUrl') or x['hostedUrl']; company=source['name']; remote=x.get('workplaceType')=='remote'; employment=c.get('commitment',''); salary=''; published=''
            sr=x.get('salaryRange') or {}
            if sr.get('currency'): salary=f"{sr['currency']} {sr.get('min','?')}–{sr.get('max','?')} / {sr.get('interval','period unspecified')}"
        elif kind=='ashby':
            if x.get('isListed') is False: continue
            title=x['title']; location='; '.join([x.get('location','')]+[y.get('location','') for y in x.get('secondaryLocations',[])])
            description=text(x.get('descriptionPlain',x.get('descriptionHtml',''))); url=x.get('applyUrl') or x['jobUrl']; company=source['name']; remote=x.get('isRemote',False); employment=x.get('employmentType',''); salary=''; published=x.get('publishedAt','')
            comp=x.get('compensation') or {}; salary=comp.get('compensationTierSummary','')
        elif kind=='remotive':
            title=x['title']; location=x.get('candidate_required_location',''); description=text(x.get('description','')); url=x['url']; company=x['company_name']; remote=True; employment=x.get('job_type',''); salary=x.get('salary',''); published=x.get('publication_date','')
        elif kind=='arbeitnow':
            title=x['title']; location=x.get('location',''); description=text(x.get('description','')); url=x['url']; company=x['company_name']; remote=x.get('remote',False); employment=', '.join(x.get('job_types',[])); salary=''; published=datetime.fromtimestamp(x['created_at'],timezone.utc).isoformat() if x.get('created_at') else ''
        else: raise ValueError('Unsupported source type')
        if not title or not description or not safe_job_url(url): continue
        out.append(dict(title=text(title),company=text(company).strip(),location=text(location),description=description,url=canonical(url),remote=remote,employment=text(employment),salary=text(salary) or 'Not published',published=published,source=source['name'],source_kind=kind))
    return out

# Responsibilities, rather than generic words such as "content" in company boilerplate.
SKILLS={
 'UX writing and content design': r'\b(?:ux writ\w*|content design\w*|microcopy|ux copy|product copy)\b',
 'Content strategy and governance': r'\b(?:content strateg\w*|content governance|editorial strateg\w*|messaging strateg\w*)\b',
 'Content workflows and operations': r'\b(?:content operation\w*|content workflow\w*|content calendar|editorial calendar|content management|content delivery|content production)\b',
 'Writing and editorial craft': r'\b(?:copywriting|copywriter|write (?:clear|engaging|compelling|high.quality)|writing and editing|blog posts|long.form|website copy|editorial standards|brand voice|narrative development)\b',
 'SEO and content marketing': r'\b(?:seo|content marketing|search engine optimi[sz]ation)\b',
 'Localization and accessibility': r'\b(?:locali[sz]ation|accessibility|inclusive language)\b',
}
FOCUS=r'\b(?:content|copywriter|copywriting|ux writer|editorial|editor|writer|storytell\w*|narrative|communications|brand strategist|conversation\w* design\w*)\b'
UNRELATED=r'\b(?:engineer|developer|data scien\w*|account executive|sales manager|recruiter|underwriter|credit|sar writer|video editor|graphic designer|product designer|program manager|project manager)\b'

def eligibility(job):
    loc=job['location'].lower(); desc=job['description'].lower(); remote=job['remote'] or bool(re.search(r'\bremote\b|home.based',loc))
    # Explicit role restrictions override broad labels, citizenship and company footprint.
    restricted=r'(?:must (?:be |reside |live |be located |be based )|only (?:available |open )?to |(?:candidates|applicants) (?:must|need to) (?:be |reside |live )).{0,45}(?:united states|usa\b|u\.s\.|united kingdom|uk\b|germany|france|poland|netherlands)'
    if re.search(restricted,desc) and not re.search(r'\bspain\b|españa',loc): return None
    if re.search(r'(?:us|usa|united states|uk|united kingdom)[ -]only|spain (?:is )?(?:excluded|not eligible)|(?:cannot|can.t|do not) (?:hire|employ).{0,20}spain',loc+' '+desc): return None
    if re.search(r'\bbarcelona\b',loc):
        return ('Remote · Barcelona' if remote else 'Barcelona · office/hybrid; check posting','Barcelona is listed as a work location.',False)
    if re.search(r'\bspain\b|españa',loc) and remote:
        return ('Remote · Spain','Spain is explicitly listed for this remote role.',False)
    broad=bool(re.search(r'\b(?:europe|european union|eu|emea|worldwide|anywhere|global)\b',loc))
    if remote and broad:
        # Region and limited country lists are ambiguous; prefer precision.
        if re.search(r'\b(?:only|excluding|except|restricted|selected countries)\b',loc): return None
        return ('Remote · '+job['location'],'Regional eligibility: '+job['location']+'. Confirm Spain hiring and any travel requirements.',True)
    return None

def pay_preference(salary):
    """Compare only explicit currencies and periods; never convert or infer dollars."""
    s=salary.lower().replace(',','')
    numbers=[float(n)*(1000 if k else 1) for n,k in re.findall(r'(\d+(?:\.\d+)?)\s*(k)?',s)]
    if not numbers: return 0
    high=max(numbers)
    if ('eur' in s or '€' in s) and re.search(r'year|annual|annum',s): target=70000
    elif 'usd' in s and re.search(r'hour|/hr|hourly',s): target=60
    elif 'usd' in s and re.search(r'/day|daily|per day',s): target=500
    else: return 0
    return 4 if high>=target else -4

def evaluate(job, now=None):
    now=now or datetime.now(timezone.utc); title=job['title'].lower(); d=job['description'].lower()
    if re.search(r'\b(?:intern(?:ship)?|junior|entry.level|graduate|working student|apprentice|trainee)\b',title): return None
    if re.search(r'\b(?:program|project) manager\b',title) and not re.search(r'\b(?:content|editorial|locali[sz]ation)\b',title): return None
    if re.search(UNRELATED,title) and not re.search(r'\b(?:content|ux|editorial|copywriting)\b',title): return None
    if re.search(r'\b(?:engineer|developer|technical program|software|program manager)\b',title) and not re.search(r'\b(?:writer|content design)\b',title): return None
    if re.search(r'\btechnical writer\b',title) and re.search(r'\b(?:sdk|api reference|developer documentation|code samples)\b',d): return None
    if re.search(r'accessing.{0,40}(?:require payment|payment)|(?:pay|fee|payment).{0,35}(?:access (?:work|tasks)|membership|apply for)',d): return None
    loc=eligibility(job)
    if not loc: return None
    if job.get('published'):
        try:
            published=datetime.fromisoformat(job['published'].replace('Z','+00:00'))
            if published.tzinfo is None: published=published.replace(tzinfo=timezone.utc)
            if now-published>timedelta(days=120): return None
        except ValueError: pass
    skills=[name for name,pattern in SKILLS.items() if re.search(pattern,d)]
    focused=bool(re.search(FOCUS,title))
    # Adjacent jobs need several independent skills and an explicit writing duty.
    duties=bool(re.search(r'(?:create|write|develop|own|lead|manage|produce|design|edit|craft).{0,65}(?:content|copy|editorial|messaging|narrative)',d))
    if not focused and not (len(skills)>=3 and duties and re.search(r'\b(?:brand|marketing|communication|conversation|knowledge|learning|experience|creative|locali[sz]ation)\b',title)): return None
    if len(skills)<2 or not duties: return None
    score=30+(12 if focused else 4)+min(28,len(skills)*6)
    why=skills[:4]; et=job['employment'].lower(); contract=bool(re.search(r'freelance|contract|temporary',et+' '+title)); part=bool(re.search(r'part[ -]?time',et+' '+title))
    if contract: score+=16; why.append('Freelance / contract preference')
    elif part: score+=12; why.append('Part-time preference')
    if re.search(r'\b(?:senior|lead|head|principal|manager|director)\b',title): score+=6
    if re.search(r'\b(?:digital health|medical devices?|healthcare|mental health|wellbeing|wellness|fitness)\b',d): score+=8; why.append('Health / wellbeing subject matter')
    elif re.search(r'\b(?:saas|software|technology)\b',d): score+=3
    if loc[2]: score-=6
    notes=[]
    pay=pay_preference(job['salary']); score+=pay
    if pay>0: why.append('Published pay range reaches a stated target')
    elif pay<0: notes.append('Published pay below the stated target')
    if loc[2]: notes.append('Confirm Spain eligibility')
    if re.search(r'\b(?:travel|in.person events|offsites)\b',d): notes.append('Check travel expectations')
    if re.search(r'\b(?:german|french|italian|dutch|polish|swedish)\b.{0,35}\b(?:native|fluent|fluency|c1|c2|required)|\b(?:native|fluent|fluency)\b.{0,25}\b(?:german|french|italian|dutch|polish|swedish)\b',d): notes.append('Additional language requirement — check posting')
    if job['salary'] != 'Not published' and '$' in job['salary'] and not re.search(r'USD|CAD|AUD|NZD',job['salary'],re.I): notes.append('Dollar currency as published; currency code not specified')
    if not re.search(r'\b(?:senior|lead|head|principal|manager|director)\b',title): notes.append('Seniority not explicit — check scope')
    job=dict(job); job.update(score=max(0,min(99,score)),why=why,arrangement=loc[0],location_evidence=loc[1],regional=loc[2],notes=notes,employment=('Freelance / contract' if contract else 'Part-time' if part else job['employment'] or 'Not specified'))
    return job

class ApplicationParser(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.href=None; self.label=''
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            d=dict(attrs); self.href=d.get('href',''); self.label=d.get('aria-label','')+' '+d.get('class','')
    def handle_data(self,data):
        if self.href is not None: self.label+=' '+data
    def handle_endtag(self,tag):
        if tag=='a' and self.href is not None:
            if re.search(r'apply|application',self.label,re.I): self.links.append(self.href)
            self.href=None; self.label=''

def validate_link(job):
    try:
        final,body=fetch(job['url'],as_json=False)
        if not safe_job_url(final): raise ValueError('Redirected to a generic page')
        plain=text(body).lower()
        if re.search(r'(?:this (?:job|position|role) (?:is no longer|has been (?:filled|closed))|job (?:not found|no longer available)|position has been filled)',plain): raise ValueError('Posting says closed or unavailable')
        # Employer location evidence overrides an aggregator's broad remote label.
        if job.get('from_aggregator'):
            location_tail=re.search(r'\blocation\s*:\s*([\s\S]{1,120})$',plain,re.I)
            if location_tail and re.search(r'\b(?:us|usa|united states|ca|canada|uk|united kingdom)\b',location_tail[1]) and not re.search(r'\b(?:spain|españa|europe|emea|worldwide)\b',location_tail[1]):
                raise ValueError('Employer location conflicts with Spain eligibility from feed')
        # Feed aggregators must expose a direct, public application URL.
        if job.get('source_kind') in ('remotive','arbeitnow'):
            parser=ApplicationParser(); parser.feed(body)
            direct=next((u for u in parser.links if safe_job_url(u) and urlparse(u).hostname!=urlparse(job['url']).hostname),None)
            if not direct: raise ValueError('No direct public application link found')
            employer=dict(job,url=canonical(direct),source_kind='employer',from_aggregator=True)
            verified,error=validate_link(employer)
            if error: raise ValueError(error['error'])
            verified['source_posting_url']=job['url']; return verified,None
        # An HTTP 200 alone is insufficient. Require job-specific title words and application evidence.
        words=[w for w in re.findall(r'[a-z]{4,}',job['title'].lower()) if w not in ('senior','remote','manager')]
        if not words or not any(w in plain for w in words): raise ValueError('Could not confirm job title on page')
        if not re.search(r'apply|application|posting-api|ashby|lever-jobs',body,re.I): raise ValueError('Could not confirm application page')
        job=dict(job); job['link_status']='Posting page checked'; return job,None
    except Exception as e: return None,dict(source=job['source'],url=job['url'],error='Link validation: '+str(e))

def dedupe(jobs):
    seen_urls=set(); seen_roles=set(); out=[]
    for j in sorted(jobs,key=lambda j:(-j['score'],j['company'].lower(),j['title'].lower())):
        role=(re.sub(r'\W','',j['company'].lower()),re.sub(r'\W','',j['title'].lower()))
        if j['url'] in seen_urls or role in seen_roles: continue
        seen_urls.add(j['url']); seen_roles.add(role); out.append(j)
    return out

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n'); tmp.replace(path)

def render(report,out):
    out.mkdir(parents=True,exist_ok=True)
    # Build every file in a staging directory; caller only promotes a complete generation.
    jobs=report['jobs']; esc=lambda s:html.escape(str(s),quote=True)
    groups=defaultdict(list)
    for j in jobs: groups[j['company']].append(j)
    sections=[]
    for company,rows in groups.items():
        cards=[]
        for j in rows:
            attrs=f'data-search="{esc(company+" "+j["title"]+" "+" ".join(j["why"]))}" data-flex="{int("contract" in j["employment"].lower() or "part-time" in j["employment"].lower())}" data-regional="{int(j["regional"])}"'
            cards.append(f'''<article class="job" {attrs}><div class="job-top"><h3>{esc(j['title'])}</h3><span class="score">{j['score']} <small>match score</small></span></div><div class="tags"><span>{esc(j['arrangement'])}</span><span>{esc(j['employment'])}</span></div><p class="salary">{esc(j['salary'])}</p><p class="why"><strong>Why it fits</strong> · {esc(' · '.join(j['why']))}</p><p class="evidence">{esc(j['location_evidence'])}</p>{('<p class="notes">'+esc(' · '.join(j['notes']))+'</p>') if j['notes'] else ''}<div class="job-bottom"><a class="apply" href="{esc(j['url'])}" target="_blank" rel="noopener noreferrer">View job &amp; apply <span aria-hidden="true">↗</span></a><small>Found {esc(j['first_found'][:10])} · {esc(j['source'])}{(' · Posted '+esc(j['published'][:10])) if j['published'] else ''}</small></div></article>''')
        sections.append(f'<section class="company"><h2>{esc(company)} <span>{len(rows)} {"opportunity" if len(rows)==1 else "opportunities"}</span></h2>'+''.join(cards)+'</section>')
    completed=datetime.fromisoformat(report['completed_at']).astimezone(ZoneInfo('Europe/Madrid')).strftime('%d %b %Y at %H:%M %Z')
    template=(ROOT/'templates/report.html').read_text()
    values={'COMPLETED':esc(completed),'ISO':esc(report['completed_at']),'COUNT':len(jobs),'COMPANIES':len(groups),'FLEX':sum('contract' in j['employment'].lower() or 'part-time' in j['employment'].lower() for j in jobs),'SOURCES':report['sources_ok'],'TOTAL_SOURCES':report['sources_total'],'SCANNED':report['postings_scanned'],'SECTIONS':''.join(sections) or '<div class="empty">No verified matches today. A quiet report is better than unrelated jobs. The next search may find new opportunities.</div>','ERROR_COUNT':len(report['errors']),'SOURCE_DETAILS':''.join(f'<li>{esc(s["name"])}: {esc(s["status"])}'+(f' — {s["count"]} postings' if 'count' in s else '')+'</li>' for s in report['source_status'])}
    for key,value in values.items(): template=template.replace('{{'+key+'}}',str(value))
    (out/'index.html').write_text(template); (out/'.nojekyll').touch()
    public=dict(report); public['jobs']=[{k:v for k,v in j.items() if k!='description'} for j in jobs]
    atomic_json(out/'results.json',public)
    fields=['company','title','score','arrangement','employment','salary','location_evidence','url','first_found','published']
    with (out/'jobs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for j in jobs:
            # Spreadsheet formula injection protection for feed-supplied text.
            w.writerow({k:("'"+str(j.get(k,'')) if str(j.get(k,'')).startswith(('=','+','-','@')) else j.get(k,'')) for k in fields})

def run(sources,output,state_dir,now=None):
    import shutil,tempfile
    now=now or datetime.now(timezone.utc); errors=[]; status=[]; raw=[]; ok=0
    def collect(s):
        try: return normalize(s,fetch(s['url'])),None
        except Exception as e: return [],dict(source=s['name'],url=s['url'],error=str(e))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for source,(rows,error) in zip(sources,pool.map(collect,sources)):
            if error: errors.append(error); status.append(dict(name=source['name'],status='Failed'))
            else: ok+=1; raw.extend(rows); status.append(dict(name=source['name'],status='OK',count=len(rows)))
    candidates=dedupe([m for j in raw if (m:=evaluate(j,now))])
    verified=[]
    # Sequential checks are deliberate: low request volume, no aggressive scraping.
    for j in candidates[:60]:
        result,error=validate_link(j)
        if error: errors.append(error)
        else: verified.append(result)
        time.sleep(.4)
    state_dir.mkdir(parents=True,exist_ok=True)
    attempt=dict(attempted_at=now.isoformat(),sources_ok=ok,sources_total=len(sources),postings_scanned=len(raw),candidates=len(candidates),verified=len(verified),errors=errors,source_status=status)
    # Don't publish a misleading empty/partial report when coverage collapses.
    healthy=ok>=max(2,(len(sources)+1)//2) and len(raw)>0
    # If the last report relied on a source now failing, retain it rather than
    # silently deleting all of that source's opportunities.
    if (output/'results.json').exists():
        previous=json.loads((output/'results.json').read_text())
        failed_sources={s['name'] for s in status if s['status']=='Failed'}
        if any(j['source'] in failed_sources for j in previous.get('jobs',[])): healthy=False
    # If most candidate links failed for transport reasons, don't wipe the report.
    transient=[e for e in errors if e['error'].startswith('Link validation:') and re.search(r'HTTP Error (?:403|429|5\d\d)|timed out|[Cc]onnection',e['error'])]
    if candidates and len(transient)>len(candidates)/2: healthy=False
    atomic_json(state_dir/'last_attempt.json',dict(attempt,success=healthy))
    if not healthy:
        print('Search failed health checks. Previous report preserved.',file=sys.stderr); return 1
    prior={}
    if (state_dir/'history.json').exists(): prior=json.loads((state_dir/'history.json').read_text())
    for j in verified:
        key=hashlib.sha256((j['company'].lower()+'|'+j['title'].lower()).encode()).hexdigest()[:24]
        j['first_found']=prior.get(key,now.isoformat()); prior[key]=j['first_found']
    # Bound history to a year. No old jobs are carried into the current report.
    prior={k:v for k,v in prior.items() if v>= (now-timedelta(days=365)).isoformat()}
    report=dict(completed_at=datetime.now(timezone.utc).isoformat(),sources_ok=ok,sources_total=len(sources),postings_scanned=len(raw),jobs=verified,errors=errors,source_status=status)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        staged=Path(tmp)/'site'; render(report,staged)
        output.mkdir(parents=True,exist_ok=True)
        for p in staged.iterdir(): p.replace(output/p.name)
    atomic_json(state_dir/'history.json',prior)
    print(json.dumps({k:v for k,v in attempt.items() if k not in ('errors','source_status')},indent=2)); return 0

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--sources',type=Path,default=ROOT/'sources.json'); p.add_argument('--output-dir',type=Path,default=ROOT/'docs'); p.add_argument('--state-dir',type=Path,default=ROOT/'data'); a=p.parse_args()
    return run(json.loads(a.sources.read_text()),a.output_dir,a.state_dir)
if __name__=='__main__': sys.exit(main())
