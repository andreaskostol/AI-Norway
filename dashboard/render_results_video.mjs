import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {createRequire} from 'node:module';import {spawnSync} from 'node:child_process';import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=path.resolve(process.argv[2]),stem=path.join(out,process.argv[3]||'kiindeksen-resultatfilm'),film=JSON.parse(fs.readFileSync(stem+'.json'));
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'kiindeksen-render-'));
const run=args=>{const r=spawnSync('ffmpeg',['-y','-v','error',...args],{encoding:'utf8'});if(r.status!==0)throw Error(r.stderr)};
const quoted=p=>"'"+p.replaceAll("'","'\\''")+"'";
let browser,completed=false;const checks=[];
try{
 browser=await chromium.launch({headless:true,...(process.env.CHROME_CHANNEL?{channel:process.env.CHROME_CHANNEL}:{})});
 const page=await browser.newPage({viewport:{width:1280,height:850},deviceScaleFactor:1});let errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(stem+'.html').href);await page.evaluate(()=>document.fonts.ready);
 const clips=[];
 for(let i=0;i<film.scenes.length;i++){
  const s=film.scenes[i];let times=[0,s.duration];const windows=await page.evaluate(i=>window.motionWindows?window.motionWindows(window.FILM.scenes[i]):[[0,4]],i);for(const [a,b] of windows)for(let t=a;t<=Math.min(b,s.duration);t+=.08)times.push(t);for(const w of s.words)times.push(Math.ceil(w.start*25)/25);
  times=[...new Set(times.filter(t=>t<=s.duration).map(t=>Math.round(t*25)/25))].sort((a,b)=>a-b);let concat=[];
  for(let j=0;j<times.length;j++){
   const t=times[j],result=await page.evaluate(t=>window.drawFilm(t),s.start+Math.min(t,s.duration-.001));
   const bounds=await page.locator('#caption').evaluate(e=>({width:e.scrollWidth,height:e.scrollHeight}));
   if(bounds.width>1104||bounds.height>65)throw Error('Caption overflow');
   const file=path.join(tmp,`${i}-${j}.jpg`);await page.locator('#stage').screenshot({path:file,type:'jpeg',quality:93});
   concat.push('file '+quoted(file));if(j<times.length-1)concat.push('duration '+(times[j+1]-t).toFixed(5));
   if(j===times.length-1)fs.copyFileSync(file,path.join(out,`${path.basename(stem)}-scene-${i}.jpg`));
  }
  if(errors.length)throw Error(errors.join('\n'));
  const list=path.join(tmp,`${i}.txt`),clip=path.join(tmp,`${i}.mp4`);fs.writeFileSync(list,concat.join('\n')+'\n');
  const audio=s.audio?['-i',s.audio]:['-f','lavfi','-i','anullsrc=r=48000:cl=mono'];
  run(['-f','concat','-safe','0','-i',list,...audio,'-vf','fps=25,format=yuv420p','-t',String(s.duration),'-c:v','libx264','-preset','fast','-crf','20','-threads','3','-c:a','aac','-ar','48000','-ac','1','-af','apad',clip]);clips.push(clip);checks.push({scene:i,captionBounds:'passed',frames:times.length});console.log('Rendered scene',i+1,'/',film.scenes.length);
 }
 const list=path.join(tmp,'film.txt');fs.writeFileSync(list,clips.map(p=>'file '+quoted(p)).join('\n'));
 run(['-f','concat','-safe','0','-i',list,'-c','copy','-movflags','+faststart',stem+'.mp4']);
 run(['-i',stem+'.mp4','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-ar','48000','-b:a','160k','-movflags','+faststart',stem+'-leveled.mp4']);fs.renameSync(stem+'-leveled.mp4',stem+'.mp4');
 run(['-i',stem+'.mp4','-f','null','-']);fs.writeFileSync(stem+'-validation.json',JSON.stringify({fullDecode:'passed',timing:film.timing,checks},null,2));
 completed=true;
}finally{let closed=true;if(browser){let timer;closed=await Promise.race([browser.close().then(()=>true),new Promise(resolve=>{timer=setTimeout(()=>resolve(false),5000)})]);clearTimeout(timer)}fs.rmSync(tmp,{recursive:true,force:true});if(!closed)process.exit(completed?0:1)}
