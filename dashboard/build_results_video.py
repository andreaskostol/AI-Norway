"""Build a data-driven, offline review film from the website's own release JSON."""
import argparse, hashlib, html, json, math, re, subprocess
from pathlib import Path
Q1='Quintile 1 (least exposed)'
Q5='Quintile 5 (most exposed)'
MONTHS=['januar','februar','mars','april','mai','juni','juli','august','september','oktober','november','desember']
def finite(x):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ValueError('Missing or non-finite observation')
    return x

def extract(d):
    required=['by_exposure','age_by_exposure','software_developers','customer_service','electricians','mouchel_by_exposure','mouchel_age_by_exposure']
    packs=d['packages']; dates=packs[required[0]]['dates'];edge=dates[-1][:7]
    if dates!=sorted(set(dates)) or len(dates)<3:raise ValueError('Invalid dates')
    for a,b in zip(dates,dates[1:]):
        ya,ma=map(int,a[:7].split('-'));yb,mb=map(int,b[:7].split('-'))
        if yb*12+mb-ya*12-ma!=1:raise ValueError('Missing month')
    for k in required:
        if packs[k]['dates']!=dates:raise ValueError('Mixed data vintages')
    if d['base_month']!='2022-11-01':raise ValueError('Changed chart baseline requires review')
    ref=dates.index('2022-10-01');base=dates.index(d['base_month'])
    def series(k,adjustment,facet,col):
        s=packs[k]['series'][adjustment][facet][col]
        if len(s)!=len(dates):raise ValueError('Series length mismatch')
        return [finite(x) for x in s]
    def growth(s):
        before=sum(s[ref-2:ref+1])/3
        if before<=0:raise ValueError('Invalid reference level')
        return (sum(s[-3:])/3)/before
    out={'release':d['release'],'edge':edge,'month':MONTHS[int(edge[5:])-1]+' '+edge[:4], 'dates':dates[base:]}
    for key,young in [('overall',False),('young',True)]:
        a=series('age_by_exposure','sa',Q1,'21-30') if young else series('by_exposure','sa','_',Q1)
        b=series('age_by_exposure','sa',Q5,'21-30') if young else series('by_exposure','sa','_',Q5)
        value=100*(growth(b)/growth(a)-1)
        u=d['headline_uncertainty'+('_young' if young else '')+'_by_measure']['eloundou']
        if u['vintage']!=edge or u['spec']!='sa':raise ValueError('Uncertainty vintage/spec mismatch')
        for field in ['ki','se','ci_lo','ci_hi']:finite(u[field])
        if abs(value-u['ki'])>.08:raise ValueError('Headline and uncertainty estimate disagree')
        if not u['ci_lo']<=u['ki']<=u['ci_hi'] or u['se']<0:raise ValueError('Invalid uncertainty interval')
        out[key]={'value':value,'low':u['ci_lo'],'high':u['ci_hi']}
    out['agentic']={}
    agent_ref=dates.index('2025-01-01')
    for measure in ['eloundou','mouchel']:
        out['agentic'][measure]={}
        prefix='' if measure=='eloundou' else 'mouchel_'
        for key,young in [('overall',False),('young',True)]:
            a=series(prefix+'age_by_exposure','sa',Q1,'21-30') if young else series(prefix+'by_exposure','sa','_',Q1)
            b=series(prefix+'age_by_exposure','sa',Q5,'21-30') if young else series(prefix+'by_exposure','sa','_',Q5)
            def factor(v):return sum(v[-3:])/sum(v[agent_ref-2:agent_ref+1])
            value=100*(factor(b)/factor(a)-1)
            u=d['headline_uncertainty'+('_young' if young else '')+'_claudecode_by_measure'][measure]
            for field in ['ki','se','ci_lo','ci_hi']:finite(u[field])
            if u['vintage']!=edge or u['spec']!='sa' or abs(value-u['ki'])>.08:raise ValueError('Agentic comparison and uncertainty disagree')
            if not u['ci_lo']<=u['ki']<=u['ci_hi'] or u['se']<0:raise ValueError('Invalid agentic uncertainty')
            out['agentic'][measure][key]={'value':value,'low':u['ci_lo'],'high':u['ci_hi']}
    out['examples']={}
    for k,label in [('software_developers','Programvareutviklere'),('customer_service','Kundeservice'),('electricians','Elektrikere')]:
        vals=series(k,'percap_sa','_','21-30')[base:]
        if abs(vals[0]-100)>.1:raise ValueError('Occupation chart is not rebased at November 2022')
        out['examples'][k]={'label':label,'values':vals,'change':vals[-1]-100}
    return out

def num(x):return f'{x:.1f}'.replace('.',',').replace('-','−')
def spoken(x):
    digits=['null','én','to','tre','fire','fem','seks','sju','åtte','ni']
    a,b=f'{abs(x):.1f}'.split('.')
    return ('minus ' if x<-.049 else '')+a+' komma '+digits[int(b)]
