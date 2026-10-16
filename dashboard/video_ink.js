// Tegnemotoren fra ../stil/A/stil.html (alt foran VISNING). Kopiert 23.9.2026. Ikke rediger: legg egen kode i egne filer.

/* =====================================================================
   STIL A: PENN OG TUSJ
   Alt er tegnet i kode. Linje, skravur og prikking gjør arbeidet.
   Ingen flate fargefyll. Hvitt papir, svart blekk.
   ===================================================================== */
const NS='http://www.w3.org/2000/svg';
const svg=document.getElementById('s');
let root, defs, cid=0, seed=7;
let U=1;                       // enhetsfaktor: px -> lokale enheter i gjeldende gruppe
function srand(s){seed=(s>>>0)||1;}
function rnd(){seed^=seed<<13;seed>>>=0;seed^=seed>>>17;seed^=seed<<5;seed>>>=0;return seed/4294967296;}
function R(a,b){return a+(b-a)*rnd();}
function clamp(v,a=0,b=1){return v<a?a:v>b?b:v;}
function E(tag,attrs,parent){const e=document.createElementNS(NS,tag);for(const k in attrs){if(attrs[k]!=null)e.setAttribute(k,attrs[k]);}(parent||root).appendChild(e);return e;}
function G(parent,attrs){return E('g',attrs||{},parent);}

/* ---------- kurver og punkter ---------- */
function catmull(pts,closed,step){
  step=(step||5)*U; const n=pts.length,out=[];
  const P=i=>pts[closed?((i%n)+n)%n:Math.max(0,Math.min(n-1,i))];
  const segs=closed?n:n-1;
  for(let i=0;i<segs;i++){
    const p0=P(i-1),p1=P(i),p2=P(i+1),p3=P(i+2);
    const L=Math.hypot(p2[0]-p1[0],p2[1]-p1[1]);const m=Math.max(2,Math.ceil(L/step));
    for(let k=0;k<m;k++){const t=k/m,t2=t*t,t3=t2*t;
      out.push([0.5*((2*p1[0])+(-p0[0]+p2[0])*t+(2*p0[0]-5*p1[0]+4*p2[0]-p3[0])*t2+(-p0[0]+3*p1[0]-3*p2[0]+p3[0])*t3),
                0.5*((2*p1[1])+(-p0[1]+p2[1])*t+(2*p0[1]-5*p1[1]+4*p2[1]-p3[1])*t2+(-p0[1]+3*p1[1]-3*p2[1]+p3[1])*t3)]);}
  }
  out.push(closed?out[0].slice():pts[n-1].slice());
  return out;
}
function linePts(pts,closed,step){
  step=(step||5)*U; const out=[],n=pts.length,segs=closed?n:n-1;
  for(let i=0;i<segs;i++){const a=pts[i],b=pts[(i+1)%n];const L=Math.hypot(b[0]-a[0],b[1]-a[1]);const m=Math.max(1,Math.ceil(L/step));
    for(let k=0;k<m;k++){const t=k/m;out.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]);}}
  out.push(closed?pts[0].slice():pts[n-1].slice());
  return out;
}
function noisy(dense,amp){
  amp*=U; if(!amp)return dense;
  const f1=R(0.015,0.04)/U,f2=R(0.07,0.14)/U,p1=R(0,6.28),p2=R(0,6.28);
  let s=0;const out=[];
  for(let i=0;i<dense.length;i++){
    const a=dense[Math.max(0,i-1)],b=dense[Math.min(dense.length-1,i+1)];
    const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy)||1;
    if(i>0)s+=Math.hypot(dense[i][0]-dense[i-1][0],dense[i][1]-dense[i-1][1]);
    const o=amp*(Math.sin(s*f1+p1)+0.45*Math.sin(s*f2+p2));
    out.push([dense[i][0]-dy/L*o,dense[i][1]+dx/L*o]);
  }
  return out;
}
function dstr(d,closed){let s='M'+d[0][0].toFixed(1)+' '+d[0][1].toFixed(1);for(let i=1;i<d.length;i++)s+='L'+d[i][0].toFixed(1)+' '+d[i][1].toFixed(1);return closed?s+'Z':s;}
function shape(pts,o){o=o||{};const d=o.curve?catmull(pts,true,o.step):linePts(pts,true,o.step);return dstr(noisy(d,o.amp||0),true);}

/* ---------- pennestrøk med varierende bredde (fylt polygon) ---------- */
function ink(pts,o,parent){
  o=o||{};
  const dense=o.curve?catmull(pts,o.closed,o.step):linePts(pts,o.closed,o.step);
  const p=noisy(dense,o.amp==null?0.5:o.amp);
  const n=p.length; if(n<2)return;
  const w=(o.w||2)*U; const taper=(o.taper==null?1:o.taper)*U*10;
  const cum=[0];let tot=0;for(let i=1;i<n;i++){tot+=Math.hypot(p[i][0]-p[i-1][0],p[i][1]-p[i-1][1]);cum.push(tot);}
  if(tot<=0)return;
  const f=R(0.006,0.02)/U,ph=R(0,6.28),f2=R(0.03,0.06)/U,ph2=R(0,6.28);
  const L=[],Rr=[];
  for(let i=0;i<n;i++){
    const a=p[Math.max(0,i-1)],b=p[Math.min(n-1,i+1)];
    let dx=b[0]-a[0],dy=b[1]-a[1];const l=Math.hypot(dx,dy)||1;dx/=l;dy/=l;
    const t=cum[i]/tot;
    let wd=o.wf?o.wf(t)*U:w*(0.62+0.38*Math.sin(cum[i]*f+ph)+0.12*Math.sin(cum[i]*f2+ph2));
    if(taper>0&&!o.closed){const e=Math.min(1,cum[i]/taper,(tot-cum[i])/taper);wd*=0.12+0.88*Math.sqrt(Math.max(0,e));}
    wd=Math.max(wd,0.25*U);
    L.push([p[i][0]-dy*wd/2,p[i][1]+dx*wd/2]);Rr.push([p[i][0]+dy*wd/2,p[i][1]-dx*wd/2]);
  }
  const d=dstr(L.concat(Rr.reverse()),true);
  return E('path',{d,fill:'#000',stroke:'none'},parent);
}
/* tynn strek, konstant bredde */
function stroke(pts,o,parent){
  o=o||{};
  const dense=o.curve?catmull(pts,o.closed,o.step):linePts(pts,o.closed,o.step);
  const p=noisy(dense,o.amp==null?0.4:o.amp);
  return E('path',{d:dstr(p,o.closed),fill:'none',stroke:o.col||'#000','stroke-width':((o.w||1)*U).toFixed(2),'stroke-linecap':'round','stroke-linejoin':'round'},parent);
}
function black(pts,o,parent){o=o||{};return E('path',{d:shape(pts,o),fill:'#000'},parent);}
function white(pts,o,parent){o=o||{};return E('path',{d:shape(pts,o),fill:'#fff'},parent);}

/* ---------- skravur og prikking, klippet til en form ---------- */
function bbox(d){const t=E('path',{d},svg);const b=t.getBBox();t.remove();return b;}
function clipG(d,parent,attrs){const id='cp'+(cid++);const cp=E('clipPath',{id},defs);E('path',{d},cp);return G(parent,Object.assign({'clip-path':`url(#${id})`},attrs||{}));}
/* Runde 8 (5.10.2026), lysplanen: når TRE_VERDIER er sann, blir skravur med tonefunksjon (dens) og grov strek
   (amp 0,8 og mer, altså vegger, mørke og vignett) delt i faste flater: strekene står hele der tonen er over
   terskelen (standard 0,35), ellers ingen. Ett lag gir mellomtonen i lange strøk, to lag i kryss gir det mørke.
   Da forsvinner støvet av korte, spredte strøk. Ansikter, hår og klær (lav amp) er som før. Tilfeldighetene
   trekkes som før, så resten av tegningen ikke flytter seg. */
