// Stable graphite strokes, small offset retracing and clipped crosshatching.
function skLine(pts,g,w=1.6,col='#343434'){for(let pass=0;pass<2;pass++){let d=pts.map(([x,y],i)=>(i?'L':'M')+(x+(pass?.65:0)+Math.sin(x*.07+y*.03+i)*.5)+','+(y+(pass?-.7:0)+Math.cos(y*.05+i)*.5)).join(' ');E('path',{d,fill:'none',stroke:col,'stroke-width':pass?w*.34:w,'stroke-opacity':pass?.32:.9,'stroke-linecap':'round','stroke-linejoin':'round'},g)}}
function skBox(x,y,w,h,g,fill='white'){E('path',{d:`M${x},${y}h${w}v${h}h${-w}Z`,fill,stroke:'none'},g);skLine([[x,y],[x+w,y],[x+w,y+h],[x,y+h],[x,y]],g)}
function skOval(x,y,rx,ry,g){const a=[];for(let i=0;i<=32;i++){const t=i*Math.PI/16;a.push([x+rx*Math.cos(t),y+ry*Math.sin(t)])}skLine(a,g)}
function skShade(x,y,w,h,g,gap=7){for(let d=-h;d<w;d+=gap){let a=Math.max(0,-d),b=Math.min(h,w-d);if(b>a)skLine([[x+d+a,y+a],[x+d+b,y+b]],g,.55,'#777')}}
function skPerson(x,y,g,scale=1,pose='stand'){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skOval(0,0,13,17,p);skLine([[-12,-8],[-6,-18],[4,-19],[12,-10]],p,2.2);skLine([[-6,17],[-6,24],[6,24],[6,17]],p);skLine([[-6,23],[-21,29],[-26,70],[23,70],[20,29],[6,23],[-1,38],[-6,23]],p);skShade(-20,38,12,28,p,5);skLine([[-17,70],[-14,105],[-23,107],[-24,112],[-5,112],[0,75],[9,108],[28,110],[26,105],[18,103],[18,70]],p);skLine([[-19,31],[-33,57],[-20,66]],p);skLine([[20,31],[35,54],[23,64]],p);if(pose==='bag'){skBox(24,62,26,35,p);skLine([[29,62],[29,55],[44,55],[44,62]],p);skShade(26,65,22,30,p,5)}return p}
function skDesk(x,y,g,scale=1,mode='code',progress=1){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skLine([[0,135],[260,135],[254,148],[8,148],[0,135]],p,2);skShade(10,138,240,7,p,8);skLine([[18,149],[14,235],[25,235],[32,149]],p);skLine([[225,149],[239,235],[249,235],[238,149]],p);
 skBox(72,34,117,78,p);skBox(79,41,102,62,p);skLine([[126,112],[126,128],[102,128],[153,128]],p);for(let i=0;i<4;i++)skLine([[88,54+i*11],[88+(i%2?65:42)*progress,54+i*11]],p,1.2,i===1?'#002b7e':'#555');skLine([[85,131],[170,131]],p);for(let i=0;i<10;i++)skLine([[90+i*7,128],[90+i*7,132]],p,.6);
 skOval(212,114,12,4,p);skLine([[200,114],[202,132],[222,132],[224,114]],p);skLine([[225,118],[233,116],[234,127],[224,128]],p);
 skLine([[30,135],[39,74],[21,45],[50,42],[63,65],[39,74]],p);skLine([[33,47],[33,66],[55,64]],p,.7);skShade(38,50,13,10,p,4);
 skLine([[92,177],[165,177],[175,192],[85,192],[92,177]],p);skBox(100,157,60,17,p);skLine([[128,192],[128,224],[101,236],[128,224],[157,236]],p);skOval(100,237,5,5,p);skOval(158,237,5,5,p);
 if(mode==='accounts'){skBox(193,50,48,51,p);for(let j=0;j<3;j++)for(let i=0;i<3;i++)skBox(199+i*11,62+j*10,6,5,p);skShade(197,53,39,5,p,5)}
 if(mode==='home'){skLine([[-30,135],[-45,55],[-31,29],[-18,59],[-30,135],[-11,73],[5,60],[-2,94],[-30,135]],p);skBox(-46,135,36,34,p);skShade(-43,139,30,27,p,6)}return p}