def assessment(s):
    if s['low']>0:return 'De mest eksponerte yrkene har vokst mer enn de minst eksponerte. Usikkerhetsintervallet ligger over null.'
    if s['high']<0:return 'De mest eksponerte yrkene har vokst mindre enn de minst eksponerte. Usikkerhetsintervallet ligger under null.'
    return 'Usikkerhetsintervallet omfatter null. Vi kan ikke skille denne forskjellen fra null med dette usikkerhetsmålet.'
def change_sentence(label,x):
    verb='økt' if x>=0 else 'falt'
    return f'For {label} har sysselsettingen per innbygger i aldersgruppen {verb} med {spoken(abs(x))} prosent siden november 2022.'

def story(f):
    a=f['agentic'];e=f['examples']
    ey,my=a['eloundou']['young'],a['mouchel']['young']
    all_close=all(abs(a[m]['overall']['value'])<.5 for m in a)
    all_text='Her viser begge anslagene omtrent samme vekst i de mest og minst eksponerte yrkene.' if all_close else 'Forskjellene mellom gruppene er vist med hvert sitt usikkerhetsintervall.'
    same='Begge målene viser svakere relativ vekst blant unge.' if max(ey['value'],my['value'])<0 else 'Retningen blant unge avhenger av de oppdaterte anslagene.'
    uncertainty=('For Eloundou omfatter usikkerhetsintervallet null. For Mouchel ligger hele intervallet under null.' if ey['low']<=0<=ey['high'] and my['high']<0 else 'Eloundou: '+assessment(ey)+' Mouchel: '+assessment(my))
    return [
      ('opening','kiindeksen.no',f'Er det blitt vanskeligere å komme inn i arbeidslivet etter gjennombruddet for agentisk KI? KI-indeksen følger norske jobber med data til {f["month"]}. Vi sammenligner yrker der KI kan gjøre mange av oppgavene, med yrker der teknologien kan gjøre mindre. Her ser vi særlig på utviklingen etter februar 2025 da agentisk KI ble tilgjengelig.'),
      ('occupation_tasks','Hva kan KI gjøre i jobben?', 'KI kan hjelpe en programvareutvikler med å skrive og teste kode, og en regnskapsfører med å kontrollere bilag og sette opp regnskap. En rørlegger må derimot montere og reparere rør. En renholder må vaske rommet. KI kan hjelpe med planleggingen, men selve arbeidet må fortsatt gjøres på stedet. Eksponering beskriver hvilke oppgaver teknologien kan utføre. Det forteller ikke hvor mange jobber som forsvinner.'),
      ('occupation_trends','Hvordan har jobbene utviklet seg?', f'Kurvene viser sysselsetting per innbygger for programvareutviklere og elektrikere fra tjueén til tretti år, med november 2022 som felles startpunkt. {change_sentence("programvareutviklere",e["software_developers"]["change"])} {change_sentence("elektrikere",e["electricians"]["change"])} Elektrikere er blant de minst eksponerte hos Eloundou, men i neste gruppe hos Mouchel. Disse yrkene er eksempler. De viser ikke alene hva som skjer i hele arbeidsmarkedet.'),
      ('mine','Kanarifuglen i kullgruven','Gruvearbeidere hadde med kanarifugler som reagerte på giftig gass før menneskene gjorde det. Fuglen varslet fare. I arbeidsmarkedet kan utviklingen blant unge gi et tidlig tegn på endring, fordi bedrifter kan redusere nyansettelsene mens de erfarne ansatte fortsatt beholder jobbene sine. Da merkes endringen først blant dem som søker sin første jobb.'),
      ('agent_work','Fra svar til arbeidsoppgaver','En vanlig KI-samtale kan gi deg et forslag til kode. En agent kan også åpne filer, endre koden, kjøre tester og forsøke igjen når noe feiler. Flere ledd i arbeidet kan dermed utføres sammen. Utvikleren må fortsatt bestemme hva som skal bygges og kontrollere resultatet. Dette gjør rekruttering til slike jobber interessant å følge.'),
      ('periods','To ulike startpunkter',f'Måler vi fra ChatGPT kom i 2022, er hovedindeksen {spoken(f["overall"]["value"])} prosent med Eloundous eksponeringsmål. Men den perioden inkluderer også flere år før agentisk KI. Derfor flytter vi nå startpunktet til Claude Code kom i februar 2025. Vi sammenligner de siste tre månedene med november 2024 til januar 2025. Vi undersøker en kortere periode med samme beregningsmåte.'),
      ('index','Fra yrker til grupper','Når vi rangerer alle yrkene etter hvor mange oppgaver KI kan utføre, havner rørleggere og renholdere i Q1, gruppen med lavest eksponering. Det er fem grupper i alt. Programvareutviklere og regnskapsførere er i Q5, gruppen med høyest eksponering. Disse eksemplene er i samme gruppe hos både Eloundou og Mouchel. Andre yrker kan skifte gruppe. Indeksen sammenligner sysselsettingsveksten i Q5 med veksten i Q1. Et negativt tall betyr at Q5 vokser mindre, eller faller mer, enn Q1.'),
      ('agent_all','Etter februar 2025: alle',f'For personer fra tjueén til seksti år viser begge eksponeringsmålene omtrent samme vekst i Q5 og Q1. Anslagene ligger nær null. Strekene rundt punktene viser usikkerheten i beregningen.' if all_close else f'For personer fra tjueén til seksti år er forskjellen {spoken(a["eloundou"]["overall"]["value"])} prosent med Eloundou og {spoken(a["mouchel"]["overall"]["value"])} prosent med Mouchel. Strekene viser usikkerheten i beregningen.'),
      ('agent_young','Etter februar 2025: unge',f'For personer fra tjueén til tretti år er bildet annerledes. Forskjellen er {spoken(ey["value"])} prosent med Eloundou og {spoken(my["value"])} prosent med Mouchel. {same} Unge har dermed en annen utvikling enn aldersgruppene samlet.'),
      ('agent_limits','Hvor sikre er funnene?',f'{uncertainty} Derfor er styrken i funnet følsom for hvordan vi måler eksponering. Sammenligningen viser heller ikke at agentisk KI har forårsaket forskjellen. Renter, konjunkturer og endret etterspørsel kan påvirke de samme yrkene. Vi følger om mønsteret varer når nye måneder kommer til.')]

