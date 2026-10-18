"""Rebuild approved Studio scripts with clone speech, silence edits and Bokmål captions.
Raw generated audio remains in the chosen existing cache directory. Originals are preserved.
Set PLAYWRIGHT_MODULE and CHROME_CHANNEL when using an existing browser installation.
"""
import sys,json,subprocess,re,wave,concurrent.futures
from pathlib import Path
import argparse,os,shutil
D=Path(__file__).resolve().parent; R=D.parent
parser=argparse.ArgumentParser(description='Rebuild Norwegian Studio films with the configured personal clone. No publication.')
parser.add_argument('--out',type=Path,required=True,help='Existing output/cache directory')
parser.add_argument('--synthesize',action='store_true',help='Explicitly authorize the configured ElevenLabs API calls')
parser.add_argument('--render',action='store_true')
args=parser.parse_args(); P=args.out.resolve()
if not P.is_dir(): parser.error('Output directory must already exist')
if not args.synthesize and not args.render: parser.error('Choose --synthesize and/or --render')
sys.path.insert(0,str(D))
from synthesize_video import synth
from build_research_video import write_html

def render(out):
 validation=out.with_name(out.stem+'-validation.json')
 if validation.exists():validation.unlink()
 subprocess.run(['node',str(D/'render_results_video.mjs'),str(P),out.stem],check=True)

def build(stem):
 src=R/(stem+'.json'); out=P/(stem+'-andreas.json')
 if not args.synthesize:
  if not out.exists():raise FileNotFoundError(out)
  render(out);return
 m=json.loads(src.read_text());m['scenes']=[x for x in m['scenes'] if x['kind']!='disclosure'];out.write_text(json.dumps(m,ensure_ascii=False))
 from synthesize_video import VOICE
 prefix=P/(stem+'-andreas-'+VOICE+'-lyd')
 # Reuse old cache only when its recorded voice matches the configured clone.
 for old in P.glob(stem+'-andreas-lyd-*.json'):
  if json.loads(old.read_text()).get('voice_id')!=VOICE:continue
  index=old.stem.rsplit('-',1)[-1];new=Path(str(prefix)+'-'+index)
  for suffix in ['.json','.mp3','.wav']:
   a=old.with_suffix(suffix);b=new.with_suffix(suffix)
   if a.exists() and not b.exists():shutil.copy2(a,b)
 synth(out,prefix)
 m=json.loads(out.read_text());total=0;cuts=0
 for i,s in enumerate(m['scenes']):
  src=s['audio'];log=subprocess.run(['ffmpeg','-hide_banner','-i',src,'-af','silencedetect=noise=-38dB:d=0.35','-f','null','-'],capture_output=True,text=True).stderr
  aa=list(map(float,re.findall(r'silence_start: ([\d.]+)',log)));bb=list(map(float,re.findall(r'silence_end: ([\d.]+)',log)));remove=[]
  for a,b in zip(aa,bb):
   if b-a<.35:continue
   prev=[w for w in s['words'] if w['end']<=a+.08];keep=.4 if prev and prev[-1]['word'].endswith(('.','?','!')) else .17
   if b-a <= keep:continue
   remove.append((a+keep/2,b-keep/2))
  def mapped(t):return t-sum(max(0,min(t,b)-a) for a,b in remove if t>a)
  with wave.open(src,'rb') as w:params=w.getparams();data=w.readframes(w.getnframes())
  step=params.sampwidth*params.nchannels;rate=params.framerate;pieces=[];cur=0
  for a,b in remove:pieces.append(data[round(cur*rate)*step:round(a*rate)*step]);cur=b
  pieces.append(data[round(cur*rate)*step:]);audio=b''.join(pieces);dest=P/f'{stem}-andreas-paced-{i:02}.wav'
  with wave.open(str(dest),'wb') as w:w.setparams(params);w.writeframes(audio)
  for w in s['words']:w['start']=mapped(w['start']);w['end']=mapped(w['end'])
  dur=round((len(audio)/step/rate+.12)*25)/25;s.update(start=total,duration=dur,audio=str(dest));total+=dur;cuts+=len(remove)
 m.update(duration=total,pause_edit={'cuts':cuts,'method':'Silence-only cuts; speech speed unchanged; caption times remapped'})
 out.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 out.with_name(out.stem+'-manus.txt').write_text('\n\n'.join(x['text'] for x in m['scenes']))
 out.with_name(out.stem+'-talemanus.txt').write_text('\n\n'.join(x['spoken_text'] for x in m['scenes']))
 if 'metode' in stem:
  h=(R/'kiindeksen-video-motion.html').read_text()
  h=h.replace('<svg id="s"','<div id="stage"><svg id="s"',1).replace('</svg>','</svg><div id="caption"></div></div>',1)
  h+='<style>#stage{position:relative;width:1280px;height:720px;background:white}#s{width:1120px;height:630px;margin-left:80px}#caption{position:absolute;left:90px;top:650px;width:1104px;white-space:nowrap;font:38px "Courier New",monospace;color:#641b35}</style>'
  h+='<script>window.FILM='+json.dumps(m,ensure_ascii=False)+';let previousScene=-1;window.drawFilm=function(time){const F=window.FILM;let i=F.scenes.findIndex(s=>time>=s.start&&time<s.start+s.duration);if(i<0)i=F.scenes.length-1;const s=F.scenes[i],t=time-s.start;if(previousScene!==i){window.makeMotion("no",i);previousScene=i}window.updateMotion(t,s.duration);let j=s.words.findLastIndex(w=>w.start<=t),first=Math.max(0,j-5),c=document.getElementById("caption");c.textContent=j<0?"":s.words.slice(first,j+1).map(w=>w.word).join(" ");while(c.scrollWidth>1104&&first<j){first++;c.textContent=s.words.slice(first,j+1).map(w=>w.word).join(" ")}return {scene:i,caption:c.textContent}};window.drawFilm(0);</script>'
  for color in ['#641b35','#490707','#8c1515','#1f4e8c','#b23a2a']:h=h.replace(color,'#002b7e')
  h=h.replace("'Noteworthy','Chalkboard SE','Marker Felt',cursive","-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif")
  h=h.replace('"Courier New",monospace','-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif')
  h=h.replace('const a=motionEase(t/1.4),b=motionEase((t-d*.30)/1.4),c=motionEase((t-d*.65)/1.4)', 'const cs=window.methodCueTimes?window.methodCueTimes(window.FILM.scenes[scene],scene):[0,d*.30,d*.65],a=motionEase((t-cs[0])/1.8),b=motionEase((t-cs[1])/1.8),c=motionEase((t-cs[2])/1.8)')
  h+='<script>'+ (D/'method_video_animation.js').read_text()+'</script>'
  out.with_suffix('.html').write_text(h)
 else:write_html(out,D)
 if args.render:render(out)
 print(stem,'READY',total,'cuts',cuts,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(build,['kiindeksen-metodefilm','kiindeksen-imas-film','kiindeksen-anthropic-film']))
