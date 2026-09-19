const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
const src=fs.readFileSync(path.resolve(__dirname,'../web/spatial-camera.js'),'utf8');const m=await import('data:text/javascript;base64,'+Buffer.from(src).toString('base64'));
let count=0;
for(const yaw of [0,.55,-1.2])for(const pitch of [0,.45,-.7])for(const azimuth of [0,45,359,720,-360]){
 const pose={time:.5,azimuth,elevation:12,distance:1.3};const b=m.observerBasis(yaw,pitch);
 const zero=m.dragOrbit(pose,0,0,90,yaw,pitch);assert.ok(Math.abs(zero.azimuth-azimuth)<1e-7);assert.ok(Math.abs(zero.elevation-12)<1e-7);
 const next=m.dragOrbit(pose,1,-1,90,yaw,pitch);const a=m.position(pose),c=m.position(next);
 // Away from the silhouette the projected result tracks the pointer exactly.
 if(Math.abs(m.dot(a,b.depth))>.4){assert.ok(Math.abs((m.dot(c,b.right)-m.dot(a,b.right))*90-1)<1e-7);assert.ok(Math.abs((m.dot(c,b.up)-m.dot(a,b.up))*90-1)<1e-7);}
 assert.equal(next.distance,pose.distance);assert.equal(next.time,pose.time);count++;
}
const edge=m.dragOrbit({time:1,azimuth:359,elevation:0,distance:1},10000,-10000,50,0,0,30);assert.ok(Number.isFinite(edge.azimuth)&&Math.abs(edge.elevation)<=30);
for(const elevation of [-89,0,89]){const b=m.cameraBasis({azimuth:720,elevation,distance:.1});assert.ok(Math.abs(m.dot(b.right,b.up))<1e-8);assert.ok(m.frustum({azimuth:720,elevation,distance:.1}).corners.flat().every(Number.isFinite));}
console.log(`PASS: ${count} geometry cases, ray/sphere projection, full-turn continuity, bounds, pole basis and frustum.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