let TRE_VERDIER=false;
function hatch(d,o,parent){
  o=o||{};
  const tre=TRE_VERDIER&&o.dens&&o.tre!==false&&(o.amp==null?0.5:o.amp)>=0.8, terskel=o.terskel==null?0.35:o.terskel;
  const gap=(o.gap||6)*U,w=(o.w||1)*U,amp=(o.amp==null?0.5:o.amp)*U,step=(o.step||8)*U,ang=o.ang==null?45:o.ang;
  const bb=bbox(d);
  const g=clipG(d,parent,{fill:'none',stroke:o.col||'#000','stroke-linecap':'round'});
  const cx=bb.x+bb.width/2,cy=bb.y+bb.height/2,r=Math.hypot(bb.width,bb.height)/2+gap;
  const a=ang*Math.PI/180,dx=Math.cos(a),dy=Math.sin(a),nx=-dy,ny=dx;
  for(let off=-r;off<=r;off+=gap*R(0.8,1.2)){
    const x0=cx+nx*off-dx*r,y0=cy+ny*off-dy*r;
    let path='',on=false;const ph=R(0,6.28),fq=R(0.01,0.03)/U,ph2=R(0,6.28),fq2=R(0.05,0.1)/U;
    const len=2*r;
    for(let s=0;s<=len;s+=step){
      const wob=amp*(Math.sin(s*fq+ph)+0.4*Math.sin(s*fq2+ph2));
      const px=x0+dx*s+nx*wob,py=y0+dy*s+ny*wob;
      const tilf=o.dens?rnd():0;
      const keep=!o.dens||(tre?o.dens(px,py)>terskel:o.dens(px,py)>tilf);
      if(keep){path+=(on?'L':'M')+px.toFixed(1)+' '+py.toFixed(1);on=true;}else on=false;
    }
    if(path)E('path',{d:path,'stroke-width':(w*R(0.75,1.25)).toFixed(2)},g);
  }
  return g;
}
function cross(d,o,parent){o=o||{};hatch(d,Object.assign({},o,{ang:o.ang==null?40:o.ang}),parent);hatch(d,Object.assign({},o,{ang:(o.ang==null?40:o.ang)+(o.d2||55),gap:(o.gap||6)*(o.g2||1.15)}),parent);}
function stipple(d,o,parent){
  o=o||{};const n=o.n||400,r0=(o.r||1)*U;
  const bb=bbox(d);const g=clipG(d,parent,{fill:o.col||'#000'});
  for(let i=0;i<n;i++){const x=bb.x+rnd()*bb.width,y=bb.y+rnd()*bb.height;
    if(o.dens&&o.dens(x,y)<rnd())continue;
    E('circle',{cx:x.toFixed(1),cy:y.toFixed(1),r:(r0*R(0.6,1.4)).toFixed(2)},g);}
  return g;
}
/* små korte strøk i en form (skjegg, hår, gress) */
function strokesIn(d,o,parent){
  o=o||{};const n=o.n||200,len=(o.len||6)*U,w=(o.w||1)*U;
  const bb=bbox(d);const g=clipG(d,parent,{fill:'none',stroke:o.col||'#000','stroke-linecap':'round'});
  for(let i=0;i<n;i++){const x=bb.x+rnd()*bb.width,y=bb.y+rnd()*bb.height;
    if(o.dens&&o.dens(x,y)<rnd())continue;
    const a=(o.angf?o.angf(x,y):(o.ang||90))*Math.PI/180+R(-0.2,0.2);
    const l=len*R(0.6,1.3);const cx=Math.cos(a),cy=Math.sin(a);
    const bend=R(-0.15,0.15)*l;
    E('path',{d:`M${(x-cx*l/2).toFixed(1)} ${(y-cy*l/2).toFixed(1)}Q${(x-cy*bend).toFixed(1)} ${(y+cx*bend).toFixed(1)} ${(x+cx*l/2).toFixed(1)} ${(y+cy*l/2).toFixed(1)}`,'stroke-width':(w*R(0.7,1.3)).toFixed(2)},g);}
  return g;
}
const rect=(x,y,w,h)=>[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
const ellipsePts=(cx,cy,rx,ry,n=24,a0=0,a1=Math.PI*2)=>{const o=[];const full=(a1-a0)>6.28;for(let i=0;i<n;i++){const a=a0+(a1-a0)*i/(full?n:(n-1));o.push([cx+rx*Math.cos(a),cy+ry*Math.sin(a)]);}return o;};

/* =====================================================================
   FIGURER. Hodet er 100 enheter høyt (0 = isse, 100 = hake), x=0 midt.
   Sittende figur i profil, vender mot +x. Skjelett:
     hofte (origo i figuren, på stolsetet)
       > body: dreier `lean` grader om hoften (fram = positivt)
         > torso: skulderleddet i origo, 200 over hoften, 10 foran
           > hode: isse i (29,-154), dreier `headTilt` om halsroten
           > arm: skulder > underarm (albue) > hånd (håndledd)
     bein: lår og legg, faste på stolen (dreier ikke med ryggen)
   Nær arm og fjern underarm tegnes i en egen frontgruppe med samme
   transformkjede, så de kan ligge over bordet mens kroppen ligger under.
   ===================================================================== */
const JON={name:'jon',beard:true,cap:false,hair:'short',brow:1.25,nose:0.95,bump:0,chin:0.35,cheek:0,shirt:'fleece',bulk:1.1};
const GEIR={name:'geir',beard:false,stubble:true,cap:true,hair:'none',brow:0.95,nose:1.12,bump:1,chin:-0.3,cheek:1,shirt:'flannel',bulk:0.94};

/* ---------- munnformer. Navnene er Rhubarb / Preston Blair. ----------
   jaw     kjevesenk 0..1
   round   leppene rundes og skyves fram 0..1
   stretch munnvikene dras bakover (positivt) eller fram (negativt)
   press   leppene presses sammen (A)
   teeth   overtennene ligger på underleppen (G)                        */
const MOUTHS={
  X:{jaw:0,   round:0,  stretch:0,   press:0,  teeth:0},   // hvile
  A:{jaw:0,   round:0,  stretch:0,   press:1,  teeth:0},   // M B P
  B:{jaw:0.16,round:0,  stretch:0.25,press:0,  teeth:0},   // de fleste konsonanter, tennene nesten sammen
  C:{jaw:0.5, round:0,  stretch:0.25,press:0,  teeth:0},   // E
  D:{jaw:0.95,round:0,  stretch:0.7, press:0,  teeth:0},   // A
  E:{jaw:0.45,round:0.7,stretch:-0.2,press:0,  teeth:0},   // O
  F:{jaw:0.22,round:1,  stretch:-0.8,press:0,  teeth:0},   // U W, snurpet og fram
  G:{jaw:0.12,round:0,  stretch:0.1, press:0,  teeth:1},   // F V
};
function mouthOf(pose){const m=Object.assign({},MOUTHS.X,MOUTHS[pose.mouth]||{});for(const k in MOUTHS.X)if(pose[k]!=null)m[k]=pose[k];return m;}
const rotP=(p,deg,c)=>{const a=deg*Math.PI/180,cs=Math.cos(a),sn=Math.sin(a),dx=p[0]-c[0],dy=p[1]-c[1];return[c[0]+dx*cs-dy*sn,c[1]+dx*sn+dy*cs];};

/* ----- hode i profil (vender mot +x) ----- */
function headProfile(fig,ch,pose){
  const m=mouthOf(pose), jd=m.jaw*15, det=pose.detail==null?1:pose.detail, fine=det>0.5;
  const HJ=[-29,68];
  const head=G(fig,{class:'head',transform:`rotate(${pose.headTilt||0} -17 130)`});
  const jaw=G(head,{class:'jaw',transform:`rotate(${jd.toFixed(2)} ${HJ[0]} ${HJ[1]})`});
  const nt=(ch.nose-1)*8, bp=ch.bump||0, ct=(ch.chin||0)*6, ck=ch.cheek||0;
  const rr=m.round, st=m.stretch, pr=m.press, th=m.teeth;
  // leppefront og munnvik. Runding skyver fronten fram og viken fram. Strekk drar viken bakover.
  const fx=37+6*rr, cx=22-7*st+5*rr;
  const lipY=77+pr*0.5;
  const skull=[[-8,0],[14,2],[26,9],[33,20],[36,30],[37,36],[33,42],[36+bp*1.5,47],[41+bp*2,52],[45+nt,59],[46+nt,63],[42,66],[37,67],[37,71],[fx+2,74],[fx-0.5,lipY],
    [fx+1,81],[fx-1,85],[34+ct,91],[28+ct,96],[18,101],[6,103],[-8,100],[-19,93],[-26,84],[-28,72],[-40,72],[-50,60],[-54,42],[-52,24],[-44,9],[-28,1]];
  white(skull,{curve:true},head);
  // panne, neserygg, tupp
  ink([[-8,0],[14,2],[26,9],[33,20],[36,30],[37,36]],{curve:true,w:2.2,amp:0.3,taper:0.5},head);
  ink([[37,36],[33,42],[36+bp*1.5,47],[41+bp*2,52],[45+nt,59],[46+nt,63],[42,66],[37.5,67]],{curve:true,w:2.8,amp:0.25,taper:0.5},head);
  stroke([[37.5,67],[35,67.5],[33,65.5],[34.5,63]],{curve:true,w:1.0,amp:0.15},head);
  // overleppe (fast på hodet): renne ned fra nesen, leppefront, munnlinje bak til viken
  ink([[37,68],[37,71],[fx+2,74],[fx-0.5,lipY]],{curve:true,w:2.0,amp:0.2,taper:0.5},head);
  ink([[fx-0.5,lipY],[30,lipY+0.6+pr*0.3],[cx,lipY-0.5-st*2+pr*0.8]],{curve:true,w:1.6+pr*0.4,amp:0.2,taper:0.8},head);
  const __sv=seed;
  if(rr>0.3)stroke([[fx-3,71.5],[fx+2.5,74.5],[fx-1,lipY]],{curve:true,w:0.9,amp:0.2},head);
  // munnhulen: mellom overleppen (fast) og underleppen (dreid med kjeven)
  if(m.jaw>0.05&&!th){
    const up=[[cx,lipY],[30,lipY+0.8],[fx-0.5,lipY+0.6]];
    const lo=[[fx-0.5,78.6],[30,79.2],[cx+1,78]].map(p=>rotP(p,jd,HJ));
    black(up.concat(lo),{curve:true},head);
    // tenner: en hvit linje rett under overleppen. Ved B er den nesten hele hulen.
    if(m.jaw>0.1&&rr<0.5)stroke([[cx+4,lipY+2.2],[fx-3,lipY+2.0]],{w:m.jaw<0.25?1.0:1.4,amp:0.1,col:'#fff'},head);
  }
  if(th){
    // G: overtennene ligger på underleppen. Leppen er trukket inn, tennene synlige som en hvit kile med strek under.
    black([[cx+2,lipY],[fx-0.5,lipY+0.4],[fx-3,lipY+3.2],[cx+3,lipY+2.2]],{curve:false},head);
    white([[cx+6,lipY+0.6],[fx-1,lipY+0.8],[fx-1.5,lipY+2.6],[cx+7,lipY+2.0]],{curve:false},head);
  }
  seed=__sv;
  // bakhode og øre
  ink([[-28,1],[-44,9],[-52,24],[-54,42],[-50,60],[-42,71]],{curve:true,w:2.0,amp:0.4,taper:0.6},head);
  ink([[-27,48],[-33,45],[-37,52],[-35,62],[-31,69],[-27,68]],{curve:true,w:1.7,amp:0.3},head);
  if(fine)stroke([[-30,51],[-33,57],[-31,64]],{curve:true,w:0.9,amp:0.2},head);
  // øye i profil: øvre lokk tykt, iris som kile
  const eo=clamp(pose.eyeOpen==null?1:pose.eyeOpen);
  ink([[17,45],[24,42.5],[31,44],[34,46.5]],{curve:true,w:2.2,amp:0.2},head);
  if(eo>0.3){black([[26,44.5],[32,45],[31.5,48.5],[26.5,48]],{curve:true},head);E('circle',{cx:29.5,cy:45.6,r:0.8,fill:'#fff'},head);}
  stroke([[22,49],[28,50],[33,48.5]],{curve:true,w:0.8,amp:0.2},head);
  if(fine)stroke([[18,52.5],[25,54.5],[31,53.5]],{curve:true,w:0.6,amp:0.2},head);
  // bryn
  const r=(pose.brow||0)*3;
  ink([[18,37-r],[26,34.5-r*1.3],[33,35.5-r],[37.5,38-r*0.6]],{curve:true,w:2.6*ch.brow,amp:0.3,taper:1.5},head);
  if(fine)for(let i=0;i<8;i++){const t=i/7;const x=19+t*17,y=36.5-r-Math.sin(t*3.1)*2.4;stroke([[x,y+0.5],[x+2.2,y-1.5]],{w:0.9,amp:0.1},head);}
  // skygger: øyehulen alltid, resten bare i nærbilde
  hatch(shape([[17,39],[37,40],[34,45],[18,47]],{curve:true}),{ang:10,gap:2.4,w:0.7,dens:()=>0.5},head);
  if(fine){
    hatch(shape([[26,65],[37,67],[37,72],[26,71]],{curve:true}),{ang:20,gap:2.4,w:0.7,dens:(x,y)=>clamp(0.2+(x-26)/12)},head);
    hatch(shape([[-30,42],[8,40],[20,56],[24,74],[-2,78],[-30,72]],{curve:true}),{ang:70,gap:4.0,w:0.7,amp:0.5,dens:(x,y)=>clamp(0.05+(-x)/60)*clamp((y-40)/20)},head);
  }
  // innsunket kinn (Geir): ett skyggefelt under kinnbeinet
  if(ck>0)hatch(shape([[-2,54],[16,58],[24,70],[12,74],[-8,70],[-12,60]],{curve:true}),{ang:75,gap:fine?3:2.4,w:0.7,dens:(x,y)=>clamp(0.1+(y-56)/22)*(fine?0.55:0.85)*ck},head);
  // --- underkjeve (egen gruppe): hvit flate, underleppe, hake, kjevelinje
  const lipLo=[[fx-0.5-th*3,78.6-pr*0.8],[fx+2+rr*2+pr*1.5-th*3.5,81-pr*0.8],[fx-1.5-th*2,85-pr*0.5]];
  white([[fx-0.5,78.6],[fx+1.5+rr*2,81],[fx-1.5,85],[34+ct,91],[28+ct,96],[18,101],[6,103],[-8,100],[-19,93],[-26,84],[-28,72],[-29,68],[-10,74],[cx+1,78]],{curve:true},jaw);
  ink(lipLo,{curve:true,w:1.8+rr*0.4,amp:0.2,taper:0.5},jaw);
  ink([[fx-1.5-th*2,85],[fx-1+ct*0.5,88],[34+ct,91],[28+ct,96],[18,101],[6,103],[-8,100],[-19,93],[-26,84],[-28,72]],{curve:true,w:fine?2.6:3.0,amp:0.3,taper:0.6},jaw);
  hatch(shape([[-26,78],[0,86],[18,95],[8,102],[-8,99],[-24,90]],{curve:true}),{ang:20,gap:3.0,w:0.8,dens:(x,y)=>clamp(0.25+(y-80)/25)},jaw);
  if(ch.beard){
    const jb=shape([[38,78],[40,84],[36,91],[30,97],[20,103],[6,105],[-10,101],[-24,92],[-30,80],[-30,68],[-16,70],[-4,80],[14,86],[26,84],[32,78]],{curve:true});
    strokesIn(jb,{n:Math.round(800*(0.6+0.4*det)),len:5,w:1.0,angf:(x,y)=>60+(x+20)*0.9,dens:(x,y)=>clamp(0.45+(y-70)/40)},jaw);
    const cb=shape([[-30,50],[-22,52],[-8,66],[10,76],[26,78],[30,80],[16,80],[-2,80],[-18,74],[-30,66]],{curve:true});
    strokesIn(cb,{n:320,len:4.5,w:0.9,angf:(x,y)=>65+(x+20)*0.8,dens:(x,y)=>clamp(0.25+(y-52)/30)},head);
    strokesIn(shape([[26,67],[37,67.5],[39,74],[35,76],[24,75]],{curve:true}),{n:130,len:4,w:0.9,ang:100},head);
  } else if(ch.stubble){
    stipple(shape([[36,79],[38,86],[30,96],[16,102],[-6,100],[-22,92],[-27,76],[-18,74],[0,84],[16,90],[28,86]],{curve:true}),{n:fine?500:420,r:fine?0.55:0.8,dens:(x,y)=>clamp((fine?0.15:0.35)+(y-74)/30)},jaw);
    stipple(shape([[24,68],[37,68],[39,74],[35,76],[22,75]],{curve:true}),{n:60,r:0.45,dens:()=>0.5},head);
  }
  if(ch.cap){
    const crown=[[36,28],[31,14],[16,3],[-6,-3],[-30,-1],[-48,10],[-56,26],[-55,34]];
    white(crown.concat([[36,35]]),{curve:true},head);
    ink(crown,{curve:true,w:2.6,amp:0.4,taper:0.5},head);
    ink([[-55,34],[-30,32],[-8,30.5],[14,30],[36,30]],{curve:true,w:2.0,amp:0.3,taper:0.6},head);
    stroke([[-6,-2],[-2,10],[2,22],[4,30]],{curve:true,w:0.8,amp:0.2},head);
    stroke([[-6,-2],[-20,8],[-32,20],[-38,31]],{curve:true,w:0.8,amp:0.2},head);
    hatch(shape(crown.concat([[36,35]]),{curve:true}),{ang:60,gap:3.2,w:0.8,dens:(x,y)=>clamp(0.15+(-x-10)/60)+0.2},head);
    const brim=[[34,30],[50,30],[68,33],[74,37],[66,40],[48,39],[33,36]];
    white(brim,{curve:true},head);
    ink(brim,{curve:true,w:2.2,amp:0.3,closed:true,taper:0},head);
    hatch(shape([[34,35],[48,37],[66,38],[72,37.5],[66,40.5],[48,39.5],[33,37]],{curve:true}),{ang:0,gap:1.8,w:0.8},head);
    if(fine)hatch(shape([[36,36],[38,37],[36,43],[26,45],[18,43],[10,39],[10,33],[34,33]],{curve:true}),{ang:15,gap:2.8,w:0.8,dens:(x,y)=>clamp(0.5+(37-y)/12)},head);
    else hatch(shape([[36,33],[38,37],[37,45],[28,52],[14,52],[2,47],[0,36],[30,32]],{curve:true}),{ang:12,gap:2.0,w:0.9,dens:(x,y)=>clamp(1.0+(38-y)/12)},head);
    strokesIn(shape([[-56,35],[-34,34],[-26,42],[-32,52],[-50,50]],{curve:true}),{n:70,len:6,w:0.9,ang:70},head);
  } else if(ch.hair==='short'){
    const hp=[[-8,-4],[14,-1],[27,7],[32,14],[30,16],[18,17],[4,21],[-10,29],[-18,40],[-24,48],[-30,52],[-36,48],[-46,50],[-53,44],[-56,26],[-48,8],[-30,-2]];
    white(hp,{curve:true},head);
    strokesIn(shape(hp,{curve:true}),{n:Math.round(1800*(0.5+0.5*det)),len:6,w:1.0,angf:(x,y)=>100+(x+10)*1.4,dens:(x,y)=>clamp(0.5+(-x)/60)},head);
    ink([[-8,-4],[14,-1],[27,7],[32,14]],{curve:true,w:1.4,amp:0.6,taper:1},head);
    ink([[-30,-2],[-48,8],[-56,26],[-53,44]],{curve:true,w:1.4,amp:0.6,taper:1},head);
  }
  return {head,jaw};
}

/* ----- armkjede. Lokalt: leddet i origo, armen langs +y. sh, el, hand i grader,
   0 = rett ned, negativt = framover. parts: 'all' | 'upper' | 'lower'. ----- */
function armChain(parent,o){
  const L1=o.L1||125,L2=o.L2||104,parts=o.parts||'all';
  const up=G(parent,{class:'arm',transform:`translate(${o.shoulder[0]} ${o.shoulder[1]}) rotate(${o.sh||0})`});
  const w0=o.wUp||21,w1=o.wFo||16;
  if(parts!=='lower'){
    const ol=[[-w0*0.5,-16],[w0*0.5,-17],[w0*1.05,-2],[w0,40],[w1*1.1,L1-16],[w1,L1+6],[0,L1+12],[-w1,L1+6],[-w1*1.1,L1-16],[-w0,40],[-w0*1.05,-2]];
    white(ol,{curve:true},up);
    ink([[-w0*0.5,-16],[w0*0.5,-17],[w0*1.05,-2],[w0,40],[w1*1.1,L1-16],[w1,L1+6]],{curve:true,w:2.2,amp:0.5,taper:0.4},up);
    ink([[-w0*1.05,-2],[-w0,40],[-w1*1.1,L1-16],[-w1,L1+6],[0,L1+12]],{curve:true,w:2.4,amp:0.5,taper:0.4},up);
    stroke([[-w0*0.7,16],[-w0*0.2,10],[w0*0.5,14]],{curve:true,w:0.9,amp:0.3},up);
    hatch(shape(ol,{curve:true}),{ang:80,gap:4.4,w:0.8,dens:(x,y)=>clamp((-x-w0*0.35)/(w0*0.7))*0.75},up);
    stroke([[-w1*0.6,L1-14],[0,L1-8],[w1*0.6,L1-12]],{curve:true,w:0.9,amp:0.3},up);
  }
  const fo=G(up,{class:'forearm',transform:`translate(0 ${L1}) rotate(${o.el||0})`});
  let hand=null;
  if(parts!=='upper'){
    const w2=w1*0.72;
    const ol=[[-w1,-6],[w1,-6],[w1*0.95,L2*0.4],[w2,L2-2],[-w2,L2-2],[-w1*0.95,L2*0.4]];
    white(ol,{curve:true},fo);
    ink([[-w1,-4],[-w1*0.98,L2*0.4],[-w2,L2-2]],{curve:true,w:2.2,amp:0.5,taper:0.4},fo);
    ink([[w1,-4],[w1*0.98,L2*0.4],[w2,L2-2]],{curve:true,w:1.9,amp:0.5,taper:0.4},fo);
    hatch(shape(ol,{curve:true}),{ang:80,gap:4.2,w:0.8,dens:(x,y)=>clamp((-x-w1*0.3)/(w1*0.75))*0.75},fo);
    ink([[-w2*1.05,L2-10],[w2*1.05,L2-11]],{w:1.4,amp:0.3,taper:0.6},fo);
    stroke([[-w2,L2-3],[w2,L2-4]],{w:0.8,amp:0.3},fo);
    hand=G(fo,{class:'hand',transform:`translate(0 ${L2}) rotate(${o.hand||0})`});
    handShape(G(hand,{transform:`rotate(90) scale(1 ${o.mirrorHand?-1:1})`}),o.grip||'rest',o);
  }
  return {up,fo,hand};
}
/* hånd sett fra siden. Lokalt: håndleddet i origo, x = fingrene fram, y = ned når underarmen ligger vannrett. */
function handShape(g,grip,o){
  if(grip==='typing'){
    const palm=[[0,-10],[14,-13],[26,-9],[28,3],[24,10],[8,11],[0,8]];
    white(palm,{curve:true},g);
    for(const [y,L,w] of [[-8,23,5],[-2,29,5],[4,26,4.8],[9,19,4.3]]){
      const f=[[21,y-w/2],[32,y-w/2-1],[21+L-4,y],[21+L,y+2],[21+L-1,y+5],[21+L-6,y+5],[30,y+w/2],[21,y+w/2]];
      white(f,{curve:true},g);ink(f.slice(0,7),{curve:true,w:1.2,amp:0.12,taper:0.5},g);
      stroke([[33,y-1],[35,y+2]],{w:0.5,amp:0.1},g);
    }
    white([[0,-10],[14,-13],[24,-9],[24,10],[8,11],[0,8]],{curve:true},g);
    ink([[0,-10],[14,-13],[24,-9]],{curve:true,w:1.6,amp:0.2},g);
    ink([[24,10],[8,11],[0,8]],{curve:true,w:1.4,amp:0.2},g);
    const thumb=[[6,-10],[12,-20],[22,-23],[29,-19],[28,-15],[20,-13],[15,-5]];
    white(thumb,{curve:true},g);ink(thumb.slice(0,6),{curve:true,w:1.4,amp:0.12},g);
    stroke([[21,-21],[25,-19],[25,-16]],{curve:true,w:0.6,amp:0.1},g);
  } else if(grip==='glass'){
    const gh=o.glassH||74;
    beerGlass(g,27,10,gh);
    const back=[[0,-12],[12,-16],[22,-15],[16,12],[0,10]];
    white(back,{curve:true},g);
    ink([[0,-12],[12,-16],[22,-15]],{curve:true,w:1.8,amp:0.3,taper:0.5},g);
    ink([[0,10],[16,12]],{curve:true,w:1.6,amp:0.3,taper:0.5},g);
    for(let i=0;i<4;i++){const y=-9+i*6.6;const f=[[12,y-3.4],[30,y-3.8],[41,y-1],[42,y+1.5],[30,y+3.2],[12,y+3.2]];white(f,{curve:true},g);ink([[12,y-3.4],[30,y-3.8],[41,y-1],[42,y+1.5],[30,y+3.2],[14,y+3.2]],{curve:true,w:1.4,amp:0.25,taper:0.3},g);}
    const th=[[6,-16],[16,-22],[28,-21],[34,-17],[30,-13],[18,-13]];
    white(th,{curve:true},g);ink([[6,-16],[16,-22],[28,-21],[34,-17],[31,-13]],{curve:true,w:1.6,amp:0.3,taper:0.5},g);
    hatch(shape([[0,-12],[12,-16],[16,12],[0,10]],{curve:true}),{ang:70,gap:3,w:0.7,dens:(x,y)=>clamp(0.15+y/24)},g);
  } else if(grip==='fork'){
    const p=[[0,-11],[14,-14],[28,-10],[32,0],[26,9],[8,10],[0,9]];
    white(p,{curve:true},g);ink(p,{curve:true,closed:true,taper:0,w:1.8,amp:0.3},g);
    for(let i=0;i<3;i++)stroke([[14+i*5,-8+i*4],[26+i*3,-2+i*4]],{curve:true,w:0.8,amp:0.2},g);
    ink([[18,-4],[40,2],[64,10]],{curve:true,w:1.5,amp:0.15,taper:0.3},g);
    for(let i=0;i<3;i++)stroke([[63,10-i*1.6],[72,13-i*2]],{w:0.8,amp:0.1},g);
    hatch(shape([[0,0],[28,2],[26,9],[0,9]]),{ang:0,gap:2.6,w:0.7,dens:()=>0.45},g);
  } else if(grip==='fist'){
    const p=[[0,-11],[12,-14],[26,-11],[30,0],[24,9],[6,10],[0,9]];
    white(p,{curve:true},g);ink(p,{curve:true,closed:true,taper:0,w:1.8,amp:0.3},g);
    for(let i=0;i<3;i++)stroke([[12+i*5,-9+i*4],[24+i*2,-4+i*4]],{curve:true,w:0.8,amp:0.2},g);
    hatch(shape([[0,0],[26,2],[24,9],[0,9]]),{ang:0,gap:2.6,w:0.7,dens:()=>0.45},g);
  } else {
    const p=[[0,-10],[14,-12],[30,-9],[44,-4],[48,2],[44,7],[30,9],[10,9],[0,8]];
    white(p,{curve:true},g);ink(p,{curve:true,closed:true,taper:0,w:1.8,amp:0.3},g);
    stroke([[20,-4],[46,1]],{curve:true,w:0.8,amp:0.2},g);stroke([[22,3],[44,5]],{curve:true,w:0.7,amp:0.2},g);
    stroke([[10,-10],[18,-14],[28,-13]],{curve:true,w:1.0,amp:0.2},g);
    hatch(shape([[0,0],[46,3],[44,8],[0,8]]),{ang:0,gap:2.6,w:0.7,dens:()=>0.5},g);
  }
}

/* ----- stol i profil. Hoften i origo, setet under hoften. ----- */
function chairProfile(fig){
  const g=G(fig,{class:'stol'});
  const bx=-60;
  // ryggstø sett fra siden: en stolpe, toppstykket som en liten kloss, en tverrspile
  white([[bx-9,-196],[bx+9,-196],[bx+5,-2],[bx-13,-2]],{},g);
  ink([[bx-7,-190],[bx-13,-2]],{w:3.2,amp:0.5,taper:0.2},g);
  ink([[bx+7,-190],[bx+3,-2]],{w:2.2,amp:0.5,taper:0.2},g);
  const top=[[bx-14,-206],[bx+14,-206],[bx+12,-188],[bx-12,-188]];
  white(top,{curve:true},g);ink(top,{curve:true,closed:true,taper:0,w:2.2,amp:0.3},g);
  hatch(shape(top,{curve:true}),{ang:0,gap:2.4,w:0.7,dens:()=>0.5},g);
  ink([[bx-10,-124],[bx+6,-124]],{w:2.4,amp:0.3},g);
  hatch(shape([[bx-8,-188],[bx+6,-188],[bx+3,-4],[bx-13,-4]]),{ang:85,gap:3,w:0.7,dens:()=>0.4},g);
  const seat=[[bx-6,-4],[64,-4],[68,8],[bx-12,8]];
  white(seat,{},g);ink(seat,{closed:true,taper:0,w:2.2,amp:0.4},g);
  hatch(shape(seat),{ang:0,gap:2.6,w:0.7,dens:()=>0.5},g);
  ink([[bx-8,8],[bx-12,200]],{w:3.4,amp:0.5,taper:0.2},g);
  ink([[58,8],[62,200]],{w:3.4,amp:0.5,taper:0.2},g);
  ink([[bx-10,124],[60,122]],{w:2,amp:0.4,taper:0.3},g);
  return g;
}
/* ----- bein, sittende. Hoften i origo, gulvet 200 under. ----- */
function legsSeated(fig,ch){
  const g=G(fig,{class:'legs'});
  function leg(dx,dy,near){
    const lg=G(g,{transform:`translate(${dx} ${dy})`});
    const thigh=[[-24,-14],[60,-20],[150,-18],[186,-6],[192,10],[180,26],[60,28],[-24,24]];
    white(thigh,{curve:true},lg);
    ink([[-24,-14],[60,-20],[150,-18],[186,-6],[192,10]],{curve:true,w:near?2.2:1.6,amp:0.5,taper:0.4},lg);
    ink([[-10,26],[60,28],[150,26]],{curve:true,w:near?1.8:1.2,amp:0.5,taper:0.6},lg);
    const shin=[[150,20],[192,10],[188,110],[184,196],[150,196],[152,110]];
    white(shin,{curve:true},lg);
    ink([[192,10],[188,110],[184,196]],{curve:true,w:near?2.2:1.6,amp:0.5,taper:0.4},lg);
    ink([[152,30],[152,110],[150,196]],{curve:true,w:near?2.0:1.4,amp:0.5,taper:0.4},lg);
    const shoe=[[146,184],[190,182],[214,192],[214,202],[146,204]];
    white(shoe,{curve:true},lg);ink(shoe,{curve:true,closed:true,taper:0,w:2.0,amp:0.4},lg);
    hatch(shape(shoe,{curve:true}),{ang:0,gap:3,w:0.8,dens:(x,y)=>clamp(0.3+(y-190)/14)},lg);
    stroke([[168,-8],[180,6],[176,22]],{curve:true,w:0.9,amp:0.4},lg);
    hatch(shape(thigh,{curve:true}),{ang:10,gap:4.5,w:0.8,dens:(x,y)=>clamp(0.05+(y-4)/24)*0.8},lg);
    hatch(shape(shin,{curve:true}),{ang:85,gap:4.5,w:0.8,dens:(x,y)=>clamp(0.1+(170-x)/30)*0.7},lg);
  }
  leg(0,0,true);
  return g;
}
/* ----- overkropp med hals. Skulderleddet i origo. ----- */
function torsoSeated(T,ch){
  const g=G(T,{class:'kropp'});
  const bk=ch.bulk||1;
  // hals: fra kjeven ned bak kragen. Skyggen ligger under haken.
  if(ch.sex==='f'){
    white([[-14,-58],[34,-58],[36,-6],[-20,-6]],{},g);
    ink([[31,-42],[34,-26],[36,-10]],{curve:true,w:1.6,amp:0.3},g);
    ink([[-13,-42],[-16,-28],[-20,-12]],{curve:true,w:1.8,amp:0.3},g);
    hatch(shape([[-13,-48],[31,-46],[36,-6],[-20,-6]]),{ang:75,gap:3.6,w:0.9,dens:(x,y)=>clamp(0.7-(y+46)/48)},g);
  } else {
  white([[-20,-58],[44,-58],[46,-6],[-28,-6]],{},g);
  ink([[40,-42],[43,-26],[46,-10]],{curve:true,w:1.8,amp:0.3},g);
  ink([[-19,-42],[-23,-28],[-28,-12]],{curve:true,w:2.0,amp:0.3},g);
  hatch(shape([[-19,-48],[40,-46],[46,-6],[-28,-6]]),{ang:75,gap:3.6,w:0.9,dens:(x,y)=>clamp(0.7-(y+46)/48)},g);
  }
  // kroppen: rund rygg, mage mot bordet
  const rk=ch.rygg==null?bk:ch.rygg;
  const fem=ch.sex==='f';
  // 7.10.2026: kvinnekropp i profil. Smalere rygg, bryst foran, midje inn, hofte ut. Mennene som før.
  const back=fem?[[-16,-16],[-28,-4],[-36,16],[-42*rk,60],[-44*rk,110],[-40*rk,150],[-44*rk,206]]
                :[[-22,-16],[-38,-4],[-48,16],[-53*rk,60],[-56*rk,120],[-52*rk,170],[-44,206]];
  const fk=ch.mage==null?bk:ch.mage;   // mage: framkanten for seg, så ryggen kan være bred uten stor mage (Andreas 5.10)
  const front=fem?[[34,-14],[38,2],[44*fk,30],[52*fk,62],[46*fk,100],[40*fk,140],[48*fk,206]]
                 :[[44,-14],[50,2],[55*fk,30],[60*fk,80],[63*fk,125],[60*fk,165],[54,206]];
  const body=back.concat(front.slice().reverse());
  const bodyD=shape(body,{curve:true});
  white(body,{curve:true},g);
  const sh=ch.shirt;
  const egne=['knit','cardigan','blazer','hoodie','polo','vest','wind','work','overall','hivis'];
  if(ch.sex&&egne.includes(sh)){   // bare rollene i KAR (de har sex). De gamle Kvilldal- og Suldal-figurene går som før.
    torsoProfilKlaer(g,ch,body,bodyD,fem);
  } else if(ch.shirt==='fleece'){
    // høy krage rundt halsen, glidelås ned framkanten, ermsøm over skulderen
    const col=[[-28,-32],[-6,-34],[20,-34],[44,-31],[48,-12],[24,-9],[-4,-8],[-30,-12]];
    white(col,{curve:true},g);
    ink([[-28,-32],[-6,-34],[20,-34],[44,-31],[48,-12]],{curve:true,w:2.0,amp:0.4,taper:0.6},g);
    ink([[48,-12],[24,-9],[-4,-8],[-30,-12],[-28,-32]],{curve:true,w:1.6,amp:0.4,taper:0.6},g);
    hatch(shape(col,{curve:true}),{ang:0,gap:3,w:0.7,dens:(x,y)=>clamp(0.05+(y+12)/-16)*0.6},g);
    stroke([[46,-10],[52,30],[58,80],[61,125],[58,165]],{curve:true,w:1.0,amp:0.4},g);
    for(let y=-6;y<165;y+=6){const t=(y+6)/170;const x=46+16*Math.sin(t*3.14);stroke([[x-2,y],[x+2,y+0.5]],{w:0.7,amp:0.05},g);}
    // folder: under armhulen og over magen
    stroke([[-6,40],[10,60],[20,84]],{curve:true,w:0.8,amp:0.5},g);
    stroke([[14,150],[34,158],[52,166]],{curve:true,w:0.9,amp:0.5},g);
    stroke([[-30,150],[-10,160]],{curve:true,w:0.8,amp:0.5},g);
    hatch(bodyD,{ang:75,gap:5,w:0.9,dens:(x,y)=>clamp((-x-26)/34)*0.6},g);
    hatch(bodyD,{ang:100,gap:5.5,w:0.7,dens:(x,y)=>clamp(0.02+(y-150)/70)*0.5},g);
  } else {
    // skjortekrage: bakstykke og en snipp som peker ned og fram. Knapper ned framkanten.
    ink([[-28,-30],[-8,-33],[22,-31],[44,-26]],{curve:true,w:1.9,amp:0.3,taper:0.6},g);
    ink([[44,-26],[54,-8],[42,-2],[30,-12]],{curve:true,w:1.7,amp:0.3,taper:0.4},g);
    ink([[-28,-30],[-30,-14]],{curve:true,w:1.6,amp:0.3,taper:0.5},g);
    stroke([[-30,-14],[-6,-10],[22,-10],[42,-2]],{curve:true,w:1.0,amp:0.4},g);
    for(const [x,y] of [[52,10],[57,50],[61,90],[62,130],[59,168]])E('circle',{cx:x,cy:y,r:1.6*U,fill:'#000'},g);
    stroke([[50,2],[56,48],[60,90],[61,130],[58,170]],{curve:true,w:0.9,amp:0.4},g);
    hatch(bodyD,{ang:93,gap:13,w:0.9,amp:0.3},g);
    hatch(bodyD,{ang:6,gap:13,w:0.9,amp:0.3},g);
    hatch(bodyD,{ang:75,gap:4.6,w:0.9,dens:(x,y)=>clamp((-x-26)/34)*0.6},g);
    hatch(bodyD,{ang:100,gap:5.5,w:0.7,dens:(x,y)=>clamp(0.02+(y-150)/70)*0.5},g);
    stroke([[-4,44],[12,64],[22,86]],{curve:true,w:0.8,amp:0.5},g);
  }
  ink(back,{curve:true,w:2.5,amp:0.5,taper:0.5},g);
  ink(front,{curve:true,w:2.2,amp:0.5,taper:0.5},g);
  return g;
}
// 7.10.2026: rollens egne klær i profil (standProfile og seatedProfile). Samme strek som forfra i karakterer.js.
// Kroppen (body) er tegnet hvit før, konturen tegnes etter. fx er framkanten, bx bakkanten, ved høyden y.
function torsoProfilKlaer(g,ch,body,bodyD,fem){
  const sh=ch.shirt, n=body.length/2;
  const back=body.slice(0,n), front=body.slice(n).reverse();
  const xAt=(arr,y)=>{for(let i=1;i<arr.length;i++){if(arr[i][1]>=y){const t=(y-arr[i-1][1])/(arr[i][1]-arr[i-1][1]);return arr[i-1][0]+t*(arr[i][0]-arr[i-1][0]);}}return arr[arr.length-1][0];};
  const fx=y=>xAt(front,y), bx=y=>xAt(back,y);
  const bk=fem?-14:-20, fr=fem?34:44;   // halsen
  const rundHals=()=>{const rb=[[bk-8,-32],[fr+4,-30],[fr+6,-20],[bk-10,-22]];white(rb,{curve:true},g);
    for(let x=bk-6;x<fr+4;x+=3.6)stroke([[x,-31],[x+0.3,-21]],{w:0.55,amp:0.1},g);ink(rb,{curve:true,closed:true,taper:0,w:1.3,amp:0.2},g);};
  const ribbNed=()=>{ink([[bx(192),192],[fx(192),192]],{w:1.1,amp:0.3,taper:0.5},g);for(let x=bx(194)+2;x<fx(194)-2;x+=4)stroke([[x,193],[x+0.4,205]],{w:0.55,amp:0.1},g);};
  const skjorteKrage=()=>{ink([[bk-8,-30],[8,-33],[fr-10,-31],[fr,-26]],{curve:true,w:1.9,amp:0.3,taper:0.6},g);
    ink([[fr,-26],[fr+10,-8],[fr-2,-2],[fr-14,-12]],{curve:true,w:1.7,amp:0.3,taper:0.4},g);ink([[bk-8,-30],[bk-10,-14]],{curve:true,w:1.6,amp:0.3,taper:0.5},g);
    stroke([[bk-10,-14],[0,-10],[fr-6,-8],[fr-2,-2]],{curve:true,w:1.0,amp:0.4},g);};
  const knapper=(ys)=>{for(const y of ys)E('circle',{cx:fx(y)-5,cy:y,r:1.6*U,fill:'#000'},g);};
  const framkant=(y0,y1,dx)=>stroke([[fx(y0)+dx,y0],[fx((y0+y1)/2)+dx,(y0+y1)/2],[fx(y1)+dx,y1]],{curve:true,w:0.9,amp:0.4},g);
  const skygge=()=>{hatch(bodyD,{ang:75,gap:4.6,w:0.9,dens:(x,y)=>clamp((-x-(fem?18:26))/34)*0.6},g);
    hatch(bodyD,{ang:100,gap:5.5,w:0.7,dens:(x,y)=>clamp(0.02+(y-150)/70)*0.5},g);};
  if(sh==='knit'){
    // Martes strikkegenser: ribb i halsen, v-mønster i rader, ribb nederst
    hatch(bodyD,{ang:0,gap:4.2,w:0.55,amp:0.4,dens:()=>0.36},g);
    const cg=clipG(bodyD,g);
    for(let y=10,r=0;y<185;y+=13,r++)for(let x=bx(y)+6+(r%2)*7;x<fx(y)-4;x+=14){if(rnd()<0.12)continue;stroke([[x-2.6,y-2.4],[x,y+1.6],[x+2.6,y-2.4]],{w:0.6,amp:0.1},cg);}
    rundHals();ribbNed();
  } else if(sh==='cardigan'){
    // konas cardigan: genseren under lys ved halsen, kanten ned framsiden med knapper, strikk som vannrette strøk
    hatch(bodyD,{ang:0,gap:4.2,w:0.55,amp:0.4,dens:()=>0.42},g);
    const V=[[fr-16,-30],[fr+4,-30],[fx(60)-2,60],[fx(60)-14,60]];white(V,{},g);
    ink([[fr-14,-30],[fx(60)-12,60],[fx(200)-12,200]],{curve:true,w:1.6,amp:0.3,taper:0.4},g);
    for(const y of [80,120,160])E('circle',{cx:fx(y)-7,cy:y,r:2.2,fill:'#fff',stroke:'#000','stroke-width':0.9*U},g);
    stroke([[fx(100)-30,100],[fx(100)-8,100],[fx(136)-8,136],[fx(136)-30,136]],{curve:true,closed:true,w:0.8,amp:0.3},g);
    ribbNed();
  } else if(sh==='blazer'){
    // Adas blazer: tett skravur, jakkeslag, hvit skjortekrage, adgangskort i snor
    hatch(bodyD,{ang:75,gap:3.0,w:0.7,amp:0.3,dens:()=>0.8},g);
    hatch(bodyD,{ang:15,gap:4.4,w:0.5,amp:0.3,dens:()=>0.35},g);
    const sl=[[fr-6,-30],[fr+6,-24],[fx(70)-4,70],[fx(70)-22,70]];white(sl,{},g);hatch(shape(sl),{ang:75,gap:3.0,w:0.7,amp:0.3,dens:()=>0.5},g);
    ink(sl,{closed:true,taper:0,w:1.3,amp:0.2},g);
    const kr=[[bk-6,-34],[fr-4,-32],[fr-2,-18],[bk-8,-20]];white(kr,{curve:true},g);ink(kr,{curve:true,closed:true,taper:0,w:1.2,amp:0.2},g);
    stroke([[fr-10,-20],[fx(90)-12,90]],{w:0.8,amp:0.3,col:'#fff'},g);
    const kx=fx(96)-14;white([[kx-9,94],[kx+9,94],[kx+9,120],[kx-9,120]],{},g);ink([[kx-9,94],[kx+9,94],[kx+9,120],[kx-9,120]],{closed:true,taper:0,w:1.2,amp:0.2},g);
    stroke([[kx-6,104],[kx+6,104]],{w:0.7},g);stroke([[kx-6,110],[kx+4,110]],{w:0.7},g);
    framkant(70,200,-2);
  } else if(sh==='hoodie'){
    // Jasmins hettegenser: hetten i en klump bak nakken, snor foran, magelomme, strikk nederst
    hatch(bodyD,{ang:80,gap:5.5,w:0.5,amp:0.3,dens:()=>0.22},g);
    const ht=[[bk-4,-40],[fr-10,-36],[fr-6,-20],[fr-16,-6],[bk-20,10],[bk-30,0],[bk-26,-24]];white(ht,{curve:true},g);
    hatch(shape(ht,{curve:true}),{ang:0,gap:3.4,w:0.55,amp:0.3,dens:()=>0.4},g);ink(ht,{curve:true,closed:true,taper:0,w:1.7,amp:0.4},g);
    stroke([[fr-8,-6],[fr-4,30],[fr-2,60]],{curve:true,w:0.8,amp:0.3},g);
    stroke([[fx(130)-6,130],[fx(130)-34,134],[fx(172)-34,172],[fx(172)-4,172]],{curve:true,w:0.9,amp:0.3},g);
    ribbNed();
  } else if(sh==='polo'){
    // morens pikéskjorte: liten krage, knappestolpe, åpen nederst
    skjorteKrage();knapper([6,24]);framkant(-2,44,-6);
    hatch(bodyD,{ang:0,gap:5,w:0.5,amp:0.3,dens:()=>0.15},g);
    ink([[bx(196),196],[fx(196),196]],{w:1.0,amp:0.3,taper:0.5},g);
  } else if(sh==='vest'){
    // Kjetils mor: REMA-vesten over genseren. Vesten er lys med en kant, genseren under tett skravert.
    hatch(bodyD,{ang:0,gap:4.2,w:0.55,amp:0.4,dens:()=>0.42},g);
    const v=[[bk+2,-8],[fr-6,-6],[fx(40)+1,40],[fx(120)+1,120],[fx(176)+1,176],[bx(176)-1,176],[bx(120)-1,120],[bx(40)-1,40]];
    white(v,{curve:true},g);ink(v,{curve:true,closed:true,taper:0,w:1.6,amp:0.3},g);
    hatch(shape(v,{curve:true}),{ang:85,gap:6,w:0.5,amp:0.2,dens:()=>0.12},g);
    rundHals();
    framkant(0,176,-4);
    stroke([[fx(70)-28,70],[fx(70)-8,72]],{w:0.9,amp:0.2},g);stroke([[fx(80)-28,80],[fx(80)-8,82]],{w:0.9,amp:0.2},g);
  } else if(sh==='wind'){
    // vindjakke (Arvid, campingkvinnen): høy krage, glidelås, lett skravur, strikk nederst
    const col=[[bk-8,-34],[fr+2,-34],[fr+6,-10],[bk-10,-12]];white(col,{curve:true},g);ink(col,{curve:true,closed:true,taper:0,w:1.8,amp:0.3},g);
    stroke([[fr+4,-8],[fx(60)+2,60],[fx(130)+2,130],[fx(190)+1,190]],{curve:true,w:1.0,amp:0.3},g);
    for(let y=-4;y<188;y+=7)stroke([[fx(y)-1,y],[fx(y)+3,y+0.4]],{w:0.6,amp:0.05},g);
    hatch(bodyD,{ang:80,gap:7,w:0.5,amp:0.3,dens:()=>0.14},g);
    stroke([[bx(60)+6,40],[bx(60)+18,70]],{curve:true,w:0.8,amp:0.4},g);
    ink([[bx(192),192],[fx(192),192]],{w:1.1,amp:0.3,taper:0.5},g);
  } else if(sh==='work'){
    // lærlingens arbeidsjakke: skjortekrage, knapper, brystlomme med klaff
    skjorteKrage();knapper([10,50,90,130,170]);framkant(2,190,-6);
    const lx=fx(60)-30;stroke([[lx-10,56],[lx+12,56],[lx+12,84],[lx-10,84]],{closed:true,curve:true,w:0.9,amp:0.3},g);stroke([[lx-10,62],[lx+12,62]],{w:0.8},g);
    hatch(bodyD,{ang:85,gap:8,w:0.5,amp:0.3,dens:()=>0.1},g);
  } else if(sh==='overall'||sh==='hivis'){
    // kjeledress og hi-vis: skjorten under, så tegner kjeledressProfil og vestProfil (steder/kvilldal/felles.js) resten
    skjorteKrage();stroke([[fx(2)-2,2],[fx(60)-2,60]],{curve:true,w:0.9,amp:0.4},g);
  }
  skygge();
  stroke([[-4,44],[12,64],[22,86]],{curve:true,w:0.8,amp:0.5},g);
}

/* ----- hel sittende figur i profil. pose.x, pose.y = hoften i verden. ----- */
function seatedProfile(ch,pose,parent,s,frontParent){
  const oldU=U;U=1/s;srand(pose.seed||11);
  const lean=pose.lean||0;
  const tf=`translate(${pose.x} ${pose.y}) scale(${pose.flip?-s:s} ${s})`;
  const fig=G(parent,{class:'fig '+ch.name,transform:tf});
  if(pose.chair!==false)chairProfile(fig);
  legsSeated(fig,ch);
  const body=G(fig,{class:'body',transform:`rotate(${lean})`});
  const T=G(body,{class:'torso',transform:'translate(10 -200)'});
  const far=pose.farArm;
  const farO={shoulder:[-8,-6],L1:122,L2:100,wUp:19,wFo:14};
  if(far)armChain(T,Object.assign({},farO,far,{parts:'upper'}));
  torsoSeated(T,ch);
  const hg=G(T,{class:'headpos',transform:'translate(29 -154)'});
  const hd=headProfile(hg,ch,pose);
  // frontgruppe: samme kjede. Fjern underarm først, så nær arm.
  const fig2=G(frontParent||parent,{class:'fig-front '+ch.name,transform:tf});
  const T2=G(G(fig2,{class:'body',transform:`rotate(${lean})`}),{class:'torso',transform:'translate(10 -200)'});
  let afar=null;
  if(far&&!far.hidden)afar=armChain(T2,Object.assign({},farO,far,{parts:'lower'}));
  const near=pose.nearArm||{sh:-30,el:-62,hand:2,grip:'rest'};
  const anear=armChain(T2,Object.assign({shoulder:[0,0],L1:125,L2:104},near));
  U=oldU;
  return {fig,fig2,head:hd.head,jaw:hd.jaw,armNear:anear,armFar:afar};
}

/* =====================================================================
   HODE I TREKVART (nærbilder). Vender mot betrakterens høyre.
   ===================================================================== */
function eye34(g,cx,cy,w,h,open,far,o){
  o=o||{};
  const op=clamp(open==null?1:open);
  const hh=h*(0.3+0.7*op);
  const inner=[cx-w/2,cy+1.5],outer=[cx+w/2,cy-0.5];
  if(far){inner[0]=cx+w/2;inner[1]=cy+1.5;outer[0]=cx-w/2;outer[1]=cy-0.5;}
  const top=[[inner[0],inner[1]],[cx-w*0.15,cy-hh],[cx+w*0.25,cy-hh*0.9],[outer[0],outer[1]]];
  const bot=[[inner[0],inner[1]],[cx-w*0.1,cy+hh*0.75],[cx+w*0.25,cy+hh*0.6],[outer[0],outer[1]]];
  if(far){top[1]=[cx+w*0.15,cy-hh];top[2]=[cx-w*0.25,cy-hh*0.9];bot[1]=[cx+w*0.1,cy+hh*0.75];bot[2]=[cx-w*0.25,cy+hh*0.6];}
  // iris klippet av lokkene
  const lid=shape(top.concat(bot.slice(1,3).reverse()),{curve:true});
  const ig=clipG(lid,g);
  const r=h*1.15, ix=cx+(far?-w*0.02:w*0.05), iy=cy;
  E('circle',{cx:ix,cy:iy,r:r,fill:'none',stroke:'#000','stroke-width':1.1*U},ig);
  hatch(dstr(ellipsePts(ix,iy,r,r,20),true),{ang:90,gap:1.3,w:0.6,amp:0.1,dens:(x,y)=>clamp(0.4+Math.hypot(x-ix,y-iy)/r*0.5)},ig);
  E('circle',{cx:ix,cy:iy,r:r*0.42,fill:'#000'},ig);
  E('circle',{cx:ix-r*0.32,cy:iy-r*0.38,r:r*0.2,fill:'#fff'},ig);
  // lokk
  ink(top,{curve:true,w:2.4,amp:0.2,taper:0.6},g);
  stroke(bot,{curve:true,w:0.8,amp:0.15},g);
  // fold over lokket, og posen under
  stroke([[cx-w*0.42,cy-hh-3],[cx,cy-hh-4.2],[cx+w*0.42,cy-hh-2.6]],{curve:true,w:0.8,amp:0.2},g);
  stroke([[cx-w*0.45,cy+4],[cx,cy+6],[cx+w*0.4,cy+4.5]],{curve:true,w:0.6,amp:0.2},g);
  if(o.crow){for(let i=0;i<3;i++)stroke([[outer[0]+(far?-1:1),outer[1]-1+i*2.2],[outer[0]+(far?-6:6),outer[1]-4+i*4]],{w:0.7,amp:0.2},g);}
}
function head34(fig,ch,pose){
  const m=mouthOf(pose), jawOpen=m.jaw, rr=m.round, st=m.stretch, pr=m.press, th=m.teeth;
  const head=G(fig,{class:'head',transform:`rotate(${pose.headTilt||0} 0 125)`});
  const jaw=G(head,{class:'jaw',transform:`translate(0 ${jawOpen*9})`});
  const outline=[[-4,-2],[16,0],[30,6],[40,16],[45,30],[46,42],[44,52],[42,62],[40,72],[36,84],[28,94],[16,101],[6,103],[-8,101],[-22,95],[-32,86],[-38,74],[-42,60],[-44,46],[-45,32],[-42,18],[-34,7],[-20,0]];
  white(outline,{curve:true},head);
  // kontur over munnen (hodegruppen)
  ink([[-34,7],[-20,0],[-4,-2],[16,0],[30,6],[40,16],[45,30],[46,42],[44,52],[42,62]],{curve:true,w:2.2,amp:0.4,taper:0.6},head);
  ink([[-42,60],[-44,46],[-45,32],[-42,18],[-34,7]],{curve:true,w:2.0,amp:0.4,taper:0.6},head);
  // øre (fjern side)
  ink([[-42,44],[-48,42],[-52,50],[-50,60],[-46,67],[-41,64]],{curve:true,w:1.6,amp:0.3},head);
  stroke([[-45,48],[-48,55],[-46,62]],{curve:true,w:0.9,amp:0.2},head);
  // nese: rygg på fjern side, tupp, nesevinge nær
  const nl=ch.nose;
  // neseryggen på fjern side, ned til tuppen; nesevingen nær; ett nesebor
  ink([[9,42],[12,52],[16,62*nl],[21,68*nl],[27,70*nl],[31,67*nl]],{curve:true,w:1.8,amp:0.3,taper:0.6},head);
  stroke([[19,68*nl],[17,70*nl],[20,71.5*nl]],{curve:true,w:1.0,amp:0.15},head);
  stroke([[23,71.5*nl],[29,72*nl]],{w:1.4,amp:0.1},head);
  hatch(shape([[3,44],[10,43],[15,60],[20,68*nl],[12,68*nl],[5,58]],{curve:true}),{ang:100,gap:2.4,w:0.7,dens:(x,y)=>clamp(0.15+(x-3)/14)*0.7},head);
  hatch(shape([[14,71*nl],[33,72*nl],[31,77*nl],[14,77*nl]],{curve:true}),{ang:10,gap:2.2,w:0.7,dens:()=>0.6},head);
  // øyne
  const br=(pose.brow||0);
  eye34(head,27,47,17,5.6,pose.eyeOpen,false,{crow:ch.stubble});
  eye34(head,-11,48,13,5.0,pose.eyeOpen,true,{crow:ch.stubble});
  // bryn: tykke, med hårstrå
  const b1=[[12,39-br*2.5],[20,35.5-br*3.5],[31,35-br*3],[40,39-br*1.5]];
  const b2=[[-28,41-br*1.5],[-20,37.5-br*3],[-9,37-br*3],[-1,39.5-br*2.5]];
  ink(b1,{curve:true,w:3.0*ch.brow,amp:0.3,taper:1.4},head);
  ink(b2,{curve:true,w:2.6*ch.brow,amp:0.3,taper:1.4},head);
  for(let i=0;i<11;i++){const t=i/10;const x=12+t*28,y=39-br*2.5-Math.sin(t*3.1)*3.6;stroke([[x,y+0.7],[x+2.4,y-1.8]],{w:0.9,amp:0.1},head);}
  for(let i=0;i<8;i++){const t=i/7;const x=-28+t*27,y=41-br*1.5-Math.sin(t*3.1)*3.6;stroke([[x,y+0.6],[x+2.2,y-1.6]],{w:0.9,amp:0.1},head);}
  if(br>0.3){stroke([[-26,29],[-6,26],[16,26],[36,29]],{curve:true,w:0.7,amp:0.3},head);stroke([[-20,23],[0,21],[22,22]],{curve:true,w:0.6,amp:0.3},head);}
  // skygge under brynene, i tinningen og under kinnbeinet på fjern side
  hatch(shape([[-30,41],[-2,42],[-4,52],[-30,53]],{curve:true}),{ang:15,gap:2.6,w:0.7,dens:()=>0.45},head);
  hatch(shape([[10,41],[42,42],[44,52],[14,54]],{curve:true}),{ang:15,gap:2.6,w:0.7,dens:()=>0.35},head);
  hatch(shape([[-45,30],[-36,34],[-30,52],[-30,72],[-38,80],[-42,64]],{curve:true}),{ang:75,gap:3.4,w:0.8,dens:(x,y)=>clamp(0.15+(-x-30)/16)},head);
  cross(shape([[-45,30],[-36,34],[-30,52],[-30,72],[-38,80],[-42,64]],{curve:true}),{ang:20,gap:4,w:0.7,dens:(x,y)=>clamp(0.05+(-x-36)/12)*0.6},head);
  hatch(shape([[-40,56],[-30,58],[-14,72],[-8,84],[-24,90],[-36,80]],{curve:true}),{ang:60,gap:3.6,w:0.7,dens:(x,y)=>clamp(0.05+(-x-16)/30)*0.5},head);
  hatch(shape([[32,56],[46,50],[44,64],[38,80],[30,80]],{curve:true}),{ang:70,gap:3.8,w:0.7,dens:(x,y)=>clamp((x-30)/18)*0.45},head);
  // nasolabialfure
  stroke([[30,68],[34,78],[32,86]],{curve:true,w:0.9,amp:0.3},head);
  stroke([[-2,68],[-8,78],[-8,86]],{curve:true,w:0.8,amp:0.3},head);
  // munn i trekvart. Samme parametre som i profil (mouthOf).
  const droop=ch.stubble?1.5:0.6;
  const wf=(1-0.45*rr)*(1+0.2*st), mcx=10;                 // bredde: runding smalner, strekk vider
  const xl=mcx-16*wf, xr=mcx+15*wf;
  const lift=rr*3.5;                                        // rund munn: overleppen løftes i midten
  const cy0=81+droop-st*1.5+pr*0.3;                         // munnvikenes høyde
  ink([[xl,cy0],[mcx-8,79.5-lift+pr*0.4],[mcx,80-lift+pr*0.4],[mcx+7,79.5-lift+pr*0.4],[xr,cy0]],{curve:true,w:1.9+pr*0.5,amp:0.2,taper:0.8},head);
  stroke([[xl+3,77-lift*0.6],[mcx-4,76-lift],[mcx,76.6-lift],[mcx+4,76-lift],[xr-2,77.5-lift*0.6]],{curve:true,w:0.8+rr*0.5,amp:0.2},head);
  stroke([[mcx,72],[mcx-1,76.5-lift]],{w:0.7,amp:0.1},head);
  if(!th&&(jawOpen>0.06||rr>0.3)){
    const h=jawOpen*14+rr*4;
    if(rr>0.5)black(ellipsePts(mcx-0.5,80.4-lift+(h+lift)/2,15.5*wf,(h+lift)/2,26),{curve:true},head);
    else black([[xl+1,cy0+0.6],[mcx,80.6-lift],[xr-1,cy0+0.6],[mcx+7*wf,80+h],[mcx-8*wf,80+h]],{curve:true},head);
    if(jawOpen>0.1&&rr<0.5)stroke([[xl+4,cy0+2],[mcx,82.4],[xr-4,cy0+2]],{curve:true,w:jawOpen<0.25?1.0:1.6,amp:0.1,col:'#fff'},head);
  }
  if(th){
    // G: overtennene på underleppen, en hvit rad med mørkt under
    black([[xl+2,cy0+0.4],[mcx,80.6],[xr-2,cy0+0.4],[xr-4,cy0+4],[mcx,84.8],[xl+4,cy0+4]],{curve:true},head);
    white([[xl+5,cy0+1.2],[mcx,81.4],[xr-5,cy0+1.2],[xr-6,cy0+3.2],[mcx,83.6],[xl+6,cy0+3.2]],{curve:true},head);
  }
  // --- kjeve
  white([[36,84],[28,94],[16,101],[6,103],[-8,101],[-22,95],[-32,86],[-30,84],[-14,88],[10,90],[30,88]],{curve:true},jaw);
  ink([[42,62],[40,72],[36,84],[28,94],[16,101],[6,103],[-8,101],[-22,95],[-32,86],[-38,74],[-42,60]],{curve:true,w:2.4,amp:0.4,taper:0.5},jaw);
  const ll=85+jawOpen*5+rr*2-th*1.5-pr*2;
  ink([[xl+4,ll],[mcx,ll+1.5+rr*1.5-th*1.2],[xr-4,ll]],{curve:true,w:1.2+rr*0.6+pr*0.8,amp:0.2,taper:1},jaw);
  if(pr>0.3)stroke([[xl+6,ll+3.5],[mcx,ll+5],[xr-6,ll+3.5]],{curve:true,w:0.7,amp:0.2},jaw);
  hatch(shape([[-4,88],[22,88],[22,92],[8,94],[-4,92]],{curve:true}),{ang:0,gap:2.2,w:0.7,dens:()=>0.5},jaw);
  hatch(shape([[-34,86],[-12,94],[8,98],[26,92],[30,96],[16,102],[0,104],[-20,100],[-36,90]],{curve:true}),{ang:20,gap:3.2,w:0.8,dens:(x,y)=>clamp(0.3+(y-88)/14)},jaw);
  if(ch.beard){
    const jb=shape([[43,60],[44,72],[40,84],[32,96],[18,104],[4,106],[-12,104],[-28,98],[-38,88],[-44,72],[-44,58],[-34,66],[-24,78],[-10,88],[4,90],[18,88],[30,80],[38,70]],{curve:true});
    strokesIn(jb,{n:5200,len:8,w:1.05,angf:(x,y)=>92+x*1.1+(y-90)*0.3,dens:(x,y)=>clamp(0.55+(y-72)/30)},jaw);
    const cb=shape([[-44,52],[-36,54],[-26,66],[-12,80],[-2,85],[22,85],[36,74],[44,54],[46,60],[44,72],[38,82],[30,88],[-6,92],[-30,86],[-42,74]],{curve:true});
    strokesIn(cb,{n:1800,len:7,w:0.95,angf:(x,y)=>92+x*1.1,dens:(x,y)=>clamp(0.2+(y-56)/22)},head);
    strokesIn(shape([[-8,69],[6,71],[24,71],[28,74],[24,79],[10,77.5],[-6,79]],{curve:true}),{n:700,len:5.5,w:0.95,angf:(x,y)=>110-(x-8)*1.6},head);
    // skjeggets ytterkant mot kinnet: en brutt linje
    stroke([[-40,58],[-30,64],[-20,74],[-10,82]],{curve:true,w:0.8,amp:0.8},head);
    stroke([[44,58],[38,66],[34,76]],{curve:true,w:0.8,amp:0.8},head);
  } else if(ch.stubble){
    stipple(shape([[41,74],[36,86],[28,96],[16,103],[2,105],[-12,103],[-28,97],[-38,88],[-42,74],[-34,78],[-16,88],[4,92],[24,88],[36,80]],{curve:true}),{n:2600,r:0.55,dens:(x,y)=>clamp(0.15+(y-76)/30)},jaw);
    stipple(shape([[-6,70],[26,71],[26,78],[-6,79]],{curve:true}),{n:260,r:0.5,dens:()=>0.45},head);
  }
  if(ch.cap){
    const crown=[[-48,32],[-46,16],[-38,4],[-24,-6],[-4,-10],[18,-8],[36,0],[46,12],[50,26],[50,32]];
    white(crown.concat([[50,36],[-48,36]]),{curve:true},head);
    ink(crown,{curve:true,w:2.6,amp:0.4,taper:0.5},head);
    ink([[-48,33],[-30,35],[0,36],[28,35],[50,32]],{curve:true,w:2.0,amp:0.3,taper:0.6},head);
    stroke([[-4,-10],[0,6],[3,22],[4,35]],{curve:true,w:0.8,amp:0.2},head);
    stroke([[-4,-10],[-22,-2],[-36,10],[-42,30]],{curve:true,w:0.8,amp:0.2},head);
    stroke([[-4,-10],[16,-4],[34,8],[42,28]],{curve:true,w:0.8,amp:0.2},head);
    hatch(shape(crown.concat([[50,36],[-48,36]]),{curve:true}),{ang:65,gap:3.4,w:0.8,dens:(x,y)=>clamp(0.2+(-x-10)/60)+0.15},head);
    hatch(shape(crown.concat([[50,36],[-48,36]]),{curve:true}),{ang:120,gap:4.4,w:0.7,dens:(x,y)=>clamp(0.0+(-x-20)/40)*0.6},head);
    E('circle',{cx:-4,cy:-10,r:2.2,fill:'#000'},head);
    // brem: fram og mot høyre
    const brim=[[-14,35],[8,34],[30,33],[50,33],[68,37],[76,43],[68,48],[50,46],[30,42],[8,39],[-12,38]];
    white(brim,{curve:true},head);
    ink(brim,{curve:true,closed:true,taper:0,w:2.2,amp:0.3},head);
    hatch(shape([[-12,38],[8,39],[30,42],[50,46],[68,48],[74,44],[66,39],[50,36],[30,35],[8,36],[-12,36.5]],{curve:true}),{ang:5,gap:2.0,w:0.8},head);
    // skyggen bremmen kaster over panne og øyne
    hatch(shape([[-44,38],[50,36],[48,48],[30,46],[10,48],[-14,48],[-34,50],[-44,46]],{curve:true}),{ang:10,gap:2.6,w:0.8,dens:(x,y)=>clamp(0.65+(40-y)/10)},head);
    strokesIn(shape([[-46,36],[-38,36],[-40,46],[-46,46]],{curve:true}),{n:40,len:5,w:0.9,ang:80},head);
  } else if(ch.hair==='short'){
    const h=[[-45,32],[-46,16],[-38,4],[-22,-4],[-2,-6],[18,-4],[34,2],[42,12],[46,24],[44,20],[34,16],[18,14],[2,15],[-12,19],[-26,28],[-36,40],[-42,50],[-44,46]];
    white(h,{curve:true},head);
    strokesIn(shape(h,{curve:true}),{n:7000,len:11,w:1.0,angf:(x,y)=>Math.atan2(y+8,x+12)*180/Math.PI,dens:(x,y)=>clamp(0.6+(-x)/90)},head);
    ink([[-46,16],[-38,4],[-22,-4],[-2,-6],[18,-4],[34,2],[42,12],[46,24]],{curve:true,w:1.4,amp:0.8,taper:1},head);
    stroke([[44,20],[34,16],[18,14],[2,15],[-12,19],[-26,28],[-36,40]],{curve:true,w:0.9,amp:1.2},head);
  }
  return {head,jaw};
}
function torso34(fig,ch){
  const g=G(fig,{class:'torso'});
  // hals først (under kragen)
  white([[-30,90],[30,90],[30,140],[-30,140]],{},g);
  ink([[26,98],[28,114],[28,132]],{curve:true,w:1.8,amp:0.3},g);
  ink([[-28,94],[-31,112],[-31,132]],{curve:true,w:2.0,amp:0.3},g);
  hatch(shape([[-30,94],[-12,102],[8,104],[26,98],[28,134],[-31,134]],{curve:true}),{ang:80,gap:4.0,w:0.9,dens:(x,y)=>clamp(0.25+(y-96)/40)},g);
  hatch(shape([[-30,94],[-12,102],[8,104],[26,98],[28,134],[-31,134]],{curve:true}),{ang:20,gap:4.5,w:0.8,dens:(x,y)=>clamp(0.15+(-x)/50)},g);
  const body=[[-40,124],[-64,130],[-92,142],[-112,162],[-120,200],[-124,400],[124,400],[120,200],[112,162],[92,142],[64,130],[40,124]];
  white(body,{curve:true},g);
  if(ch.shirt==='fleece'){
    // høy fleecekrage: bakkant bak halsen, framkant rundt halsen
    const col=[[-36,106],[-20,103],[0,102],[20,103],[36,106],[42,122],[24,127],[0,129],[-24,127],[-42,122]];
    white(col,{curve:true},g);
    white([[-27,96],[27,96],[28,118],[-30,118]],{},g);
    ink([[26,98],[28,110],[28,122]],{curve:true,w:1.8,amp:0.3},g);
    ink([[-28,94],[-31,108],[-31,122]],{curve:true,w:2.0,amp:0.3},g);
    hatch(shape([[-30,94],[-12,102],[8,104],[26,98],[28,122],[-31,122]],{curve:true}),{ang:80,gap:4.0,w:0.9,dens:(x,y)=>clamp(0.3+(y-96)/34)},g);
    hatch(shape([[-30,94],[-12,102],[8,104],[26,98],[28,122],[-31,122]],{curve:true}),{ang:20,gap:4.5,w:0.8,dens:(x,y)=>clamp(0.15+(-x)/50)},g);
    ink([[-36,106],[-33,104],[-31,106]],{curve:true,w:1.8,amp:0.3,taper:0.5},g);
    ink([[28,106],[33,104],[36,106]],{curve:true,w:1.8,amp:0.3,taper:0.5},g);
    ink([[-42,122],[-24,127],[0,129],[24,127],[42,122]],{curve:true,w:2.2,amp:0.4,taper:0.5},g);
    ink([[-36,106],[-42,122]],{curve:true,w:2.0,amp:0.3,taper:0.5},g);
    ink([[36,106],[42,122]],{curve:true,w:2.0,amp:0.3,taper:0.5},g);
    ink([[-42,122],[-64,128],[-92,140],[-112,162],[-120,220]],{curve:true,w:2.3,amp:0.5,taper:0.5},g);
    ink([[42,122],[64,128],[92,140],[112,162],[120,220]],{curve:true,w:2.3,amp:0.5,taper:0.5},g);
    stroke([[0,129],[1,200],[2,400]],{curve:true,w:1.3,amp:0.3},g);
    for(let y=133;y<400;y+=6)stroke([[-1.5,y],[3.5,y+0.5]],{w:0.7,amp:0.05},g);
    hatch(shape([[-36,108],[36,108],[42,122],[0,129],[-42,122]],{curve:true}),{ang:0,gap:3.0,w:0.8,dens:(x,y)=>clamp(0.15+(y-110)/16)},g);
    hatch(shape([[-120,162],[-42,126],[-4,132],[-2,400],[-120,400]],{curve:true}),{ang:75,gap:5.5,w:0.9,dens:(x,y)=>clamp(0.05+(-x-46)/100)},g);
    hatch(shape([[4,132],[42,126],[120,162],[120,400],[4,400]],{curve:true}),{ang:105,gap:6,w:0.8,dens:(x,y)=>clamp(0.0+(x-60)/180)*0.6},g);
    // ermsøm og skulderfold
    stroke([[-66,130],[-76,170],[-80,222]],{curve:true,w:0.9,amp:0.4},g);
    stroke([[66,130],[76,170],[80,222]],{curve:true,w:0.9,amp:0.4},g);
    stroke([[-40,150],[-30,180],[-24,220]],{curve:true,w:0.7,amp:0.5},g);
    stroke([[44,152],[34,182],[30,222]],{curve:true,w:0.7,amp:0.5},g);
  } else {
    ink([[-40,124],[-64,130],[-92,142],[-112,162],[-120,220]],{curve:true,w:2.3,amp:0.5,taper:0.5},g);
    ink([[40,124],[64,130],[92,142],[112,162],[120,220]],{curve:true,w:2.3,amp:0.5,taper:0.5},g);
    ink([[-30,120],[-48,110],[-32,102],[-12,110],[-2,124]],{curve:true,w:1.9,amp:0.3,taper:0.5},g);
    ink([[27,120],[44,108],[28,100],[10,108],[2,124]],{curve:true,w:1.9,amp:0.3,taper:0.5},g);
    ink([[-48,110],[-56,130],[-52,170],[-46,220],[-42,400]],{curve:true,w:1.8,amp:0.4,taper:0.6},g);
    ink([[44,108],[54,130],[50,170],[46,220],[44,400]],{curve:true,w:1.8,amp:0.4,taper:0.6},g);
    stroke([[-30,124],[-14,134],[0,136],[14,134],[27,124]],{curve:true,w:1.2,amp:0.3},g);
    const left=shape([[-120,162],[-92,142],[-56,130],[-46,220],[-42,400],[-120,400]],{curve:true});
    const right=shape([[120,162],[92,142],[54,130],[46,220],[44,400],[120,400]],{curve:true});
    for(const d of [left,right]){hatch(d,{ang:92,gap:24,w:1.5,amp:0.5},g);hatch(d,{ang:4,gap:24,w:1.5,amp:0.5},g);hatch(d,{ang:92,gap:8,w:0.5,amp:0.3,dens:()=>0.7},g);}
    hatch(left,{ang:75,gap:5,w:0.9,dens:(x,y)=>clamp(0.05+(-x-64)/80)},g);
    hatch(shape([[-42,136],[42,136],[44,400],[-42,400]],{curve:true}),{ang:80,gap:6,w:0.8,dens:(x,y)=>clamp(0.1+(y-140)/300)*0.7},g);
  }
  return g;
}
function figure34(ch,pose,parent,s){
  const oldU=U;U=1/s;srand(pose.seed||5);
  const fig=G(parent,{class:'fig '+ch.name,transform:`translate(${pose.x} ${pose.y}) scale(${pose.flip?-s:s} ${s})`});
  const torso=torso34(fig,ch);
  const aL=G(torso,{class:'arm',transform:'translate(-125 200) rotate(0)'});
  const aR=G(torso,{class:'arm',transform:'translate(125 200) rotate(0)'});
  const hd=head34(fig,ch,pose);
  U=oldU;
  return {fig,torso,head:hd.head,jaw:hd.jaw,armNear:aR,armFar:aL};
}

/* =====================================================================
   REKVISITTER
   ===================================================================== */
function plateKomle(g,cx,cy,rx){
  const ry=rx*0.36;
  white(ellipsePts(cx,cy,rx,ry,36),{curve:true},g);
  ink(ellipsePts(cx,cy,rx,ry,36),{curve:true,closed:true,taper:0,w:1.8,amp:0.4},g);
  stroke(ellipsePts(cx,cy,rx*0.82,ry*0.78,36),{curve:true,closed:true,w:0.8,amp:0.3},g);
  hatch(dstr(ellipsePts(cx,cy+ry*0.55,rx*0.9,ry*0.35,30),true),{ang:0,gap:2.6,w:0.6,dens:()=>0.3},g);
  const ks=[[cx-rx*0.36,cy-ry*0.05,rx*0.22],[cx+rx*0.02,cy-ry*0.25,rx*0.21],[cx+rx*0.3,cy+ry*0.1,rx*0.2]];
  for(const [kx,ky,kr] of ks){
    const pts=ellipsePts(kx,ky,kr,kr*0.8,14).map(p=>[p[0]+R(-1,1)*kr*0.05,p[1]+R(-1,1)*kr*0.05]);
    white(pts,{curve:true},g);ink(pts,{curve:true,closed:true,taper:0,w:1.3,amp:0.4},g);
    hatch(shape(pts,{curve:true}),{ang:35,gap:2.4,w:0.7,dens:(x,y)=>clamp(0.05+((x-kx)/kr+(y-ky)/kr)*0.7)},g);
    stipple(shape(pts,{curve:true}),{n:25,r:0.6},g);
  }
  const st=[[cx-rx*0.2,cy+ry*0.15],[cx-rx*0.05,cy-ry*0.05],[cx+rx*0.2,cy+ry*0.05],[cx+rx*0.35,cy+ry*0.45],[cx+rx*0.05,cy+ry*0.6],[cx-rx*0.25,cy+ry*0.5]];
  white(st,{curve:true},g);stroke(st,{curve:true,closed:true,w:1.0,amp:0.5},g);
  stipple(shape(st,{curve:true}),{n:70,r:0.6},g);
  const meat=[[cx-rx*0.62,cy+ry*0.2],[cx-rx*0.3,cy+ry*0.35],[cx-rx*0.28,cy+ry*0.6],[cx-rx*0.6,cy+ry*0.5]];
  white(meat,{curve:true},g);ink(meat,{curve:true,closed:true,taper:0,w:1.2,amp:0.3},g);
  hatch(shape(meat,{curve:true}),{ang:20,gap:2.2,w:0.9},g);
  const but=[[cx+rx*0.35,cy-ry*0.35],[cx+rx*0.52,cy-ry*0.3],[cx+rx*0.5,cy-ry*0.1],[cx+rx*0.33,cy-ry*0.15]];
  stroke(but,{curve:false,closed:true,w:0.9,amp:0.2},g);
}
function beerGlass(g,x,y,h){
  const w=h*0.36;
  const glass=[[x-w/2,y],[x-w*0.44,y-h*0.55],[x-w*0.5,y-h],[x+w*0.5,y-h],[x+w*0.44,y-h*0.55],[x+w/2,y]];
  white(glass,{curve:false},g);
  ink(glass,{curve:true,w:1.6,amp:0.2,closed:true,taper:0},g);
  const beer=shape([[x-w*0.46,y-h*0.12],[x+w*0.46,y-h*0.12],[x+w*0.44,y-h*0.7],[x-w*0.44,y-h*0.7]]);
  hatch(beer,{ang:90,gap:2.6,w:0.8,dens:(px,py)=>clamp(0.3+(px-x)/w*0.9)},g);
  stroke(ellipsePts(x,y-h*0.7,w*0.44,w*0.1,20),{curve:true,closed:true,w:0.8,amp:0.3},g);
  const foam=ellipsePts(x,y-h*0.76,w*0.46,w*0.12,20).map(p=>[p[0],p[1]+R(-1,1)]);
  white(foam,{curve:true},g);stroke(foam,{curve:true,closed:true,w:0.7,amp:0.6},g);
  stipple(beer,{n:30,r:0.5},g);
  stroke(ellipsePts(x,y,w*0.5,w*0.12,20,0,Math.PI),{curve:true,w:1.0,amp:0.2},g);
}
function coffeeCup(g,x,y,r){
  white(ellipsePts(x,y,r,r*0.35,24),{curve:true},g);
  white([[x-r,y],[x-r*0.85,y+r*1.1],[x+r*0.85,y+r*1.1],[x+r,y]],{},g);
  ink([[x-r,y],[x-r*0.9,y+r*0.8],[x-r*0.75,y+r*1.1],[x+r*0.75,y+r*1.1],[x+r*0.9,y+r*0.8],[x+r,y]],{curve:true,w:1.6,amp:0.2,taper:0.4},g);
  ink(ellipsePts(x,y,r,r*0.35,24),{curve:true,closed:true,taper:0,w:1.5,amp:0.2},g);
  hatch(dstr(ellipsePts(x,y,r*0.85,r*0.28,20),true),{ang:0,gap:2,w:0.9,dens:()=>0.9},g);
  ink([[x+r*0.95,y+r*0.25],[x+r*1.5,y+r*0.35],[x+r*1.45,y+r*0.85],[x+r*0.9,y+r*0.9]],{curve:true,w:1.5,amp:0.2,taper:0.4},g);
  hatch(shape([[x-r,y+r*0.2],[x-r*0.3,y+r*0.35],[x-r*0.3,y+r*1.1],[x-r*0.8,y+r*1.1]],{curve:true}),{ang:80,gap:2.6,w:0.7,dens:(px,py)=>clamp(0.2+(x-r*0.3-px)/r)},g);
  stroke(ellipsePts(x,y+r*1.15,r*1.6,r*0.5,24,0.1,Math.PI-0.1),{curve:true,w:1.1,amp:0.3},g);
}
function candle(g,x,y,h){
  white([[x-5,y-h],[x+5,y-h],[x+6,y],[x-6,y]],{},g);
  ink([[x-5,y-h],[x-5.5,y]],{w:1.2,amp:0.3},g);ink([[x+5,y-h],[x+5.5,y]],{w:1.2,amp:0.3},g);
  stroke(ellipsePts(x,y-h,5,1.6,12),{curve:true,closed:true,w:0.8,amp:0.2},g);
  stroke([[x,y-h],[x,y-h-7]],{w:0.8,amp:0.1},g);
  ink([[x,y-h-24],[x+3.5,y-h-13],[x,y-h-7],[x-3.5,y-h-13],[x,y-h-24]],{curve:true,w:1.0,amp:0.2,taper:0.4},g);
  ink([[x-9,y],[x+9,y]],{w:1.8,amp:0.2,taper:0.5},g);
  ink(ellipsePts(x,y+2,11,3.5,16,0,Math.PI),{curve:true,w:1.2,amp:0.2},g);
}
function saltPepper(g,x,y){
  for(let i=0;i<2;i++){const sx=x+i*16;
    white([[sx-5,y-26],[sx+5,y-26],[sx+6,y],[sx-6,y]],{},g);
    ink([[sx-5,y-22],[sx-6,y]],{w:1.1,amp:0.2},g);ink([[sx+5,y-22],[sx+6,y]],{w:1.1,amp:0.2},g);
    ink(ellipsePts(sx,y-24,5,4,12,Math.PI,2*Math.PI),{curve:true,w:1.1,amp:0.2},g);
    stroke([[sx-5,y-18],[sx+5,y-18]],{w:0.8},g);
    if(i==1)hatch(shape([[sx-5,y-17],[sx+5,y-17],[sx+6,y-1],[sx-6,y-1]]),{ang:70,gap:2,w:0.7},g);
    else stipple(shape([[sx-5,y-16],[sx+5,y-16],[sx+6,y-1],[sx-6,y-1]]),{n:35,r:0.5},g);
    stroke(ellipsePts(sx,y,6,2,12,0,Math.PI),{curve:true,w:0.9},g);
  }
}
function knife(g,x,y,ang){
  const gg=G(g,{transform:`translate(${x} ${y}) rotate(${ang})`});
  ink([[0,0],[36,0]],{w:2.4,amp:0.2,taper:0.5},gg);
  white([[34,-3],[64,-2],[70,1],[36,3]],{},gg);
  ink([[34,-3],[64,-2],[70,1],[36,3]],{curve:true,closed:true,taper:0,w:1.0,amp:0.15},gg);
}

/* ---------- utsikten gjennom et vindu: kveldshimmel, fjell, granskog, fonn, gatelys ---------- */
function viewScene(wx,wy,ww,wh,k){
  // k skalerer detaljnivået (nærbilder: mindre detalj, glasset er ute av fokus)
  return (x,y,w,h,g)=>{
    const gg=clipG(dstr(rect(x,y,w,h),true),g);
    const u=wh/380, v=ww/520;
    const ridge=[[wx-10,wy+150*u],[wx+80*v,wy+110*u],[wx+170*v,wy+140*u],[wx+260*v,wy+90*u],[wx+340*v,wy+120*u],[wx+430*v,wy+70*u],[wx+530*v,wy+120*u]];
    const sky=ridge.concat([[wx+ww+10,wy-10],[wx-10,wy-10]]);
    cross(shape(sky,{curve:true}),{ang:35,gap:3.0,w:1.0,amp:0.6,dens:(px,py)=>clamp(0.7+(wy+110*u-py)/(200*u))},gg);
    const mount=ridge.concat([[wx+ww+10,wy+270*u],[wx-10,wy+270*u]]);
    hatch(shape(mount,{curve:true}),{ang:-60,gap:4,w:0.9,dens:(px,py)=>clamp(0.1+(py-wy-100*u)/(160*u))*0.5*k},gg);
    strokesIn(shape(mount,{curve:true}),{n:Math.round(120*k),len:14,w:1.2,ang:-55,dens:(px,py)=>clamp((py-wy-120*u)/(120*u))},gg);
    const fr=[];for(let fx=wx-10;fx<=wx+ww+10;fx+=9)fr.push([fx,wy+250*u+Math.sin(fx/30)*8+R(-6,6)]);
    black(fr.concat([[wx+ww+10,wy+290*u],[wx-10,wy+290*u]]),{},gg);
    const dr=[[wx-10,wy+300*u],[wx+90*v,wy+280*u],[wx+200*v,wy+262*u],[wx+330*v,wy+270*u],[wx+440*v,wy+250*u],[wx+540*v,wy+275*u]];
    white(dr.concat([[wx+ww+10,wy+wh+40],[wx-10,wy+wh+40]]),{curve:true},gg);
    ink(dr,{curve:true,w:1.6,amp:0.8,taper:0},gg);
    hatch(shape(dr.concat([[wx+ww+10,wy+wh+40],[wx-10,wy+wh+40]]),{curve:true}),{ang:0,gap:5,w:0.7,amp:1.5,dens:(px,py)=>clamp((py-wy-330*u)/(120*u))*0.3},gg);
    ink([[wx+400*v,wy+130*u],[wx+402*v,wy+262*u]],{w:2.2,amp:0.2,taper:0},gg);
    black([[wx+392*v,wy+128*u],[wx+412*v,wy+128*u],[wx+410*v,wy+136*u],[wx+394*v,wy+136*u]],{},gg);
    E('ellipse',{cx:wx+402*v,cy:wy+140*u,rx:8,ry:3,fill:'#fff'},gg);
    // gjenskinn i glasset: papiret får stå
    white([[x+w*0.74,y],[x+w*0.86,y],[x+w*0.62,y+h],[x+w*0.5,y+h]],{},gg);
  };
}
/* ---------- vindu med sprosser: to rammer, 2x3 ruter hver ---------- */
function window2(g,x,y,w,h,o){
  o=o||{};
  const fr=o.frame||10, mid=o.mid||6;
  white(rect(x,y,w,h),{},g);
  ink(rect(x,y,w,h),{closed:true,taper:0,w:3,amp:0.3},g);
  ink(rect(x+fr,y+fr,w-2*fr,h-2*fr),{closed:true,taper:0,w:1.6,amp:0.25},g);
  hatch(shape([[x,y],[x+fr,y+fr],[x+fr,y+h-fr],[x,y+h]]),{ang:70,gap:2.2,w:0.7},g);
  hatch(shape([[x,y],[x+w,y],[x+w-fr,y+fr],[x+fr,y+fr]]),{ang:0,gap:2.2,w:0.7},g);
  const gx=x+fr,gy=y+fr,gw=w-2*fr,gh=h-2*fr;
  black(rect(gx+gw/2-mid/2,gy,mid,gh),{},g);
  for(let s=0;s<2;s++){
    const sw=gw/2-mid/2, sx0=s?gx+gw/2+mid/2:gx;
    ink(rect(sx0+2,gy+2,sw-4,gh-4),{closed:true,taper:0,w:1.8,amp:0.2},g);
    const cw=(sw-4)/2, ch=(gh-4)/3;
    if(o.glass)for(let i=0;i<2;i++)for(let r=0;r<3;r++)o.glass(sx0+2+i*cw,gy+2+r*ch,cw,ch,g);
    ink([[sx0+2+cw,gy+2],[sx0+2+cw,gy+gh-2]],{w:1.6,amp:0.15,taper:0.2},g);
    for(let r=1;r<3;r++)ink([[sx0+2,gy+2+ch*r],[sx0+sw-2,gy+2+ch*r]],{w:1.6,amp:0.15,taper:0.2},g);
  }
}

/* ---------- bord med to menn. Gjenbrukes av kafeen og positurarket. ----------
   o.y = bordets fjerne kant (bordplaten). Underarmene hviler 44 px under den.
   o.x0, o.x1 = fjern kant venstre/høyre. o.dep = bordets dybde i px. o.s = figurskala.
   Rekkefølge: stoler og kropper, bord, ting på bordet, armene over bordet.        */
function tableScene(parent,o){
  const s=o.s, y=o.y, H=1080;
  const hipY=y+44+80*s;
  const jonX=o.x0+40-73*s, geirX=o.x1-40+73*s;
  const back=G(parent,{class:'bak-figurer'});
  const tg=G(parent,{class:'bord'});
  const front=G(parent,{class:'front'});
  const jon=seatedProfile(JON,Object.assign({x:jonX,y:hipY,seed:31},o.jon),back,s,front);
  const geir=seatedProfile(GEIR,Object.assign({x:geirX,y:hipY,seed:47,flip:true},o.geir),back,s,front);
  // bordplaten
  const nx0=o.nx0==null?o.x0-160:o.nx0, nx1=o.nx1==null?o.x1+160:o.nx1, dep=o.dep||170, ap=Math.round(26*s/1.35);
  const tl=[[o.x0,y],[o.x1,y],[nx1,y+dep],[nx0,y+dep]];
  white(tl,{},tg);
  ink([[o.x0,y],[o.x1,y]],{w:2.4,amp:0.5,taper:0},tg);
  ink([[o.x1,y],[nx1,y+dep]],{w:2.4,amp:0.4,taper:0},tg);
  ink([[o.x0,y],[nx0,y+dep]],{w:2.4,amp:0.4,taper:0},tg);
  ink([[nx0,y+dep],[nx1,y+dep]],{w:3.6,amp:0.5,taper:0},tg);
  white(rect(nx0,y+dep,nx1-nx0,ap),{},tg);
  ink([[nx0,y+dep+ap],[nx1,y+dep+ap]],{w:2.4,amp:0.5,taper:0},tg);
  ink([[nx0,y+dep],[nx0,y+dep+ap]],{w:2,amp:0.2},tg);ink([[nx1,y+dep],[nx1,y+dep+ap]],{w:2,amp:0.2},tg);
  hatch(dstr(rect(nx0,y+dep,nx1-nx0,ap),true),{ang:0,gap:3.2,w:0.8,dens:()=>0.55},tg);
  for(let i=0;i<7;i++){const t=(i+0.5)/7;const x0=o.x0+(o.x1-o.x0)*t,x1=nx0+(nx1-nx0)*t;stroke([[x0,y+2],[x1,y+dep-2]],{w:0.6,amp:2.0},tg);}
  // mørket under bordet: tett rett under platen, tynnere mot gulvet
  const under=[[nx0,y+dep+ap],[nx1,y+dep+ap],[nx1+30,H],[nx0-30,H]];
  hatch(shape(under),{ang:0,gap:4,w:0.9,amp:1.2,dens:(x,yy)=>clamp(0.7-(yy-y-dep-ap)/(260*s/1.35))*(0.5+0.5*s/1.35)},tg);
  hatch(shape(under),{ang:60,gap:5,w:0.8,amp:1.0,dens:(x,yy)=>clamp(0.45-(yy-y-dep-ap)/(200*s/1.35))*(0.4+0.6*s/1.35)},tg);
  for(const bx of [nx0+50,nx1-74]){const d=bx<(nx0+nx1)/2?1:-1;ink([[bx,y+dep+ap],[bx-6*d,H]],{w:4,amp:0.4,taper:0},tg);ink([[bx+20,y+dep+ap],[bx+20-6*d,H]],{w:2.2,amp:0.4,taper:0},tg);hatch(dstr(rect(bx-2,y+dep+ap,24,H-y-dep-ap),true),{ang:85,gap:3,w:0.8,dens:()=>0.5},tg);}
  if(o.props)o.props(tg);
  return {jon,geir,tg,front,back};
}

/* =====================================================================
   VIEW 1: KAFEEN, TOTALBILDE
   ===================================================================== */
function drawKafe(){
  srand(101);
  const W=1920,H=1080;
  const bg=G(root,{class:'rom'});
  const wallBot=660;
  const lampX=960,lampY=230;
  // --- bakvegg: liggende panel. Papiret er lyset. Skravur bare i de øvre hjørnene.
  for(let y=96;y<wallBot;y+=64)ink([[0,y],[W,y+R(-1,1)]],{w:1.1,amp:0.6,taper:0},bg);
  ink([[0,96],[W,96]],{w:2.0,amp:0.4,taper:0},bg);
  hatch(dstr(rect(0,0,W,96),true),{ang:0,gap:4.5,w:0.9,dens:(x,y)=>clamp(0.8-y/110)},bg);
  const wallD=dstr(rect(0,96,W,wallBot-96),true);
  const wallTone=(x,y)=>{const d=Math.hypot((x-lampX)/980,(y-lampY-300)/640);return clamp(d*d*0.8-0.72);};
  hatch(wallD,{ang:40,gap:7,w:0.8,amp:0.7,dens:wallTone},bg);
  hatch(wallD,{ang:130,gap:8,w:0.7,amp:0.7,dens:(x,y)=>clamp(wallTone(x,y)-0.3)*1.2},bg);
  // gulvlist
  ink([[0,wallBot],[W,wallBot]],{w:3,amp:0.4,taper:0},bg);
  stroke([[0,wallBot+12],[W,wallBot+12]],{w:1.2,amp:0.4},bg);
  hatch(dstr(rect(0,wallBot,W,12),true),{ang:80,gap:3,w:0.7,dens:()=>0.5},bg);
  // --- gulv: planker i perspektiv. Hvitt, mørkere bare i de nedre hjørnene.
  const floorD=dstr(rect(0,wallBot+12,W,H-wallBot-12),true);
  const vx=960,vy=180;
  for(let i=-16;i<=16;i++){
    const xb=960+i*150, xt=vx+(xb-vx)*((wallBot+12-vy)/(H-vy));
    ink([[xt,wallBot+12],[xb,H]],{w:1.0,amp:0.5,taper:0},bg);
  }
  hatch(floorD,{ang:0,gap:8,w:0.8,amp:1.2,dens:(x,y)=>clamp(Math.abs(x-960)/960-0.62)*1.6*clamp((y-700)/300)},bg);

  // --- vindu bak, mellom de to. Utsikt: snøfonn, fjell, kveldshimmel
  const wx=700,wy=150,ww=520,wh=380;
  const glassScene=viewScene(wx,wy,ww,wh,1);
  const trim=26;
  white(rect(wx-trim,wy-trim,ww+2*trim,wh+trim+40),{},bg);
  ink(rect(wx-trim,wy-trim,ww+2*trim,wh+2*trim),{closed:true,taper:0,w:2.6,amp:0.4},bg);
  hatch(dstr(rect(wx-trim,wy-trim,ww+2*trim,wh+2*trim),true),{ang:90,gap:5,w:0.7,dens:()=>0.15},bg);
  window2(bg,wx,wy,ww,wh,{frame:14,mid:10,glass:glassScene});
  white(rect(wx-trim-6,wy+wh+trim-8,ww+2*trim+12,18),{},bg);
  ink(rect(wx-trim-6,wy+wh+trim-8,ww+2*trim+12,18),{closed:true,taper:0,w:2,amp:0.3},bg);
  hatch(dstr(rect(wx-trim-6,wy+wh+trim+2,ww+2*trim+12,8),true),{ang:0,gap:2.4,w:0.7},bg);
  const lk=wx+ww-70,lky=wy+wh+trim-8;
  white(rect(lk-14,lky-42,28,42),{},bg);ink(rect(lk-14,lky-42,28,42),{closed:true,taper:0,w:1.6,amp:0.3},bg);
  ink([[lk-16,lky-42],[lk,lky-52],[lk+16,lky-42]],{w:1.6,amp:0.2},bg);
  hatch(dstr(rect(lk-12,lky-40,24,38),true),{ang:60,gap:2.4,w:0.7,dens:(x,y)=>0.55},bg);
  E('ellipse',{cx:lk,cy:lky-20,rx:6,ry:9,fill:'#fff'},bg);
  const rx=wx+60,ry=wy+wh+trim+20,rw=ww-120,rh=48;
  ink(rect(rx,ry,rw,rh),{closed:true,taper:0,w:1.6,amp:0.4},bg);
  for(let x=rx+12;x<rx+rw-6;x+=16)stroke([[x,ry+5],[x,ry+rh-5]],{w:0.9,amp:0.3},bg);

  // --- veggting: hylle med kopper (venstre), bilde, tavle (høyre), klokke
  const sx=110,sy=250,sw=380;
  ink([[sx,sy],[sx+sw,sy]],{w:3,amp:0.4,taper:0},bg);
  stroke([[sx,sy+8],[sx+sw,sy+8]],{w:1.2,amp:0.4},bg);
  hatch(dstr(rect(sx,sy,sw,8),true),{ang:0,gap:2.4,w:0.7,dens:()=>0.7},bg);
  ink([[sx+30,sy+8],[sx+50,sy+50]],{w:1.6,amp:0.2},bg);ink([[sx+sw-30,sy+8],[sx+sw-50,sy+50]],{w:1.6,amp:0.2},bg);
  for(let i=0;i<6;i++){const cx=sx+40+i*58,cy=sy-4;
    white([[cx-16,cy-28],[cx+16,cy-28],[cx+15,cy],[cx-15,cy]],{},bg);
    ink([[cx-16,cy-28],[cx-15,cy]],{w:1.3,amp:0.3},bg);ink([[cx+16,cy-28],[cx+15,cy]],{w:1.3,amp:0.3},bg);
    ink(ellipsePts(cx,cy-28,16,4,14),{curve:true,closed:true,taper:0,w:1.2,amp:0.2},bg);
    stroke(ellipsePts(cx,cy,15,3.5,14,0,Math.PI),{curve:true,w:1.0,amp:0.2},bg);
    stroke([[cx+16,cy-20],[cx+26,cy-18],[cx+24,cy-8],[cx+15,cy-6]],{curve:true,w:1.2,amp:0.2},bg);
    hatch(shape([[cx-15,cy-26],[cx-5,cy-26],[cx-5,cy-1],[cx-14,cy-1]]),{ang:80,gap:2.5,w:0.7,dens:()=>0.5},bg);
  }
  hatch(dstr(rect(sx,sy+8,sw,30),true),{ang:0,gap:3.5,w:0.7,dens:(x,y)=>clamp(0.6-(y-sy-8)/30)},bg);
  const px=250,py=360,pw=220,ph=160;
  white(rect(px-8,py-8,pw+16,ph+16),{},bg);
  ink(rect(px-8,py-8,pw+16,ph+16),{closed:true,taper:0,w:2.6,amp:0.3},bg);
  ink(rect(px,py,pw,ph),{closed:true,taper:0,w:1.2,amp:0.3},bg);
  cross(dstr(rect(px,py,pw,ph),true),{ang:30,gap:3.2,w:0.8,dens:(x,y)=>clamp(0.15+(py+40-y)/60)},bg);
  const hp=[[px+40,py+118],[px+40,py+72],[px+95,py+36],[px+150,py+72],[px+150,py+118]];
  white(hp,{},bg);ink(hp,{closed:true,taper:0,w:1.2,amp:0.3},bg);
  for(let x=px+46;x<px+148;x+=5)stroke([[x,py+74],[x,py+116]],{w:0.5,amp:0.2},bg);
  hatch(shape([[px+40,py+72],[px+95,py+36],[px+150,py+72]]),{ang:0,gap:2.5,w:0.6,dens:()=>0.5},bg);
  hatch(dstr(rect(px,py+118,pw,ph-118),true),{ang:0,gap:3,w:0.7,dens:()=>0.25},bg);
  const tx=1440,ty=170,tw=260,th=180;
  white(rect(tx-10,ty-10,tw+20,th+20),{},bg);
  ink(rect(tx-10,ty-10,tw+20,th+20),{closed:true,taper:0,w:3,amp:0.4},bg);
  cross(dstr(rect(tx,ty,tw,th),true),{ang:35,gap:2.4,w:1.1,amp:0.5,dens:()=>0.95},bg);
  const ff="'Chalkduster','Bradley Hand','Marker Felt','Comic Sans MS',cursive";
  const t1=E('text',{x:tx+tw/2,y:ty+72,'text-anchor':'middle','font-family':ff,'font-size':46,fill:'#fff'},bg);t1.textContent='Torsdag';
  const t2=E('text',{x:tx+tw/2,y:ty+140,'text-anchor':'middle','font-family':ff,'font-size':48,fill:'#fff'},bg);t2.textContent='komle';
  const kx=1620,ky=470,kr=38;
  white(ellipsePts(kx,ky,kr,kr,30),{curve:true},bg);
  ink(ellipsePts(kx,ky,kr,kr,30),{curve:true,closed:true,taper:0,w:2.4,amp:0.3},bg);
  for(let i=0;i<12;i++){const a=i/12*6.283;stroke([[kx+Math.cos(a)*kr*0.82,ky+Math.sin(a)*kr*0.82],[kx+Math.cos(a)*kr*0.92,ky+Math.sin(a)*kr*0.92]],{w:1.2},bg);}
  ink([[kx,ky],[kx+Math.cos(-1.05)*kr*0.5,ky+Math.sin(-1.05)*kr*0.5]],{w:2.2,amp:0.1,taper:0.4},bg);
  ink([[kx,ky],[kx+Math.cos(1.57)*kr*0.75,ky+Math.sin(1.57)*kr*0.75]],{w:1.6,amp:0.1,taper:0.4},bg);
  // disk i bakgrunnen, høyre: en mørk masse i hjørnet
  const dx=1560,dy=580;
  white(rect(dx,dy,W-dx,H-dy),{},bg);
  ink([[dx,dy],[dx,H]],{w:2.6,amp:0.4,taper:0},bg);
  ink([[dx-22,dy-8],[W,dy-8]],{w:3,amp:0.4,taper:0},bg);
  ink([[dx-22,dy-8],[dx-22,dy+6],[dx,dy+6]],{w:1.6,amp:0.2},bg);
  for(let y=dy+44;y<H;y+=44)stroke([[dx+8,y],[W,y]],{w:1.0,amp:0.5},bg);
  hatch(dstr(rect(dx,dy,W-dx,H-dy),true),{ang:70,gap:6,w:0.8,dens:(x,y)=>clamp((y-dy)/600)*0.8},bg);
  const cx=1680,cy=dy-8;
  white(rect(cx-30,cy-95,60,95),{},bg);ink(rect(cx-30,cy-95,60,95),{closed:true,taper:0,w:1.8,amp:0.3},bg);
  ink([[cx-22,cy-40],[cx+22,cy-40]],{w:1.2,amp:0.2},bg);
  white(rect(cx-18,cy-38,36,36),{},bg);ink([[cx-18,cy-2],[cx-16,cy-36],[cx+16,cy-36],[cx+18,cy-2]],{curve:true,w:1.4,amp:0.2},bg);
  hatch(dstr(rect(cx-30,cy-95,60,52),true),{ang:80,gap:3,w:0.8,dens:()=>0.6},bg);
  white(rect(cx+60,cy-70,34,70),{},bg);ink(rect(cx+60,cy-70,34,70),{closed:true,taper:0,w:1.6,amp:0.3},bg);
  ink(ellipsePts(cx+77,cy-70,17,4,14),{curve:true,closed:true,taper:0,w:1.2},bg);
  hatch(dstr(rect(cx+60,cy-70,34,70),true),{ang:85,gap:2.6,w:0.7,dens:(x,y)=>clamp(0.2+(x-cx-77)/20)},bg);

  // --- pendellampe over bordet
  const lg=G(root,{class:'lampe'});
  ink([[lampX,0],[lampX+1,lampY-40]],{w:1.4,amp:0.3,taper:0},lg);
  const shade=[[lampX-7,lampY-40],[lampX+7,lampY-40],[lampX+62,lampY+24],[lampX-62,lampY+24]];
  white(shade,{},lg);
  ink([[lampX-7,lampY-40],[lampX-62,lampY+24]],{w:2.4,amp:0.3,taper:0.3},lg);
  ink([[lampX+7,lampY-40],[lampX+62,lampY+24]],{w:2.4,amp:0.3,taper:0.3},lg);
  ink([[lampX-7,lampY-40],[lampX+7,lampY-40]],{w:2,amp:0.2},lg);
  hatch(shape(shade),{ang:100,gap:3.2,w:0.9,dens:(x,y)=>clamp(0.3+(x-lampX)/100)},lg);
  ink(ellipsePts(lampX,lampY+24,62,11,30),{curve:true,closed:true,taper:0,w:2.2,amp:0.3},lg);
  E('ellipse',{cx:lampX,cy:lampY+22,rx:16,ry:6,fill:'#fff'},lg);
  stroke(ellipsePts(lampX,lampY+22,16,6,16),{curve:true,closed:true,w:1.0,amp:0.2},lg);

  // --- bordet med de to. Jon lener seg inn og snakker, Geir sitter tilbake med glasset og hører.
  const tableY=700, s=1.35;
  tableScene(root,{y:tableY,x0:610,x1:1310,nx0:400,nx1:1520,dep:170,s,
    jon:{lean:12,headTilt:-5,mouth:'C',brow:-0.1,eyeOpen:0.85,detail:0.5,
      nearArm:{sh:-14,el:-90,hand:2,grip:'fist'},farArm:{sh:-44,el:-62,hand:-6,grip:'fork'}},
    geir:{lean:-6,headTilt:5,mouth:'X',brow:0.7,eyeOpen:1,detail:0.5,
      nearArm:{sh:-10,el:-74,hand:0,grip:'glass',glassH:74},farArm:{sh:4,el:-6,hidden:true}},
    props:(tg)=>{
      plateKomle(tg,900,tableY+34,86);
      plateKomle(tg,1090,tableY+30,86);
      knife(tg,1160,tableY+92,-20);
      coffeeCup(tg,830,tableY+86,20);
      candle(tg,1000,tableY+52,36);
      saltPepper(tg,985,tableY+118);
      const av=[[430,tableY+130],[600,tableY+108],[620,tableY+150],[450,tableY+160]];
      white(av,{},tg);ink(av,{closed:true,taper:0,w:1.4,amp:0.4},tg);
      for(let i=1;i<6;i++)stroke([[442+i*2,tableY+134+i*4],[610-i*2,tableY+114+i*5]],{w:0.8,amp:0.3},tg);
      hatch(shape([[446,tableY+136],[520,tableY+126],[526,tableY+138],[452,tableY+148]]),{ang:0,gap:2,w:0.8},tg);
    }});

  // --- vignett: bare de ytterste hjørnene
  hatch(dstr(rect(0,0,W,H),true),{ang:40,gap:5,w:0.9,amp:1.2,dens:(x,y)=>clamp(Math.hypot((x-960)/1150,(y-540)/760)**3-0.62)*1.4},root);
}

/* =====================================================================
   VIEW 5: MUNNFORMENE. Rhubarb-bokstavene, i nærbilde (trekvart, s=5,4)
   og i totalskala (profil, s=1,35). Hver form må leses på én frame.
   ===================================================================== */
const MOUTH_GLOSS={X:'hvile',A:'M B P',B:'konsonant',C:'E',D:'A',E:'O',F:'U W',G:'F V'};
function drawMunn(){
  srand(301);
  const letters=['X','A','B','C','D','E','F','G'];
  const fontS="Helvetica Neue,Helvetica,Arial,sans-serif";
  const col=i=>150+i*220, cw=210;
  const rows=[
    {ch:JON,mode:'34',y:56,h:250,label:'Jon, nærbilde 5,4'},
    {ch:JON,mode:'pr',y:322,h:160,label:'Jon, totalbilde 1,35'},
    {ch:GEIR,mode:'34',y:508,h:250,label:'Geir, nærbilde 5,4'},
    {ch:GEIR,mode:'pr',y:774,h:160,label:'Geir, totalbilde 1,35'},
  ];
  for(let i=0;i<8;i++){
    const t=E('text',{x:col(i)+cw/2,y:34,'text-anchor':'middle','font-family':fontS,'font-size':26,'font-weight':'bold',fill:'#000'},root);t.textContent=letters[i];
    const t2=E('text',{x:col(i)+cw/2,y:52,'text-anchor':'middle','font-family':fontS,'font-size':13,fill:'#000'},root);t2.textContent=MOUTH_GLOSS[letters[i]];
  }
  for(const r of rows){
    const lab=E('text',{x:16,y:r.y+r.h/2,'font-family':fontS,'font-size':14,fill:'#000'},root);lab.textContent=r.label;
    for(let i=0;i<8;i++){
      const x=col(i);
      const cell=clipG(dstr(rect(x,r.y,cw,r.h),true),root);
      const pose={mouth:letters[i],seed:11+i,brow:r.ch===GEIR?0.3:-0.1,eyeOpen:0.9};
      if(r.mode==='34'){
        const s=5.4, mx=x+cw/2-10*s, my=r.y+r.h*0.5-81*s;
        const oldU=U;U=1/s;srand(pose.seed);
        const g=G(cell,{transform:`translate(${mx} ${my}) scale(${s})`});
        head34(g,r.ch,pose);
        U=oldU;
      } else {
        const s=1.35, ox=x+cw/2-14*s, oy=r.y+16;
        const oldU=U;U=1/s;srand(pose.seed);
        const g=G(cell,{transform:`translate(${ox} ${oy}) scale(${s})`});
        pose.detail=0.5;
        // litt hals under, så hodet ikke svever
        white([[-46,96],[12,96],[14,140],[-46,140]],{},g);
        ink([[4,101],[7,120],[10,138]],{curve:true,w:1.8,amp:0.3},g);
        ink([[-42,72],[-45,100],[-46,138]],{curve:true,w:2.0,amp:0.3},g);
        headProfile(g,r.ch,pose);
        U=oldU;
      }
      stroke(rect(x,r.y,cw,r.h),{closed:true,w:0.8,amp:0},root);
    }
  }
}

/* =====================================================================
   VIEW 6: POSITURER. De to i fire sittestillinger. Beviset på at riggen beveger seg.
   ===================================================================== */
function drawPositur(){
  srand(401);
  const fontS="Helvetica Neue,Helvetica,Arial,sans-serif";
  const cells=[
    {label:'Lener seg inn, snakker',
     jon:{lean:14,headTilt:-6,mouth:'C',brow:-0.2,nearArm:{sh:-24,el:-80,hand:2,grip:'fist'},farArm:{sh:-40,el:-66,hand:-4,grip:'rest'}},
     geir:{lean:14,headTilt:-6,mouth:'D',brow:0.4,nearArm:{sh:-24,el:-80,hand:2,grip:'rest'},farArm:{sh:-40,el:-66,hand:-4,grip:'fist'}}},
    {label:'Sitter tilbake, lytter',
     jon:{lean:-10,headTilt:6,mouth:'X',brow:0.3,nearArm:{sh:-6,el:-74,hand:0,grip:'fist'},farArm:{sh:4,el:-6,hidden:true}},
     geir:{lean:-10,headTilt:6,mouth:'X',brow:0.6,nearArm:{sh:-6,el:-74,hand:0,grip:'glass'},farArm:{sh:4,el:-6,hidden:true}}},
    {label:'Løfter glasset',
     jon:{lean:4,headTilt:-2,mouth:'X',brow:0,nearArm:{sh:-30,el:-125,hand:65,grip:'glass'},farArm:{sh:-30,el:-64,hand:0,grip:'rest'}},
     geir:{lean:4,headTilt:-2,mouth:'B',brow:0.2,nearArm:{sh:-30,el:-125,hand:65,grip:'glass'},farArm:{sh:-30,el:-64,hand:0,grip:'rest'}}},
    {label:'Setter glasset ned',
     jon:{lean:6,headTilt:0,mouth:'B',brow:-0.1,nearArm:{sh:-36,el:-60,hand:6,grip:'glass'},farArm:{sh:-32,el:-64,hand:0,grip:'rest'}},
     geir:{lean:6,headTilt:0,mouth:'A',brow:0.3,nearArm:{sh:-36,el:-60,hand:6,grip:'glass'},farArm:{sh:-32,el:-64,hand:0,grip:'rest'}}},
  ];
  const s=0.85;
  cells.forEach((c,i)=>{
    const cx=(i%2)*960, cy=Math.floor(i/2)*540;
    const cell=clipG(dstr(rect(cx,cy,960,540),true),root);
    // gulvlinje, så beina står på noe
    ink([[cx,cy+240+44+80*s+200*s],[cx+960,cy+240+44+80*s+200*s]],{w:1.4,amp:0.6,taper:0},cell);
    tableScene(cell,{y:cy+240,x0:cx+330,x1:cx+630,nx0:cx+270,nx1:cx+690,dep:84,s,jon:c.jon,geir:c.geir,
      props:(tg)=>{coffeeCup(tg,cx+400,cy+290,14);candle(tg,cx+480,cy+272,26);}});
    const t=E('text',{x:cx+28,y:cy+44,'font-family':fontS,'font-size':24,fill:'#000'},root);t.textContent=(i+1)+'. '+c.label;
    stroke(rect(cx+1,cy+1,958,538),{closed:true,w:0.8,amp:0},root);
  });
}

/* =====================================================================
   VIEW 2 og 3: NÆRBILDER
   ===================================================================== */
function drawNær(ch,pose){
  srand(pose.seed);
  const W=1920,H=1080;
  const bg=G(root,{class:'bak'});
  // veggpanel bak, ute av fokus: bordlinjene, og skravur bare i de ytre hjørnene
  for(let y=40;y<H;y+=118){ink([[0,y],[W,y+R(-2,2)]],{w:1.4,amp:1.0,taper:0},bg);stroke([[0,y+7],[W,y+7]],{w:0.6,amp:0.6},bg);}
  const tone=(x,y)=>clamp(Math.hypot((x-pose.lx)/1250,(y-pose.ly)/950)**2*1.0-0.45);
  hatch(dstr(rect(0,0,W,H),true),{ang:40,gap:7,w:0.9,amp:1.0,dens:tone},bg);
  hatch(dstr(rect(0,0,W,H),true),{ang:130,gap:8,w:0.8,amp:1.0,dens:(x,y)=>clamp(tone(x,y)-0.3)*1.3},bg);
  if(pose.window){
    const [wx,wy,ww,wh]=pose.window;
    const trim=30;
    white(rect(wx-trim,wy-trim,ww+2*trim,wh+2*trim),{},bg);
    ink(rect(wx-trim,wy-trim,ww+2*trim,wh+2*trim),{closed:true,taper:0,w:3.0,amp:0.4},bg);
    hatch(dstr(rect(wx-trim,wy-trim,ww+2*trim,wh+2*trim),true),{ang:90,gap:5,w:0.7,dens:()=>0.2},bg);
    window2(bg,wx,wy,ww,wh,{frame:16,mid:12,glass:viewScene(wx,wy,ww,wh,0.85)});
  }
  const f=figure34(ch,pose,root,pose.s);
  hatch(dstr(rect(0,0,W,H),true),{ang:40,gap:5,w:0.9,amp:1.2,dens:(x,y)=>clamp(Math.hypot((x-960)/1150,(y-540)/760)**3-0.4)*1.2},root);
  return f;
}
function drawJon(){
  drawNær(JON,{x:880,y:170,s:5.4,seed:71,mouth:'B',brow:-0.15,eyeOpen:0.85,headTilt:2,lx:500,ly:-100,window:[1230,90,540,640]});
}
function drawGeir(){
  drawNær(GEIR,{x:1040,y:170,s:5.4,seed:83,mouth:'C',brow:0.9,eyeOpen:0.9,headTilt:-3,flip:true,lx:1400,ly:-100,window:[150,90,540,640]});
}

/* =====================================================================
   VIEW 4: HUSET. Fargeriet fra gata i snø, kveld. Ekte perspektiv i meter.
   ===================================================================== */
function drawHus(){
  srand(211);
  const W=1920,H=1080;
  const eye=[-6.0,1.7,12.0], tgt=[4.6,3.3,-1.0], f=1750;
  const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const crs=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const nrm=a=>{const l=Math.hypot(...a);return [a[0]/l,a[1]/l,a[2]/l];};
  const fw=nrm(sub(tgt,eye)),rt=nrm(crs(fw,[0,1,0])),upv=crs(rt,fw);
  const P=(x,y,z)=>{const d=sub([x,y,z],eye);const X=dot(d,rt),Y=dot(d,upv),Z=dot(d,fw);return [960+f*X/Z,600-f*Y/Z];};
  const PP=pts=>pts.map(p=>P(...p));
  const L=11,D=8,hw=4.2,pitch=38*Math.PI/180,ridge=hw+(D/2)*Math.tan(pitch),ov=0.55,gov=0.45,snowT=0.42;

  const bg=G(root,{class:'bak'});
  // --- himmel: skravur i én retning, tettest øverst. Ingen kryss nederst.
  const skyD=dstr(rect(0,0,W,720),true);
  hatch(skyD,{ang:28,gap:3.6,w:1.1,amp:0.7,dens:(x,y)=>clamp(0.95-y/750)},bg);
  hatch(skyD,{ang:72,gap:4.2,w:0.9,amp:0.7,dens:(x,y)=>clamp(0.7-y/380)},bg);
  // --- fjell: hvit snø, ryggen som strek, litt berg
  const ridgeLine=[[-10,520],[160,440],[340,470],[520,360],[700,410],[880,330],[1060,380],[1250,310],[1440,360],[1650,290],[1850,350],[1930,330]];
  const mount=ridgeLine.concat([[1930,760],[-10,760]]);
  white(mount,{curve:true},bg);
  ink(ridgeLine,{curve:true,w:1.8,amp:1.2,taper:0},bg);
  strokesIn(shape(mount,{curve:true}),{n:260,len:26,w:1.3,angf:(x,y)=>-56+R(-8,8),dens:(x,y)=>clamp((y-380)/220)*0.45*clamp(1-(y-520)/120)},bg);
  hatch(shape(mount,{curve:true}),{ang:-60,gap:6,w:0.8,amp:1.0,dens:(x,y)=>clamp((y-330)/350)*0.35},bg);
  // granskog i foten av fjellet: enkelttrær
  function spruce(g,x,y,h){
    const w=h*0.36,tiers=6,pts=[[x,y-h]];
    for(let i=1;i<=tiers;i++){const t=i/tiers,yy=y-h+h*t*0.95,ww=w*t;pts.push([x+ww*0.35,yy-h*0.06],[x+ww,yy]);}
    pts.push([x+w*0.12,y]);pts.push([x-w*0.12,y]);
    for(let i=tiers;i>=1;i--){const t=i/tiers,yy=y-h+h*t*0.95,ww=w*t;pts.push([x-ww,yy],[x-ww*0.35,yy-h*0.06]);}
    black(pts,{},g);
    for(let i=1;i<=tiers;i++){const t=i/tiers,yy=y-h+h*t*0.95,ww=w*t;stroke([[x-ww*0.85,yy-1.5],[x,yy-h*0.06-1.5],[x+ww*0.85,yy-1.5]],{curve:true,w:2.2,amp:0.4,col:'#fff'},g);}
  }
  for(let x=-30;x<1960;x+=R(22,40)){const h=R(60,120);spruce(bg,x,690+R(-10,14),h);}
  // --- bakken: hvitt papir
  white(rect(0,700,W,400),{},bg);

  // --- huset
  const hg=G(root,{class:'hus'});
  const gable=[[0,0.0,0],[0,hw,0],[0,ridge,-D/2],[0,hw,-D],[0,0,-D]];
  white(PP(gable),{},hg);
  const fac=[[0,0,0],[L,0,0],[L,hw,0],[0,hw,0]];
  white(PP(fac),{},hg);
  // stående panel (tømmermannspanel): underligger bred, overligger smal med skyggestrek
  for(let x=0.06;x<L;x+=0.125){
    const a=P(x,0.6,0),b=P(x,hw-0.1,0);
    const k=Math.round(x/0.125)%2;
    if(k===0)ink([a,b],{w:1.3,amp:0.25,taper:0},hg);else stroke([a,b],{w:0.55,amp:0.2},hg);
  }
  for(let z=-0.06;z>-D;z-=0.125){
    const yTop=(z>-D/2)?hw+(-z)*Math.tan(pitch):hw+(D+z)*Math.tan(pitch);
    const a=P(0,0.6,z),b=P(0,yTop-0.1,z);
    const k=Math.round(-z/0.125)%2;
    if(k===0)ink([a,b],{w:1.2,amp:0.25,taper:0},hg);else stroke([a,b],{w:0.5,amp:0.2},hg);
  }
  const lamp3=[3.4,2.3,0.3];const lampS=P(...lamp3);
  const winLit=[1.6,5.6,9.7].map(x=>P(x,1.65,0));
  const facTone=(x,y)=>{let l=clamp(1-Math.hypot(x-lampS[0],(y-lampS[1])*0.7)/380);for(const w of winLit)l=Math.max(l,clamp(1-Math.hypot(x-w[0],y-w[1])/240)*0.8);return clamp(0.38-l*0.5);};
  hatch(dstr(PP(fac),true),{ang:88,gap:6,w:0.7,amp:0.5,dens:facTone},hg);
  cross(dstr(PP(gable),true),{ang:88,gap:4.2,w:0.9,amp:0.5,dens:()=>0.6},hg);
  ink([P(0,0.55,0),P(0,hw,0)],{w:3.2,amp:0.3,taper:0},hg);
  ink([P(0.12,0.55,0),P(0.12,hw,0)],{w:1.4,amp:0.3,taper:0},hg);
  ink([P(L,0.55,0),P(L,hw,0)],{w:3,amp:0.3,taper:0},hg);
  ink([P(0,0.55,-D),P(0,hw,-D)],{w:2.2,amp:0.3,taper:0},hg);
  ink([P(0,0.6,0),P(L,0.6,0)],{w:2.2,amp:0.4,taper:0},hg);
  ink([P(0,0.6,0),P(0,0.6,-D)],{w:2.0,amp:0.4,taper:0},hg);

  function win3(x0,y0,w,h,zp,lit,vertical){
    const T=0.11;
    const pt=(u,v,dz)=>vertical?P(0+(dz||0),v,u):P(u,v,zp+(dz||0));
    const q=[pt(x0-T,y0-T),pt(x0+w+T,y0-T),pt(x0+w+T,y0+h+T),pt(x0-T,y0+h+T)];
    white(q,{},hg);ink(q,{closed:true,taper:0,w:2.2,amp:0.3},hg);
    const qi=[pt(x0,y0),pt(x0+w,y0),pt(x0+w,y0+h),pt(x0,y0+h)];
    ink(qi,{closed:true,taper:0,w:1.6,amp:0.2},hg);
    black([pt(x0-T-0.03,y0+h+T),pt(x0+w+T+0.03,y0+h+T),pt(x0+w+T+0.03,y0+h+T+0.06),pt(x0-T-0.03,y0+h+T+0.06)],{},hg);
    hatch(dstr([pt(x0-T-0.03,y0-T-0.05),pt(x0+w+T+0.03,y0-T-0.05),pt(x0+w+T+0.03,y0-T),pt(x0-T-0.03,y0-T)],true),{ang:0,gap:1.6,w:0.7},hg);
    const sn=[pt(x0-T-0.05,y0-T),pt(x0-T,y0-T+0.08),pt(x0+w/2,y0-T+0.11),pt(x0+w+T,y0-T+0.07),pt(x0+w+T+0.05,y0-T)];
    white(sn,{curve:true},hg);stroke(sn,{curve:true,w:1.0,amp:0.5},hg);
    const mid=0.06;
    black([pt(x0+w/2-mid/2,y0),pt(x0+w/2+mid/2,y0),pt(x0+w/2+mid/2,y0+h),pt(x0+w/2-mid/2,y0+h)],{},hg);
    for(let s=0;s<2;s++){
      const sx0=x0+s*(w/2+mid/2), sw=w/2-mid/2, fr=0.04;
      const glassQ=[pt(sx0+fr,y0+fr),pt(sx0+sw-fr,y0+fr),pt(sx0+sw-fr,y0+h-fr),pt(sx0+fr,y0+h-fr)];
      ink(glassQ,{closed:true,taper:0,w:1.3,amp:0.15},hg);
      const cw=(sw-2*fr)/2,chh=(h-2*fr)/3;
      if(!lit){
        cross(dstr(glassQ,true),{ang:40,gap:2.4,w:0.9,dens:()=>0.8},hg);
        white([pt(sx0+fr+cw*0.3,y0+h-fr),pt(sx0+fr+cw*0.55,y0+h-fr),pt(sx0+fr+cw*1.6,y0+fr),pt(sx0+fr+cw*1.35,y0+fr)],{},hg);
      } else {
        // lyst rom: gardinkappe øverst og en liten lampe i vinduet
        hatch(dstr([pt(sx0+fr,y0+h-fr-0.22),pt(sx0+sw-fr,y0+h-fr-0.22),pt(sx0+sw-fr,y0+h-fr),pt(sx0+fr,y0+h-fr)],true),{ang:90,gap:2.2,w:0.8,dens:()=>0.5},hg);
        stroke([pt(sx0+fr,y0+h-fr-0.22),pt(sx0+sw-fr,y0+h-fr-0.23)],{w:1.2,amp:0.4},hg);
        if(s===1){const lx=sx0+sw/2;ink([pt(lx,y0+0.05),pt(lx,y0+0.3)],{w:1.6,amp:0.1},hg);black([pt(lx-0.1,y0+0.3),pt(lx+0.1,y0+0.3),pt(lx+0.06,y0+0.42),pt(lx-0.06,y0+0.42)],{},hg);}
        stipple(dstr(glassQ,true),{n:40,r:0.6,dens:()=>0.35},hg);
      }
      ink([pt(sx0+fr+cw,y0+fr),pt(sx0+fr+cw,y0+h-fr)],{w:1.2,amp:0.1,taper:0.2},hg);
      for(let r=1;r<3;r++)ink([pt(sx0+fr,y0+fr+chh*r),pt(sx0+sw-fr,y0+fr+chh*r)],{w:1.2,amp:0.1,taper:0.2},hg);
    }
  }
  win3(1.0,0.95,1.2,1.4,0,true);
  win3(5.0,0.95,1.2,1.4,0,true);
  win3(7.0,0.95,1.2,1.4,0,false);
  win3(9.1,0.95,1.2,1.4,0,true);
  win3(-3.0,0.95,1.2,1.4,0,false,true);
  win3(-6.2,0.95,1.2,1.4,0,true,true);
  win3(-4.5,4.7,1.0,1.1,0,false,true);

  // --- dør med bislag, lampe og skilt
  const dx=2.9,dw=1.0,dh=2.05,T=0.11;
  const dq=PP([[dx-T,0.6,0],[dx+dw+T,0.6,0],[dx+dw+T,dh+T,0],[dx-T,dh+T,0]]);
  white(dq,{},hg);ink(dq,{closed:true,taper:0,w:2.4,amp:0.3},hg);
  const dq2=PP([[dx,0.6,0],[dx+dw,0.6,0],[dx+dw,dh,0],[dx,dh,0]]);
  ink(dq2,{closed:true,taper:0,w:1.6,amp:0.2},hg);
  cross(dstr(dq2,true),{ang:88,gap:3.0,w:0.9,dens:()=>0.55},hg);
  for(const [y0,h0] of [[0.75,0.55],[1.4,0.45]]){const q=PP([[dx+0.15,y0,0],[dx+dw-0.15,y0,0],[dx+dw-0.15,y0+h0,0],[dx+0.15,y0+h0,0]]);white(q,{},hg);ink(q,{closed:true,taper:0,w:1.2,amp:0.2},hg);hatch(dstr(q,true),{ang:88,gap:3.4,w:0.8,dens:()=>0.3},hg);}
  E('circle',{cx:P(dx+0.85,1.1,0)[0],cy:P(dx+0.85,1.1,0)[1],r:3.2,fill:'#000'},hg);
  // trapp: ett trinn, snø på
  const st1=PP([[dx-0.4,0.6,0],[dx+dw+0.4,0.6,0],[dx+dw+0.4,0.6,0.9],[dx-0.4,0.6,0.9]]);
  white(st1,{},hg);ink(st1,{closed:true,taper:0,w:1.6,amp:0.6},hg);
  ink([P(dx-0.4,0.6,0.9),P(dx-0.4,0.35,0.9)],{w:1.6,amp:0.3},hg);ink([P(dx+dw+0.4,0.6,0.9),P(dx+dw+0.4,0.35,0.9)],{w:1.6,amp:0.3},hg);
  ink([P(dx-0.4,0.35,0.9),P(dx+dw+0.4,0.35,0.9)],{w:1.6,amp:0.4},hg);
  hatch(dstr(PP([[dx-0.4,0.35,0.9],[dx+dw+0.4,0.35,0.9],[dx+dw+0.4,0.6,0.9],[dx-0.4,0.6,0.9]]),true),{ang:0,gap:2,w:0.8},hg);
  // bislag: pulttak 1,2 m ut på to knekter
  const bz=0.9,by=2.5,bh=0.42;
  const roofQ=PP([[dx-0.6,by+bh,0],[dx+dw+0.6,by+bh,0],[dx+dw+0.6,by,bz],[dx-0.6,by,bz]]);
  const under=PP([[dx-0.6,by-0.06,bz],[dx+dw+0.6,by-0.06,bz],[dx+dw+0.6,by+bh-0.06,0],[dx-0.6,by+bh-0.06,0]]);
  white(roofQ,{},hg);white(under,{},hg);
  cross(dstr(under,true),{ang:0,gap:2.6,w:0.9,dens:()=>0.8},hg);
  ink(under,{closed:true,taper:0,w:1.4,amp:0.2},hg);
  const bsTop=PP([[dx-0.66,by+bh+0.3,0],[dx+dw+0.66,by+bh+0.3,0],[dx+dw+0.64,by+0.32,bz+0.12],[dx-0.64,by+0.32,bz+0.12]]);
  white(bsTop.concat([roofQ[2],roofQ[3]]),{},hg);
  ink([bsTop[3],bsTop[2]],{w:2.4,amp:1.2,taper:0},hg);
  ink([bsTop[3],roofQ[3]],{w:1.4,amp:0.6},hg);ink([bsTop[2],roofQ[2]],{w:1.4,amp:0.6},hg);
  ink([roofQ[3],roofQ[2]],{w:2.2,amp:0.3,taper:0},hg);
  ink([bsTop[0],bsTop[3]],{w:1.2,amp:0.6},hg);
  for(let i=0;i<9;i++){const t=i/8;const x=dx-0.55+t*(dw+1.1);const top=P(x,by-0.06,bz);const len=R(0.08,0.4);ink([top,P(x,by-0.06-len,bz)],{w:2.2,amp:0.2,taper:0.9},hg);}
  for(const x of [dx-0.45,dx+dw+0.45]){ink([P(x,by-0.02,bz-0.05),P(x,by-0.95,0)],{w:2.0,amp:0.2},hg);ink([P(x,by-0.02,bz-0.05),P(x,by+0.3,0)],{w:2.0,amp:0.2},hg);ink([P(x,by+0.3,0),P(x,by-0.95,0)],{w:2.0,amp:0.2},hg);}
  // lampe under bislaget: arm ut fra veggen, kjegleskjerm, lyset som hvit ellipse
  ink([P(dx+dw/2,2.35,0),P(dx+dw/2,2.35,0.32)],{w:2.4,amp:0.2},hg);
  const lsh=[P(dx+dw/2-0.06,2.36,0.30),P(dx+dw/2+0.06,2.36,0.30),P(dx+dw/2+0.24,2.14,0.30),P(dx+dw/2-0.24,2.14,0.30)];
  black(lsh,{},hg);
  E('ellipse',{cx:P(dx+dw/2,2.14,0.30)[0],cy:P(dx+dw/2,2.14,0.30)[1],rx:13,ry:4.5,fill:'#fff',stroke:'#000','stroke-width':1.2},hg);
  // skilt over bislaget
  const sq=PP([[dx-0.9,3.12,0.02],[dx+dw+0.9,3.12,0.02],[dx+dw+0.9,3.57,0.02],[dx-0.9,3.57,0.02]]);
  white(sq,{},hg);ink(sq,{closed:true,taper:0,w:2.2,amp:0.3},hg);
  ink([[sq[0][0]+4,sq[0][1]-4],[sq[1][0]-4,sq[1][1]-4],[sq[2][0]-4,sq[2][1]+4],[sq[3][0]+4,sq[3][1]+4]],{closed:true,taper:0,w:0.9,amp:0.2},hg);
  {
    const [a,b,c,d]=sq; // a,b = nederste hjørner; d,c = øverste
    const bw=dw+1.8,bhh=0.45;
    const m=[(c[0]-d[0])/bw,(c[1]-d[1])/bw,(a[0]-d[0])/bhh,(a[1]-d[1])/bhh,d[0],d[1]];
    const t=E('text',{x:bw/2,y:0.34,'text-anchor':'middle','font-family':"Georgia,'Times New Roman',serif",'font-size':0.3,'font-weight':'bold','letter-spacing':0.04,fill:'#000',transform:`matrix(${m.map(v=>v.toFixed(4)).join(' ')})`},hg);
    t.textContent='FARGERIET';
  }

  // --- tak
  const eaveZ=ov, ridgeZ=-D/2;
  const rq=PP([[-gov,hw,eaveZ],[L+gov,hw,eaveZ],[L+gov,ridge,ridgeZ],[-gov,ridge,ridgeZ]]);
  white(rq,{},hg);
  black(PP([[-gov,hw-0.02,eaveZ],[L+gov,hw-0.02,eaveZ],[L+gov,hw-0.02,0],[-gov,hw-0.02,0]]),{},hg);
  ink([P(-gov,hw-0.16,eaveZ),P(L+gov,hw-0.16,eaveZ)],{w:2.2,amp:0.3,taper:0},hg);
  ink([P(-gov,hw-0.05,eaveZ+0.08),P(L+gov,hw-0.05,eaveZ+0.08)],{w:3.2,amp:0.3,taper:0},hg);
  const snowQ=PP([[-gov-0.05,hw+snowT,eaveZ+0.1],[L+gov+0.05,hw+snowT,eaveZ+0.1],[L+gov+0.05,ridge+snowT,ridgeZ],[-gov-0.05,ridge+snowT,ridgeZ]]);
  white(snowQ,{},hg);
  const edge=[];for(let x=-gov-0.05;x<=L+gov+0.05;x+=0.25)edge.push(P(x,hw+snowT+R(-0.03,0.03),eaveZ+0.1+R(0,0.05)));
  ink(edge,{curve:true,w:2.6,amp:1.0,taper:0},hg);
  const under2=[];for(let x=-gov-0.05;x<=L+gov+0.05;x+=0.25)under2.push(P(x,hw-0.02+R(-0.04,0.04),eaveZ+0.12));
  ink(under2,{curve:true,w:1.6,amp:1.2,taper:0},hg);
  hatch(dstr(edge.concat(under2.slice().reverse()),true),{ang:90,gap:3,w:0.8,dens:()=>0.5},hg);
  for(let x=-gov;x<=L+gov;x+=0.16){if(rnd()<0.5)continue;const top=P(x,hw-0.05,eaveZ+0.1);const len=R(0.1,0.55);ink([top,P(x,hw-0.05-len,eaveZ+0.1)],{w:2.4,amp:0.2,taper:0.9},hg);}
  hatch(dstr(snowQ,true),{ang:-30,gap:10,w:0.6,amp:1.5,dens:(x,y)=>clamp(0.05+(430-y)/300)*0.4},hg);
  // snøfangere: én rekke nær takfoten
  {const up=1.1;const y=hw+up*Math.sin(pitch)+snowT, z=eaveZ-up*Math.cos(pitch);
    ink([P(-gov+0.2,y+0.05,z),P(L+gov-0.2,y+0.05,z)],{w:2.0,amp:0.3,taper:0},hg);
    for(let x=0.2;x<=L;x+=0.9){ink([P(x,y-0.14,z),P(x,y+0.07,z)],{w:2.4,amp:0.1,taper:0},hg);}}
  const rl=PP([[-gov-0.05,ridge+snowT,ridgeZ],[L+gov+0.05,ridge+snowT,ridgeZ]]);
  ink(rl,{w:2.6,amp:0.8,taper:0},hg);
  const back=PP([[-gov-0.05,ridge+snowT,ridgeZ],[L+gov+0.05,ridge+snowT,ridgeZ],[L+gov+0.05,ridge+snowT+0.15,ridgeZ-0.3],[-gov-0.05,ridge+snowT+0.15,ridgeZ-0.3]]);
  white(back,{},hg);ink([back[3],back[2]],{w:1.6,amp:0.8,taper:0},hg);
  ink(PP([[-gov,hw-0.1,eaveZ],[-gov,ridge,ridgeZ],[-gov,hw-0.1,-D-ov]]),{w:3.2,amp:0.3,taper:0},hg);
  ink(PP([[-gov,hw-0.24,eaveZ],[-gov,ridge-0.14,ridgeZ],[-gov,hw-0.24,-D-ov]]),{w:1.4,amp:0.3,taper:0},hg);
  // pipe
  const cx0=7.2,cz=-D/2,cw=0.7,ch=1.1;
  const chim=PP([[cx0,ridge,cz+cw/2],[cx0+cw,ridge,cz+cw/2],[cx0+cw,ridge+ch,cz+cw/2],[cx0,ridge+ch,cz+cw/2]]);
  const chimS=PP([[cx0,ridge,cz-cw/2],[cx0,ridge+ch,cz-cw/2],[cx0,ridge+ch,cz+cw/2],[cx0,ridge,cz+cw/2]]);
  white(chim,{},hg);white(chimS,{},hg);
  ink(chim,{closed:true,taper:0,w:2,amp:0.3},hg);ink(chimS,{closed:true,taper:0,w:1.6,amp:0.3},hg);
  hatch(dstr(chim,true),{ang:0,gap:4,w:0.9,dens:()=>0.45},hg);cross(dstr(chimS,true),{ang:0,gap:3.5,w:0.9,dens:()=>0.7},hg);
  const cap=PP([[cx0-0.06,ridge+ch,cz-cw/2-0.06],[cx0+cw+0.06,ridge+ch,cz-cw/2-0.06],[cx0+cw+0.06,ridge+ch,cz+cw/2+0.06],[cx0-0.06,ridge+ch,cz+cw/2+0.06]]);
  const capTop=PP([[cx0-0.08,ridge+ch+0.25,cz-cw/2-0.08],[cx0+cw+0.08,ridge+ch+0.25,cz-cw/2-0.08],[cx0+cw+0.08,ridge+ch+0.25,cz+cw/2+0.08],[cx0-0.08,ridge+ch+0.25,cz+cw/2+0.08]]);
  white(capTop.concat([cap[2],cap[3]]),{},hg);
  ink([cap[3],cap[2],capTop[2],capTop[3],cap[3]],{curve:true,w:1.8,amp:0.8,taper:0},hg);
  stipple(shape([[chim[2][0]-10,chim[2][1]-40],[chim[2][0]+40,chim[2][1]-120],[chim[2][0]+60,chim[2][1]-200],[chim[2][0]+120,chim[2][1]-230],[chim[2][0]+80,chim[2][1]-150],[chim[2][0]+50,chim[2][1]-60],[chim[2][0]+20,chim[2][1]-20]],{curve:true}),{n:260,r:1.0,col:'#fff',dens:(x,y)=>clamp((y-chim[2][1]+260)/260)},hg);

  // --- snø: mot veggen, sti, brøytekant, bil, gate
  const sg=G(root,{class:'snø'});
  const wallSnow=[];for(let x=-1.5;x<=L+1;x+=0.5)wallSnow.push(P(x,0.55+R(0.2,0.45),0.15+R(0,0.3)));
  white(wallSnow.concat([P(L+1,0,1.4),P(-1.5,0,1.4)]),{curve:true},sg);
  ink(wallSnow,{curve:true,w:1.6,amp:1.2,taper:0},sg);
  // fonn ved gavlen
  const gs=[];for(let z=0.4;z>=-D-1;z-=0.5)gs.push(P(-0.2-R(0,0.3),0.5+R(0.2,0.5),z));
  white(gs.concat([P(-2,0,-D-1),P(-2,0,0.4)]),{curve:true},sg);
  ink(gs,{curve:true,w:1.4,amp:1.0,taper:0},sg);
  // brøytekant: én sammenhengende fonn langs gata, med et hakk for stien
  const bank=[];
  for(let x=-8;x<=18;x+=0.4){
    let h=1.6+Math.sin(x*1.1)*0.15+Math.sin(x*2.7)*0.08;
    const c=dx+dw/2, dd=Math.abs(x-c);
    if(dd<0.8)h=0.5+dd*0.15; else if(dd<1.3)h=0.62+(dd-0.8)*2.0;
    if(x>5.2&&x<10.4)h=1.2+Math.sin(x*2)*0.05; // lavere foran bilen
    bank.push([x,h]);
  }
  const bankTopFar=bank.map(([x,h])=>P(x,h,5.4));
  const bankTopNear=bank.map(([x,h])=>P(x,h,5.9));
  // baksiden (mot huset): hvit flate ned til bakken
  white(bankTopFar.concat([P(18,0,4.6),P(-8,0,4.6)]),{curve:true},sg);
  hatch(shape(bankTopFar.concat([P(18,0,4.6),P(-8,0,4.6)]),{curve:true}),{ang:5,gap:5,w:0.8,amp:1.4,dens:(x,y)=>clamp(0.04+(y-700)/160)*0.4},sg);
  ink(bankTopFar,{curve:true,w:1.6,amp:1.2,taper:0},sg);
  // bilen står mellom baksiden og forsiden av fonnen
  const carX=5.6,carZ=4.6;
  const carG=G(sg,{class:'bil'});
  const roof=PP([[carX,1.46,carZ-0.9],[carX+4.3,1.46,carZ-0.9],[carX+4.3,1.46,carZ+0.9],[carX,1.46,carZ+0.9]]);
  const roofSnow=PP([[carX-0.05,1.62,carZ-0.95],[carX+4.35,1.62,carZ-0.95],[carX+4.35,1.62,carZ+0.95],[carX-0.05,1.62,carZ+0.95]]);
  const side=PP([[carX+0.35,1.46,carZ+0.9],[carX+3.9,1.46,carZ+0.9],[carX+4.15,1.05,carZ+0.98],[carX+0.05,1.05,carZ+0.98]]);
  const body=PP([[carX-0.1,1.05,carZ+0.98],[carX+4.3,1.05,carZ+0.98],[carX+4.3,0.5,carZ+0.98],[carX-0.1,0.5,carZ+0.98]]);
  white(body,{},carG);ink(body,{closed:true,taper:0,w:1.6,amp:0.3},carG);
  hatch(dstr(body,true),{ang:0,gap:3.5,w:0.8,dens:(x,y)=>0.45},carG);
  white(side,{},carG);ink(side,{closed:true,taper:0,w:1.8,amp:0.3},carG);
  cross(dstr(side,true),{ang:30,gap:2.6,w:0.9,dens:()=>0.75},carG);
  ink([P(carX+1.5,1.46,carZ+0.9),P(carX+1.55,1.05,carZ+0.98)],{w:2.6,amp:0.1},carG);ink([P(carX+2.7,1.46,carZ+0.9),P(carX+2.75,1.05,carZ+0.98)],{w:2.6,amp:0.1},carG);
  white(roofSnow.concat([roof[2],roof[3]]),{},carG);
  ink([roofSnow[3],roofSnow[2]],{curve:true,w:2,amp:1.0,taper:0},carG);
  ink([roof[3],roof[2]],{w:1.6,amp:0.3,taper:0},carG);
  ink([roofSnow[3],roof[3]],{w:1.4,amp:0.5},carG);ink([roofSnow[2],roof[2]],{w:1.4,amp:0.5},carG);
  // forsiden av fonnen (mot gata)
  const bankFront=bankTopNear.concat([P(18,0,7.6),P(-8,0,7.6)]);
  white(bankFront,{curve:true},sg);
  hatch(shape(bankFront,{curve:true}),{ang:-15,gap:4.5,w:0.9,amp:1.8,dens:(x,y)=>clamp(0.05+(y-740)/260)*0.6},sg);
  strokesIn(shape(bankFront,{curve:true}),{n:120,len:22,w:1.0,ang:-12,dens:(x,y)=>clamp((y-780)/260)*0.4},sg);
  ink(bankTopNear,{curve:true,w:2.4,amp:1.4,taper:0},sg);
  // stien gjennom hakket, med spor
  const pq=PP([[dx-0.35,0,1.2],[dx+dw+0.35,0,1.2],[dx+dw+0.6,0,7.4],[dx-0.6,0,7.4]]);
  hatch(dstr(pq,true),{ang:0,gap:4,w:0.7,amp:1,dens:()=>0.25},sg);
  ink([pq[0],pq[3]],{w:1.2,amp:0.8,taper:0},sg);ink([pq[1],pq[2]],{w:1.2,amp:0.8,taper:0},sg);
  for(let z=1.6;z<7;z+=0.62){for(const o of [-0.16,0.16]){const p=P(dx+dw/2+o,0.02,z+(o>0?0.31:0));E('ellipse',{cx:p[0],cy:p[1],rx:3.6,ry:1.6,fill:'#000'},sg);}}
  // gata: to par hjulspor langs gata (gata går parallelt med fasaden)
  for(const zz of [[8.6,9.0],[10.6,11.0]]){
    for(let k=0;k<2;k++){const tr=[];for(let x=-9;x<=19;x+=0.5)tr.push(P(x,0.01,zz[k]+Math.sin(x*0.5)*0.06));ink(tr,{curve:true,w:2.0,amp:0.8,taper:0},sg);}
    hatch(dstr([P(-9,0,zz[0]),P(19,0,zz[0]),P(19,0,zz[1]),P(-9,0,zz[1])],true),{ang:0,gap:4,w:0.7,amp:1.0,dens:()=>0.55},sg);
  }
  stipple(dstr([P(-8,0,7.5),P(18,0,7.5),P(18,0,8.3),P(-8,0,8.3)],true),{n:260,r:0.9,dens:()=>0.5},sg);

  // --- lyktestolpe til høyre, bjørk til venstre, kraftlinje
  const lg=G(root,{class:'lykt'});
  const lb=P(14.4,0,3.6),lt=P(14.4,6.2,3.6),la=P(13.6,6.35,3.6);
  ink([lb,lt],{w:6,amp:0.3,taper:0},lg);
  ink([lt,la],{curve:true,w:4,amp:0.2,taper:0},lg);
  black([[la[0]-22,la[1]-4],[la[0]+14,la[1]-4],[la[0]+10,la[1]+10],[la[0]-18,la[1]+10]],{},lg);
  E('ellipse',{cx:la[0]-4,cy:la[1]+10,rx:14,ry:5,fill:'#fff',stroke:'#000','stroke-width':1.2},lg);
  white([[la[0]-24,la[1]-4],[la[0]-18,la[1]-12],[la[0],la[1]-15],[la[0]+14,la[1]-9],[la[0]+16,la[1]-4]],{curve:true},lg);
  stroke([[la[0]-24,la[1]-4],[la[0]-18,la[1]-12],[la[0],la[1]-15],[la[0]+14,la[1]-9],[la[0]+16,la[1]-4]],{curve:true,w:1.2,amp:0.5},lg);
  // snø på stolpetoppen og fonn rundt foten
  const lf=[];for(let a=0;a<=6.3;a+=0.5)lf.push([lb[0]+Math.cos(a)*30,lb[1]-8+Math.sin(a)*9]);
  white(lf,{curve:true},lg);stroke(lf,{curve:true,closed:true,w:1.2,amp:0.8},lg);
  // bjørk helt til venstre, utenfor huset
  const bg2=G(root,{class:'bjørk'});
  const bx=P(-3.6,0,-1.2),btop=P(-3.4,8.8,-1.2);
  ink([bx,[bx[0]+4,bx[1]-180],[btop[0],btop[1]]],{curve:true,w:10,amp:1.5,taper:0.3},bg2);
  function branch(x,y,ang,len,w,depth){
    if(depth==0||len<12)return;
    const ex=x+Math.cos(ang)*len,ey=y+Math.sin(ang)*len;
    ink([[x,y],[x+Math.cos(ang+0.2)*len*0.5,y+Math.sin(ang+0.2)*len*0.5],[ex,ey]],{curve:true,w:w,amp:0.8,taper:0.4},bg2);
    const n=2+Math.floor(rnd()*2);
    for(let i=0;i<n;i++)branch(ex,ey,ang+R(-0.7,0.7)+(i-0.5)*0.4,len*R(0.55,0.75),w*0.65,depth-1);
  }
  branch(bx[0]+3,bx[1]-320,-1.9,100,3.5,5);branch(bx[0]+2,bx[1]-400,-1.1,90,3,5);branch(bx[0]+2,bx[1]-470,-1.6,80,2.5,5);branch(bx[0]+1,bx[1]-500,-2.5,80,2.5,4);branch(bx[0]+2,bx[1]-540,-0.9,70,2.2,4);
  for(let i=0;i<16;i++){const y=bx[1]-20-i*34;stroke([[bx[0]-5,y],[bx[0]+5,y+1]],{w:2.4,amp:0.3},bg2);}
  ink([[la[0]-10,la[1]-10],[(la[0]+P(L,hw-0.1,0)[0])/2,la[1]+50],P(L-0.2,hw-0.4,0)],{curve:true,w:1.2,amp:0.5,taper:0},lg);

  hatch(dstr(rect(0,0,W,H),true),{ang:40,gap:5,w:0.9,amp:1.2,dens:(x,y)=>clamp(Math.hypot((x-960)/1150,(y-540)/760)**3-0.5)*1.2},root);
}

