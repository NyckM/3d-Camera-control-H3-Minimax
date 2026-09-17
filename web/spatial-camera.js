// Original geometry implementation. Distances share the editor's 1.8-unit radius.
const rad=v=>v*Math.PI/180;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
export const add=(a,b)=>a.map((v,i)=>v+b[i]);
export const mul=(a,s)=>a.map(v=>v*s);
export const dot=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const unit=a=>mul(a,1/Math.max(1e-12,Math.hypot(...a)));
export function position(p){const a=rad(p.azimuth),e=rad(p.elevation),r=p.distance*1.8;return [Math.sin(a)*Math.cos(e)*r,Math.sin(e)*r,Math.cos(a)*Math.cos(e)*r];}
export function observerBasis(yaw,pitch){return {right:[Math.cos(yaw),0,-Math.sin(yaw)],up:[-Math.sin(yaw)*Math.sin(pitch),Math.cos(pitch),-Math.cos(yaw)*Math.sin(pitch)],depth:[Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),Math.cos(yaw)*Math.cos(pitch)]};}
export function dragOrbit(original,dx,dy,scale,yaw,pitch,limit=89){
  // Orthographic pointer ray intersects a sphere about the subject. Preserve the
  // starting hemisphere; outside the silhouette, clamp to its rim continuously.
  const basis=observerBasis(yaw,pitch),p=position(original),r=original.distance*1.8;
  let x=dot(p,basis.right)+dx/scale,y=dot(p,basis.up)-dy/scale;
  const length=Math.hypot(x,y);if(length>r){x*=r/length;y*=r/length;}
  const sign=dot(p,basis.depth)<0?-1:1,z=sign*Math.sqrt(Math.max(0,r*r-x*x-y*y));
  const next=add(add(mul(basis.right,x),mul(basis.up,y)),mul(basis.depth,z));
  const raw=Math.atan2(next[0],next[2])*180/Math.PI;
  const azimuth=original.azimuth+((raw-original.azimuth+180)%360+360)%360-180;
  return {...original,azimuth:clamp(azimuth,-11520,11520),elevation:clamp(Math.asin(clamp(next[1]/r,-1,1))*180/Math.PI,-limit,limit)};
}
export function cameraBasis(pose){const eye=position(pose),forward=unit(mul(eye,-1));let right=unit(cross(forward,[0,1,0]));if(Math.hypot(...right)<.1)right=[1,0,0];return {eye,forward,right,up:unit(cross(right,forward))};}
export function frustum(pose,aspect=16/9){const b=cameraBasis(pose),depth=.45,t=Math.tan(rad(20));const center=add(b.eye,mul(b.forward,depth));return {eye:b.eye,corners:[[-1,-1],[1,-1],[1,1],[-1,1]].map(([x,y])=>add(center,add(mul(b.right,x*depth*t*aspect),mul(b.up,y*depth*t))))};}
export function drawCameraView(canvas,pose,aspect=16/9){
 const width=canvas.clientWidth||400,height=canvas.clientHeight||230,dpr=Math.min(globalThis.devicePixelRatio||1,2);
 canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);
 const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#10131b';ctx.fillRect(0,0,width,height);
 const w=Math.min(width,height*aspect),h=w/aspect,left=(width-w)/2,top=(height-h)/2;
 ctx.save();ctx.beginPath();ctx.rect(left,top,w,h);ctx.clip();ctx.fillStyle='#202733';ctx.fillRect(left,top,w,h);
 const basis=cameraBasis(pose),t=Math.tan(rad(20)),near=.025;
 const camera=p=>{const v=add(p,mul(basis.eye,-1));return [dot(v,basis.right),dot(v,basis.up),dot(v,basis.forward)];};
 const screen=p=>[left+w/2+p[0]/(p[2]*t*aspect)*w/2,top+h/2-p[1]/(p[2]*t)*h/2];
 function clip(vertices){const out=[];for(let i=0;i<vertices.length;i++){const a=vertices[i],b=vertices[(i+1)%vertices.length],inside=a[2]>=near;if(inside)out.push(a);if(inside!==(b[2]>=near)){const u=(near-a[2])/(b[2]-a[2]);out.push(a.map((v,j)=>v+(b[j]-v)*u));}}return out;}
 function line(a,b){a=camera(a);b=camera(b);if(a[2]<near&&b[2]<near)return;if(a[2]<near||b[2]<near){const u=(near-a[2])/(b[2]-a[2]),c=a.map((v,i)=>v+(b[i]-v)*u);if(a[2]<near)a=c;else b=c;}ctx.beginPath();ctx.moveTo(...screen(a));ctx.lineTo(...screen(b));ctx.stroke();}
 ctx.strokeStyle='#3a5363';ctx.lineWidth=1;
 for(let n=-8;n<=8;n++){line([n*.3,-.7,-2.4],[n*.3,-.7,2.4]);line([-2.4,-.7,n*.3],[2.4,-.7,n*.3]);}
 const faces=[];
 function box(center,size,color){const vertices=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]].map(v=>camera(v.map((x,i)=>center[i]+x*size[i]/2)));
 for(const ids of [[0,1,2,3],[4,7,6,5],[0,4,5,1],[3,2,6,7],[1,5,6,2],[0,3,7,4]]){const points=clip(ids.map(i=>vertices[i]));if(points.length>=3)faces.push({points,color,depth:points.reduce((s,p)=>s+p[2],0)/points.length});}}
 box([0,.05,0],[.38,.55,.23],'#34968f');box([0,.47,0],[.25,.25,.25],'#c6a98a');
 box([-.27,.03,0],[.13,.52,.16],'#287c80');box([.27,.03,0],[.13,.52,.16],'#287c80');
 box([-.11,-.45,0],[.15,.5,.19],'#39629a');box([.11,-.45,0],[.15,.5,.19],'#39629a');
 box([0,.48,.135],[.13,.06,.035],'#f4f0d2');
 faces.sort((a,b)=>b.depth-a.depth);
 for(const f of faces){ctx.beginPath();f.points.forEach((p,i)=>{const q=screen(p);i?ctx.lineTo(...q):ctx.moveTo(...q);});ctx.closePath();ctx.fillStyle=f.color;ctx.fill();ctx.strokeStyle='#15262b';ctx.lineWidth=.7;ctx.stroke();}
 ctx.restore();ctx.strokeStyle='#6c8097';ctx.strokeRect(left,top,w,h);
}