function skWorkshop(x,y,g,scale=1,progress=1){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skBox(74,0,124,125,p);skBox(83,12,105,96,p);for(let r=0;r<3;r++)for(let c=0;c<4;c++){skBox(91+c*22,23+r*25,13,17,p);skLine([[96+c*22,27+r*25],[96+c*22,36+r*25]],p,1.8)}skLine([[139,125],[139,147],[215,147],[215,110+50*progress]],p,2);skLine([[145,125],[145,140],[221,140],[221,110+50*progress]],p,.8);
 skLine([[10,25],[-16,235],[-5,235],[22,25],[10,25]],p);skLine([[43,25],[64,235],[75,235],[55,25],[43,25]],p);for(let i=0;i<6;i++)skLine([[8-i*3,55+i*28],[46+i*3,55+i*28]],p,3);skBox(101,188,126,44,p);skLine([[141,188],[141,174],[185,174],[185,188]],p);skShade(105,201,118,25,p,6);skLine([[111,188],[110,161],[119,154],[128,160],[120,169],[120,188]],p);skLine([[200,188],[203,155],[210,155],[207,188]],p);return p}
function skBuilding(x,y,g,scale=1,door=0){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skBox(0,0,240,260,p);skLine([[-8,0],[120,-35],[249,0]],p);skShade(4,5,13,248,p,8);for(let r=0;r<3;r++)for(let c=0;c<3;c++){skBox(28+c*70,25+r*58,42,39,p);skLine([[28+c*70,44+r*58],[70+c*70,44+r*58]],p,.8);skShade(30+c*70,27+r*58,38,11,p,6)}skBox(89,205,63,55,p);skLine([[90,205],[90+55*door,214],[90+55*door,260],[90,260]],p);skOval(98+45*door,237,2,2,p);skLine([[-15,262],[255,262]],p);return p}
function skConveyor(x,y,g,scale=1,progress=1){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skBox(0,115,260,20,p);for(let i=0;i<12;i++)skOval(9+i*22,125,7,7,p);skLine([[22,136],[12,185],[25,185],[40,136]],p);skLine([[225,136],[240,185],[252,185],[240,136]],p);for(let i=0;i<3;i++){let x=12+i*77+25*progress;skBox(x,65-i*5,57,49+i*5,p);skLine([[x+25,65-i*5],[x+25,114]],p,.8);skShade(x+3,91,51,20,p,7)}return p}
function skPhone(x,y,g,scale=1){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skBox(0,50,120,74,p);skLine([[0,50],[19,20],[100,20],[120,50]],p);skLine([[12,25],[3,15],[7,1],[30,-6],[38,11],[82,11],[90,-6],[113,1],[118,15],[107,25]],p,3);for(let r=0;r<3;r++)for(let c=0;c<3;c++)skBox(32+c*21,58+r*17,13,9,p);skShade(4,82,20,35,p,5);skLine([[118,25],[132,30],[125,40],[136,48],[128,57],[140,66],[131,77],[140,87]],p);return p}

function skArchive(x,y,g,scale=1,progress=1){const p=G(g,{transform:`translate(${x},${y}) scale(${scale})`});skBox(65,0,120,175,p);skShade(70,5,12,163,p,7);for(let i=0;i<5;i++){skBox(88,14+i*30,87,23,p);skLine([[97,25+i*30],[148,25+i*30]],p,.7);skOval(161,25+i*30,3,3,p)}const d=G(p,{transform:`translate(${30*progress},0)`});skBox(0,90,48,65,d);for(let j=0;j<4;j++)skLine([[8,105+j*10],[38,105+j*10]],d,.7);skLine([[190,120],[242,120],[242,160],[190,160],[190,120],[216,141],[242,120]],p);skLine([[40,175],[210,175]],p,2,'#002b7e');return p}

