"""Explicitly invoked ElevenLabs synthesis. Never called by the default offline build."""
import argparse,base64,hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
CONFIG=json.loads((Path(__file__).parent/'video_voice.json').read_text())
VOICE=CONFIG['voice_id']
def speech_plan(display):
    tokens=display.split();pieces=[];spans=[]
    for token in tokens:
        pattern=r'\b(?:'+'|'.join(re.escape(k) for k in sorted(CONFIG['spoken_replacements'],key=len,reverse=True))+r')\b'
        spoken=re.sub(pattern,lambda m:CONFIG['spoken_replacements'][m.group()],token)
        begin=len(pieces);pieces.extend(spoken.split());spans.append((begin,len(pieces)))
    return ' '.join(pieces),tokens,spans

def display_alignment(words,tokens,spans):
    return [{'word':token,'start':words[a]['start'],'end':words[b-1]['end']} for token,(a,b) in zip(tokens,spans)]
def synth(manifest,prefix):
 m=json.loads(manifest.read_text());total=0
 for i,s in enumerate(m['scenes']):
  display=s.get('display_text',s['text']);text,tokens,spans=speech_plan(display);base=Path(str(prefix)+f'-{i:02d}');wav=base.with_suffix('.wav');meta=base.with_suffix('.json')
  body={'text':text,'model_id':CONFIG['model_id'],'language_code':CONFIG['language_code'],'voice_settings':CONFIG['voice_settings']}
  digest=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
  if not (meta.exists() and wav.exists() and json.loads(meta.read_text()).get('request_sha256')==digest):
   key=os.environ.get('ELEVENLABS_API_KEY') or (Path.home()/'.config/elevenlabs/key').read_text().strip()
   req=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128',data=json.dumps(body).encode(),headers={'xi-api-key':key,'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=180) as r:d=json.load(r)
   a=d['alignment'];chars=''.join(a['characters'])
   if chars!=text:raise ValueError('Provider alignment differs from transcript. Inspect before rendering.')
   words=[{'word':w.group(),'start':a['character_start_times_seconds'][w.start()],'end':a['character_end_times_seconds'][w.end()-1]} for w in re.finditer(r'\S+',text)]
   mp3=base.with_suffix('.mp3');mp3.write_bytes(base64.b64decode(d['audio_base64']))
   subprocess.run(['ffmpeg','-y','-v','error','-i',str(mp3),'-ar','48000','-ac','1',str(wav)],check=True)
   meta.write_text(json.dumps({'request_sha256':digest,'voice_id':VOICE,'words':words},ensure_ascii=False,indent=2))
  words=json.loads(meta.read_text())['words'];duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(wav)]))
  if [w['word'] for w in words]!=text.split():raise ValueError('Cached speech transcript mismatch')
  words=display_alignment(words,tokens,spans)
  s.update(text=display,display_text=display,spoken_text=text,audio=str(wav.resolve()),words=words,duration=round((duration+.3)*25)/25,start=total);total+=s['duration'];print(i,'ready',flush=True)
 m.update(duration=total,timing='aligned',voice={'name':CONFIG['name'],'id':VOICE,'model':CONFIG['model_id'],**CONFIG['voice_settings']},primary_language=CONFIG['primary_language'],pronunciation_notes=CONFIG.get('pronunciation_notes',{}))
 manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 print('Total',total,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('prefix',type=Path);a=p.parse_args();synth(a.manifest,a.prefix)
