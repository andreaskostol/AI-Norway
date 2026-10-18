import argparse,hashlib,json,subprocess
from pathlib import Path
from research_video_stories import FILMS,SOURCES

def write_html(manifest,assets):
 m=json.loads(manifest.read_text());stem=manifest.with_suffix('');shell=(assets/'results_video.html').read_text()
 shell=shell.replace('kiindeksen-resultatfilm',stem.name).replace('/*DATA*/','window.FILM='+json.dumps(m,ensure_ascii=False).replace('<','\\u003c')+';')
 shell=shell.replace('/*INK*/',(assets/'video_ink.js').read_text()).replace('/*SCENES*/',(assets/'results_video.js').read_text()+'\n'+(assets/'research_video_scenes.js').read_text())
 stem.with_suffix('.html').write_text(shell)

def build(name,out,assets):
 scenes=[];start=0
 for kind,title,text,sources in FILMS[name]:
  words=text.split();d=max(13,len(words)/145*60+1)
  scenes.append(dict(kind=kind,title=title,text=text,start=start,duration=d,audio=None,sources=[SOURCES[k] for k in sources],words=[dict(word=w,start=.3+j*(d-.7)/len(words),end=.3+(j+1)*(d-.7)/len(words)) for j,w in enumerate(words)]));start+=d
 m={'schema_version':1,'film':name,'facts':{'month':'oktober 2026'},'scenes':scenes,'duration':start,'timing':'provisional','review':{'status':'pending','draft_label':'Til gjennomgang'},'sources':SOURCES,'source_checked':'2026-10-15'}
 p=out/f'kiindeksen-{name}-film.json';p.write_text(json.dumps(m,ensure_ascii=False,indent=2));p.with_name(p.stem+'-manus.txt').write_text('\n\n'.join(s['text'] for s in scenes));write_html(p,assets)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('film',choices=FILMS);p.add_argument('--out',type=Path,required=True);p.add_argument('--synthesize',action='store_true');p.add_argument('--render',action='store_true');a=p.parse_args()
 if not a.out.is_dir():p.error('Use an existing output directory')
 build(a.film,a.out,Path(__file__).parent)
 if a.synthesize:
  from synthesize_video import synth
  manifest=a.out/f'kiindeksen-{a.film}-film.json'
  synth(manifest,a.out/f'kiindeksen-{a.film}-lyd')
  write_html(manifest,Path(__file__).parent)
 if a.render:subprocess.run(['node',str(Path(__file__).parent/'render_results_video.mjs'),str(a.out.resolve()),f'kiindeksen-{a.film}-film'],check=True)