// Narration-cued pencil objects. Chart values remain fixed, only their reveal moves.
const baseDraw=window.drawFilm, baseWindows=window.motionWindows;
const researchCues={research_open:[/imas/,/blandet/,/rekruttering/,/jobbkrise/],flow:[/bedrift/,/slutter/,/jobbsøkere/,/stillingsannonser/],us:[/stanford/,/nitten/,/sparken/,/nyansettelser/,/varselsignal/,/utdanningskontroller/],nordic:[/nordiske/,/norske/,/finske/,/utviklere/,/alle/],causes:[/hjemmekontor/,/renteøkninger/,/pandemien/,/skille/,/eksponering/,/brukes/],aggregate:[/yales/,/sammensetningen/,/bruksmålene/,/dagens/,/bedrift/,/leveranser/,/faktisk/],scenario_open:[/modell/,/usa/,/prognoser/,/antakelsene/,/jobber/],task_machine:[/arbeidsoppgavene/,/hjelpe/,/overta/,/nye/,/uendret/,/bruker/],levers:[/oppgaver/,/bruken/,/produktivitetsgevinstene/,/automatisering/,/nye/,/arbeidsmarkedet/,/annet/],scenario_bars:[/moderate/,/betydelige/,/ekstreme/,/nivå/],transition:[/programmerer/,/elektriker/,/jobbsøking/,/opplæring/,/uten/,/produserer/],distribution:[/bnp/,/ekstreme/,/kapital/,/kunnskapsarbeidernes/],unemployment:[/moderate/,/betydelige/,/ekstreme/,/ledighetsnivåer/,/^uten$/, /sytten/,/gruppen/],limits:[/spart/,/produktivitetsløft/,/automatisering/,/etterspørselen/,/nye/,/finner/,/usa/,/norge/]};
const at=(s,re,f=0)=>cue(s,re,f), step=(s,t,re,f=0,d=1.5)=>ease(t,at(s,re,f),d);
window.motionWindows=s=>researchCues[s.kind]?[[0,2.5],...researchCues[s.kind].map((re,i)=>{const c=at(s,re,i*2);return [Math.max(0,c-.2),Math.min(s.duration,c+3.6)]})]:baseWindows(s);
function coin(x,y,n=3,parent=root){for(let i=0;i<n;i++){ellipse(x,y-i*10,35,11,parent);line([[x-35,y-i*10],[x-35,y+7-i*10]],'#222',1,parent);line([[x+35,y-i*10],[x+35,y+7-i*10]],'#222',1,parent)}}
function worker(x,y,parent=root,scale=1){return skPerson(x,y,parent,scale,'bag')}
function pencil(x,y,parent=root){line([[x,y],[x+55,y-48],[x+61,y-42],[x+5,y+6],[x,y]],'#222',2,parent);line([[x,y],[x-5,y+10],[x+5,y+6]],wine,2,parent)}
function jobSheet(x,y,progress,title,parent=root){const g=G(parent,{transform:`translate(${x},${y+45*(1-progress)})`,opacity:progress});paper(0,0,125,140,g);label(13,29,title,19,wine,g);return g;}
function drawnSheet(x,y,w,h,p,parent=root){const g=G(parent,{opacity:p});paper(x,y,w,h,g);pencil(x+w*p,y+h,g);return g;}
window.drawFilm=function(time){const result=baseDraw(time),s=F.scenes.find(s=>time>=s.start&&time<s.start+s.duration)||F.scenes.at(-1),t=Math.max(0,time-s.start),k=s.kind;
if(!researchCues[k])return result;
const q=re=>step(s,t,re), enter=ease(t,0,1.8);
if(k==='research_open'||k==='scenario_open'){
 drawnSheet(130,180,270,335,enter);label(154,223,k==='research_open'?'Imas & Schaal':'Korinek mfl.',30,wine);skDesk(705,285,root,1.05,'accounts',enter);
 const pats=k==='research_open'?[/blandet/,/rekruttering/,/jobbkrise/]:[/usa/,/prognoser/,/antakelsene/];const labs=k==='research_open'?['Forskning','Nyansettelser','Alle jobber']:['USA','Scenarioer','Antakelser'];
 skBuilding(470,200,G(root,{opacity:q(pats[0])}),.65,q(pats[1]));label(690,215,labs[1],25,wine);label(930,215,labs[2],25,wine);
 worker(580-70*(1-q(pats[1])),480,root,.8);arrow(400,425,680,425);label(485,600,k==='research_open'?'Hva ser vi i dataene?':'Muligheter, ikke prognoser',32,wine);
}
if(k==='flow'){
 skBuilding(810,205,root,1.15,1-q(/slutter/));label(850,170,'Bedriften',30);worker(1050,460,root,.55);
 const halt=q(/slutter/),seek=q(/jobbsøkere/),ads=q(/stillingsannonser/);jobSheet(140+480*(1-halt),300,enter,'Søknad');worker(190+360*seek,490,root,.7);arrow(340,380,780,380);line([[740,330],[740,430]],wine,5*halt+.1);
 jobSheet(200,175,ads,'Ledig jobb');line([[210,235],[310,200]],wine,3, G(root,{opacity:ads}));label(110,610,'Færre innganger til bedriften',32,wine);
}
if(k==='us'){
 label(140,180,'22–25 år · USA · juni 2026',30);const drop=q(/nitten/),hire=q(/nyansettelser/),care=q(/varselsignal/);
 line([[160,470],[1070,470]],gray,1);line([[160,290],[990,290]],gray,2);label(170,262,'Sammenligningsbane',24,gray);
 line([[160,290],[430,290],[700,290+100*drop],[990,290+150*drop]],wine,3);label(920,340+150*drop,'−19 %',40,wine);
 for(let i=0;i<3;i++){worker(230+i*100,500,root,.55);jobSheet(570+i*135,495,hire,'Søknad')}
 label(140,620,care>.1?'Beskrivende forskjell, ikke et årsaksestimat':'Færre nyansettelser er noe annet enn oppsigelser',25,gray);
}
if(k==='nordic'){
 skBuilding(190,225,G(root,{opacity:enter}),.95,q(/norske/));skBuilding(785,225,G(root,{opacity:enter}),.95,q(/finske/));label(200,195,'Norge',35,wine);label(800,195,'Finland',35,wine);
 const one=q(/utviklere/),all=q(/alle/);skDesk(150,450,G(root,{opacity:one}),.65,'code',one);for(let i=0;i<7;i++)worker(570+i*75,510,G(root,{opacity:all}),.55);label(150,620,'Enkeltyrker og hele yrkesfordelingen',29,wine);
}
if(k==='causes'){
 const ps=[q(/hjemmekontor/),q(/renteøkninger/),q(/pandemien/)];skDesk(120,280,root,.9,'home',ps[0]);skBuilding(560,280,root,.68,ps[1]);coin(695,495,2+Math.floor(4*ps[1]));skConveyor(930,320,root,.85,ps[2]);
 ['Hjemmekontor','Renter','Etter pandemien'].forEach((v,i)=>{label(130+i*390,230,v,29);const p=ps[i];arrow(250+i*390,470,250+i*390+(640-250-i*390)*p,470+90*p)});
 const use=q(/brukes/);label(460,540,'Evne',24,wine);label(730,540,'Bruk',24,wine);pencil(580+90*use,540);label(290,620,'Flere forhold kan påvirke de samme yrkene',30,wine);
}
if(k==='aggregate'){
 drawnSheet(130,180,320,360,enter);label(155,225,'Yale Budget Lab',30,wine);label(155,270,'14. oktober 2026',25);
 const use=q(/bruksmålene/),firm=q(/bedrift/),out=q(/leveranser/);skDesk(535,240,root,.8,'accounts',use);skConveyor(850,360,G(root,{opacity:Math.max(firm,out)}),1,out);
 worker(680,460,root,.7);label(130,610,out>.1?'Spart tid kan brukes til flere leveranser':'Dagens data måler ikke framtiden',30,wine);
}
if(k==='task_machine'){
 const stages=[q(/uendret/),q(/hjelpe/),q(/overta/),q(/nye/)];const labs=['Uendret','KI hjelper','KI overtar','Nye oppgaver'];
 stages.forEach((p,i)=>{label(120+i*280,215,labs[i],27,wine);const g=G(root,{opacity:p});if(i===0)skWorkshop(140,300,g,.75,p);if(i===1)skDesk(410,300,g,.85,'accounts',p);if(i===2)skArchive(700,315,g,.9,p);if(i===3){skDesk(990,300,g,.75,'code',p);pencil(1040,540,g)}});
 const use=q(/bruker/);arrow(250,600,250+800*use,600);label(200,620,'Teknisk evne må tas i bruk',28,wine);
}
if(k==='levers'){
 const pats=[/oppgaver/,/bruken/,/produktivitetsgevinstene/,/automatisering/,/nye/,/arbeidsmarkedet/];['Evne','Bruk','Produktivitet','Automatisering','Nye oppgaver','Omstilling'].forEach((v,i)=>{let x=140+(i%3)*390,y=230+Math.floor(i/3)*230,p=q(pats[i]);label(x,y,v,28);line([[x,y+55],[x+215,y+55]],gray,2);ellipse(x+25+160*p,y+55,12,18);pencil(x+25+160*p,y+50);});
 worker(880+140*q(/annet/),585,root,.5);
}
if(k==='scenario_bars'){
 const vals=[1.6,8.3,32.4],pats=[/moderate/,/betydelige/,/ekstreme/];vals.forEach((v,i)=>{let x=210+i*350,p=q(pats[i]),h=v/35*300*p;box(x,510-h,130,h);if(h>5)skShade(x+5,515-h,120,Math.max(0,h-10),root,10);label(x-20,555,['Moderat','Betydelig','Ekstremt'][i],30);label(x-10,190,fmt(v)+' %',40,wine);pencil(x+130,510-h)});label(140,625,q(/nivå/)>.1?'BNP-nivå i 2030, ikke årlig vekst':'USA · relativt til samme økonomi uten KI',27,gray);
}
if(k==='transition'){
 skDesk(120,265,root,.95,'code',q(/programmerer/));skWorkshop(980,270,root,.9,q(/elektriker/));label(130,210,'Programmerer',30);label(955,210,'Elektriker',30);arrow(380,390,970,390);
 const search=q(/jobbsøking/),learn=q(/opplæring/),wait=q(/uten/);worker(300+390*search+130*learn,420,root,.8);jobSheet(470,225,search,'Søknad');jobSheet(670,225,learn,'Opplæring');
 ellipse(720,570,38,38);line([[720,570],[720+26*Math.sin(wait*4),570-26*Math.cos(wait*4)]],wine,2);label(200,615,'Omstilling tar tid, også når produksjonen vokser',28,wine);
}
if(k==='distribution'){
 skDesk(110,285,root,.85,'accounts',q(/bnp/));worker(400,390,root,.8);skBuilding(865,290,root,.6,q(/kapital/));const cap=q(/kapital/),wage=q(/kunnskapsarbeidernes/);coin(300,510,4-Math.floor(wage));coin(900,510,4+Math.floor(8*cap));
 label(130,240,'Arbeidsinntekt',35);label(760,240,'Kapitalinntekt',35);const g=G(root,{opacity:cap});ellipse(400+350*cap,390-80*Math.sin(cap*Math.PI),25,9,g);arrow(430,430,750,430);label(230,620,'Større produksjon kan fordeles ulikt',32,wine);
}
if(k==='unemployment'){
 const vals=[3.9,4.6,11.9],pats=[/moderate/,/betydelige/,/ekstreme/];label(120,155,'Samlet ledighet · USA · 2030',28,gray);
 vals.forEach((v,i)=>{let x=190+i*300,p=q(pats[i]),h=v/12*260*p;box(x,485-h,120,h);if(h>5)skShade(x+5,490-h,110,Math.max(0,h-10),root,9);label(x-15,535,['Moderat','Betydelig','Ekstremt'][i],26);label(x,200,fmt(v)+' %',36,wine);pencil(x+120,485-h)});
 const baseline=q(/^uten$/);line([[145,485-3.8/12*260],[1080,485-3.8/12*260]],gray,baseline*2+.1);label(160,580,baseline>.1?'Uten KI: 3,8 % samlet ledighet':'Nivåer, ikke økninger i prosentpoeng',26,gray);
 const cg=q(/sytten/);if(cg>0){const g=G(root,{opacity:cg});E('rect',{x:100,y:110,width:1100,height:480,fill:'white'},g);worker(210,310,g,1.1);skDesk(315,265,g,1.0,'code',cg);label(660,300,'17,9 %',68,wine,g);label(620,370,'uten arbeid i det ekstreme scenarioet',25,'#222',g);label(170,530,'Blant dem som startet i kunnskapsyrker',31,wine,g)}
 label(150,620,'Scenarioer, ikke prognoser for Norge',27,wine);
}
if(k==='limits'){
 const saved=q(/spart/),demand=q(/etterspørselen/),tasks=q(/nye/),search=q(/finner/);jobSheet(120,220,enter,'Oppgave');ellipse(390,320,48,48);line([[390,320],[390+32*Math.sin(saved*4),320-32*Math.cos(saved*4)]],wine,2);label(320,410,'Spart tid',28,wine);
 arrow(460,320,740,240);arrow(460,340,740,480);jobSheet(820,190,demand,'Leveranser');jobSheet(1000,190,tasks,'Ny oppgave');worker(770+250*search,470,root,.8);label(740,580,'Jobbsøking og omstilling',28,wine);label(120,615,q(/usa/)>.1?'USA: scenarioene kan ikke overføres direkte til Norge':'Spart tid er ikke det samme som tapte jobber',28,wine);
}
return result;
};drawFilm(0);