def build(source,out,assets,audio=None):
    raw=source.read_bytes();f=extract(json.loads(raw));scenes=[];start=0
    for i,(kind,title,text) in enumerate(story(f)):
        tokens=text.split();duration=max(20,len(tokens)/145*60+1.2);words=[];sound=None
        if audio:
            sound=Path(str(audio)+f'-{i:02d}.wav');alignment=Path(str(audio)+f'-{i:02d}.json')
            if not sound.exists() or not alignment.exists():raise ValueError(f'Missing audio/alignment for scene {i}')
            duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(sound)]))
            words=json.loads(alignment.read_text())['words']
            if [w['word'] for w in words]!=tokens:raise ValueError('Alignment transcript differs from script')
            previous=-1
            for w in words:
                if not previous<=finite(w['start'])<finite(w['end'])<=duration:raise ValueError('Invalid word timing')
                previous=w['end']
        else:
            words=[{'word':w,'start':.3+(duration-.7)*j/len(tokens),'end':.3+(duration-.7)*(j+1)/len(tokens)} for j,w in enumerate(tokens)]
        duration=math.ceil(duration*25)/25
        scenes.append(dict(kind=kind,title=title,text=text,duration=duration,start=start,words=words,audio=str(sound.resolve()) if sound else None));start+=duration
    if not 180<=start<=300:raise ValueError(f'Film duration outside 3–5 minutes: {start}')
    manifest={'schema_version':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'source':str(source.resolve()),'facts':f,'scenes':scenes,'duration':start,'timing':'aligned' if audio else 'provisional','history_source':'https://blog.scienceandindustrymuseum.org.uk/canary-resuscitator/'}
    stem=out/'kiindeksen-resultatfilm'
    Path(str(stem)+'.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    Path(str(stem)+'-manus.txt').write_text('\n\n'.join(s['text'] for s in scenes))
    shell=(assets/'results_video.html').read_text();shell=shell.replace('/*DATA*/', 'window.FILM='+json.dumps(manifest,ensure_ascii=False).replace('<','\\u003c')+';')
    shell=shell.replace('/*INK*/',(assets/'video_ink.js').read_text()).replace('/*SCENES*/',(assets/'results_video.js').read_text())
    Path(str(stem)+'.html').write_text(shell)
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=Path(__file__).parent/'site/public/data/dashboard.json');p.add_argument('--out',type=Path,required=True);p.add_argument('--audio',type=Path);p.add_argument('--render',action='store_true');p.add_argument('--synthesize',action='store_true',help='Explicitly send narration to ElevenLabs with the approved Kristine voice');args=p.parse_args()
    if not args.out.is_dir():p.error('--out must be an existing directory')
    m=build(args.data,args.out,Path(__file__).parent,args.audio)
    if args.synthesize:
        from synthesize_video import synth
        from build_research_video import write_html
        manifest=args.out/'kiindeksen-resultatfilm.json'
        synth(manifest,args.out/'kiindeksen-resultatfilm-lyd')
        write_html(manifest,Path(__file__).parent)
        m=json.loads(manifest.read_text())
    if args.render:subprocess.run(['node',str(Path(__file__).parent/'render_results_video.mjs'),str(args.out.resolve())],check=True)
    print(json.dumps({'release':m['facts']['release'],'data_month':m['facts']['edge'],'duration':m['duration'],'timing':m['timing']},ensure_ascii=False))
if __name__=='__main__':main()
