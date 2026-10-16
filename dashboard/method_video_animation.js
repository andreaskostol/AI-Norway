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

// Sample the original Suveren object movements at the words that explain them.
const methodPatterns=[[/^en$/, /skriving/, /eksponering/],[/pressemeldinger/,/henvendelser/,/relasjoner/],[/null/,/^ett$/, /halvt/],[/pressemeldinger/,/mediehenvendelser/,/relasjoner/],[/kjerneoppgaver/,/dobbelt/,/deler/],[/nyheter/,/direkte/,/integrasjoner/],[/mouchel/,/større/,/sju/],[/kildeyrkene/,/kobler/,/norske/],[/prikk/,/ordner/,/fem/],[/resultatet/,/sannsynligheten/,/arbeidsgiver/]];
window.methodCueTimes=(s,i)=>methodPatterns[i].map((p,j)=>s.words.find(w=>p.test(w.word.toLowerCase()))?.start??[0,s.duration*.3,s.duration*.65][j]);
window.motionWindows=s=>[[0,3.2],...window.methodCueTimes(s,window.FILM.scenes.indexOf(s)).map(t=>[Math.max(0,t-.1),t+2.2])];
const methodDraw=window.drawFilm;let inkScene=-1,inkPaths=[];
window.drawFilm=function(time){let i=window.FILM.scenes.findIndex(s=>time>=s.start&&time<s.start+s.duration);if(i<0)i=window.FILM.scenes.length-1;const s=window.FILM.scenes[i],t=time-s.start;const result=methodDraw(time);
 if(inkScene!==i){inkScene=i;
  if(i===1||i===3){
   const texts=Array.from(document.querySelectorAll('#s text'));
   ['pressemeldinger','mediehenvendelser','relasjoner'].forEach((word,j)=>{const node=texts.find(e=>e.textContent.toLowerCase()===word);if(!node)return;const pg=node.parentNode,gg=G(pg,{'data-pencil-occupation':'true'});E('rect',{x:29,y:217,width:421,height:i===3?178:275,fill:'white'},gg);
    if(j===0)skDesk(100,220,gg,i===3?.7:1,'code',1);
    if(j===1)skPhone(150,240,gg,i===3?1:1.4);
    if(j===2){skPerson(130,250,gg,i===3?.9:1.25);skPerson(310,250,gg,i===3?.9:1.25);skLine([[151,290],[218,320],[285,290]],gg,2,'#002b7e');}
   });
  }
  if(i===5){const texts=Array.from(document.querySelectorAll('#s text'));const node=texts.find(e=>e.textContent==='Nyheter');if(node){const pg=node.parentNode,g=G(pg,{});E('rect',{x:28,y:100,width:433,height:215,fill:'white'},g);skPhone(70,130,g,1.1);skBox(260,125,150,155,g);skShade(270,135,130,35,g,6);for(let j=0;j<5;j++)skLine([[270,188+j*14],[390,188+j*14]],g,.7)}}
  inkPaths=Array.from(document.querySelectorAll('#s path')).filter(e=>e.getAttribute('stroke')&&e.getAttribute('stroke')!=='none').map(e=>[e,e.getTotalLength()]);}
 for(const [e,len] of inkPaths){const p=Math.min(1,t/2.7);e.style.strokeDasharray=p<1?`${len} ${len}`:'';e.style.strokeDashoffset=p<1?String(len*(1-p)):'';}
 return result;
};window.drawFilm(0);
