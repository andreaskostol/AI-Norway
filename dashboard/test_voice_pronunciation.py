import json,sys,wave,math,unittest,tempfile,os
from pathlib import Path
from array import array
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D))
from voice_pronunciation import apply_approved_pronunciation
from synthesize_video import speech_plan
class PronunciationTests(unittest.TestCase):
 def test_sentence_silence_and_timing(self):
  rate=48000;pcm=array('h',[0]*rate*3)
  for a,b in [(.1,.5),(1.1,1.5)]:
   for i in range(round(a*rate),round(b*rate)):pcm[i]=round(3000*math.sin(2*math.pi*180*i/rate))
  p=Path(tempfile.gettempdir()) / ('ki-pronunciation-test-'+str(os.getpid())+'.wav')
  with wave.open(str(p),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())
  words=[{'word':'kå-Í?','start':.1,'end':.8},{'word':'neste','start':1.1,'end':1.5}]
  c=json.loads((D/'video_voice.json').read_text());out,adjusted,report=apply_approved_pronunciation(p,words,c,D)
  with wave.open(str(out),'rb') as w:new=array('h',w.readframes(w.getnframes()))
  shift=round((adjusted[1]['start']-1.1)*rate)
  self.assertEqual(new[round(.8*rate)+shift:round(1.1*rate)+shift].tobytes(),pcm[round(.8*rate):round(1.1*rate)].tobytes())
  self.assertAlmostEqual(adjusted[1]['end']-adjusted[1]['start'],.4)
  self.assertEqual(len(report['replacements']),1)
  self.assertGreater(adjusted[1]['start']-adjusted[0]['end'],.29)
  p.unlink();out.unlink();out.with_suffix('.json').unlink()
 def test_caption_mapping_for_compounds(self):
  spoken,tokens,spans=speech_plan('KI-agenter og KI-indeksen.')
  self.assertEqual(tokens,['KI-agenter','og','KI-indeksen.'])
  self.assertTrue(spoken.startswith('kå-Í agente'))
  self.assertEqual(spans[0],(0,2))
 def test_hash_guard(self):
  c=json.loads((D/'video_voice.json').read_text());c['approved_pronunciation_audio']['sha256']='wrong'
  with self.assertRaises(ValueError):apply_approved_pronunciation(Path('unused.wav'),[],c,D)
unittest.main()
