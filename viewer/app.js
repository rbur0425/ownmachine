import RFB from '/vendor/novnc/core/rfb.js';
'use strict';
const byId=id=>document.getElementById(id);
window.addEventListener('hashchange',()=>{if(location.hash)location.reload();});
const supplied=location.hash.slice(1)||sessionStorage.getItem('ownmachineToken')||'';
if(location.hash)history.replaceState(null,'',location.pathname);
sessionStorage.removeItem('ownmachineToken');
const token=''; // Authentication is a browser-session HttpOnly cookie.
let viewerMode='frames',rfb=null,streamStatus='Connecting stream…',streamGeneration=null,reconnectAt=0;
let pendingControlFocus=null;
let control=null,busy=false,imageURL=null,stopped=false,frameId=null,viewOnly=true,interval=1000,frameBusy=false;
async function request(path,options={}){
 const r=await fetch(path,{...options,cache:'no-store',headers:{'X-OwnMachine-Token':token,...(options.headers||{})}});
 if(!r.ok){if(r.status===403){stopped=true;if(rfb){rfb.disconnect();rfb=null;}document.body.classList.add('locked');byId('login').hidden=false;throw Error('Unlock the viewer with your private access link.');}const data=await r.json().catch(()=>({}));const messages={fresh_frame_required:'Desktop changed or the frame expired. Wait for a fresh picture, then try again.',stale_target:'Control changed. Wait for a fresh picture before sending input.',paused:'Reserve for human use before clicking or typing.',human_takeover:'Control changed. Check who holds the reservation.',viewer_read_only:'This server was started in read-only mode.',operation_in_progress:'Another operation is still running. Wait for it to finish.'};throw Error(messages[data.error]||'An operation may have happened. Inspect the desktop and control state before trying again.');}
 return r;
}
function canInput(){return viewerMode==='frames'&&!viewOnly&&!busy&&!stopped&&control?.controller==='human'&&!control.pending&&frameId;}
function buttons(){
 document.querySelectorAll('[data-action]').forEach(b=>{
  b.disabled=busy||!control||stopped;
  if(['agent','human','paused'].includes(b.dataset.action)&&control){
   const selected=control.controller===b.dataset.action;
   b.classList.toggle('primary',selected);
   b.setAttribute('aria-pressed',String(selected));
  }
 });
 if(pendingControlFocus&&!pendingControlFocus.disabled){
  const button=pendingControlFocus;pendingControlFocus=null;
  if(document.activeElement===document.body||document.activeElement===button)button.focus({preventScroll:true});
 }
 document.querySelectorAll('[data-input],#send-text').forEach(b=>b.disabled=!canInput());
 byId('desktop').classList.toggle('interactive',!!canInput());
 byId('mode').textContent=viewOnly?'View only':control?.controller==='human'?'Human control':'View only';
}
function connectStream(s){
 streamStatus='Connecting stream…';streamGeneration=control.generation;
 const connection=new RFB(byId('stream'),`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/stream`,{shared:true});
 rfb=connection;connection.scaleViewport=true;connection.resizeSession=false;
 connection.viewOnly=viewOnly||control.controller!=='human'||control.pending;
 connection.qualityLevel=s.quality;connection.compressionLevel=s.compression;
 connection.addEventListener('connect',()=>{if(rfb===connection)streamStatus='Connected · live desktop';});
 connection.addEventListener('disconnect',()=>{
  if(rfb===connection){rfb=null;streamStatus='Stream disconnected · reconnecting…';reconnectAt=Date.now()+2000;}
 });
 connection.addEventListener('securityfailure',()=>{streamStatus='Stream authentication failed. Check the host VNC setup.';});
}
async function state(){
 if(stopped)return;
 try{
  const s=await(await request('/api/state')).json();control=s.control;viewOnly=s.view_only;viewerMode=s.viewer_mode;interval=Math.max(250,s.frame_interval*1000);
  byId('stream').hidden=viewerMode!=='vnc';byId('stream').classList.toggle('swap-rb',s.swap_red_blue===true);byId('frame-tools').hidden=viewerMode==='vnc';byId('stream-help').hidden=viewerMode!=='vnc';
  if(viewerMode==='vnc'){
   byId('desktop').hidden=true;byId('empty').hidden=true;
   if(rfb&&streamGeneration!==control.generation){rfb.disconnect();rfb=null;reconnectAt=Date.now()+300;}
   if(rfb)rfb.viewOnly=viewOnly||control.controller!=='human'||control.pending||!!s.operation;
   if(!rfb&&!s.operation&&Date.now()>=reconnectAt)connectStream(s);
  }
  byId('vm').textContent=s.host.vm_state||'Unknown';
  byId('controller').textContent=s.control.pending?'Review required':s.control.controller;
  byId('age').textContent=viewerMode==='vnc'?'Live stream':s.frame_age===null?'Waiting':s.frame_age+'s ago';
  byId('connection').textContent=s.operation?s.operation+' in progress…':viewerMode==='vnc'?streamStatus:s.capture_error?'Waiting for desktop':canInput()?'Connected · human control':'Connected · view only';
  const uncertainty='An operation has an uncertain outcome. Inspect the VM before acknowledging it.';
  if(s.control.pending)byId('notice').textContent=uncertainty;
  else if(byId('notice').textContent===uncertainty)byId('notice').textContent='Control is ready.';
 }catch(e){control=null;byId('connection').textContent=e.message;}
 finally{buttons();if(!stopped)setTimeout(state,1000);}
}
async function frame(){
 if(stopped||frameBusy)return;
 frameBusy=true;
 try{
  const response=await request('/api/frame');const id=response.headers.get('X-OwnMachine-Frame');
  const blob=await response.blob();const next=URL.createObjectURL(blob);
  const img=new Image();img.src=next;await img.decode();
  byId('desktop').src=next;frameId=id;
  if(imageURL)URL.revokeObjectURL(imageURL);imageURL=next;
  byId('desktop').hidden=false;byId('desktop').classList.remove('stale');byId('empty').hidden=true;
 }catch(e){frameId=null;byId('desktop').classList.add('stale');byId('empty').hidden=false;byId('empty').textContent=stopped?e.message:'Desktop unavailable. Waiting for the VM…';}
 finally{frameBusy=false;buttons();}
}
async function refreshFrames(){if(!busy&&viewerMode==='frames')await frame();if(!stopped)setTimeout(refreshFrames,interval);}
async function input(payload){
 if(!canInput()){byId('notice').textContent='Reserve for human use and wait for a fresh desktop before sending input.';return;}
 const current=frameId;busy=true;buttons();byId('notice').textContent='Sending once…';
 try{
  const result=await(await request('/api/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,frame_id:current})})).json();
  byId('notice').textContent=result.verified?'Input verified.':'Input delivered. Check the desktop for the result.';
  if(payload.kind==='text')byId('text').value='';
 }catch(e){byId('notice').textContent=e.message;}
 finally{frameId=null;busy=false;buttons();await frame();}
}
document.querySelectorAll('[data-action]').forEach(button=>button.addEventListener('click',async()=>{
 const action=button.dataset.action,payload={action};
 if(['stop','restart'].includes(action)&&!confirm('Save your work first. This will '+(action==='stop'?'shut down':'restart')+' the VM and end running apps. Agent control will stay paused. Continue?'))return;
 if(['agent','human','paused'].includes(action)&&control?.pending){
  if(!confirm('An operation may already have happened. Have you inspected the VM and are you ready to acknowledge that uncertainty?'))return;
  payload.acknowledge=true;
 }
 if(['agent','human','paused'].includes(action))pendingControlFocus=button;
 busy=true;buttons();byId('notice').textContent='Working…';
 try{await request('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});control=null;frameId=null;byId('notice').textContent='Done. Waiting for fresh status.';}
 catch(e){byId('notice').textContent=e.message;}
 finally{busy=false;buttons();}
}));
byId('desktop').addEventListener('click',event=>{
 const img=byId('desktop'),r=img.getBoundingClientRect();
 const scale=Math.min(r.width/img.naturalWidth,r.height/img.naturalHeight);
 const x=Math.floor((event.clientX-r.left-(r.width-img.naturalWidth*scale)/2)/scale);
 const y=Math.floor((event.clientY-r.top-(r.height-img.naturalHeight*scale)/2)/scale);
 if(x<0||y<0||x>=img.naturalWidth||y>=img.naturalHeight)return;
 input({kind:'click',x,y,button:byId('click-mode').value==='right'?'right':'left',count:byId('click-mode').value==='double'?2:1});
});
byId('desktop').addEventListener('dragstart',e=>e.preventDefault());
byId('send-text').addEventListener('click',()=>{const text=byId('text').value;if(text)input({kind:'text',text});});
document.querySelectorAll('[data-input]').forEach(b=>b.addEventListener('click',()=>{
 if(b.dataset.input==='scroll')input({kind:'scroll',direction:b.dataset.direction,amount:3});
 else input({kind:'key',keys:b.dataset.keys.split('+')});
}));
async function login(value){
 let candidate=value.trim();
 if(candidate.includes('#'))candidate=candidate.slice(candidate.indexOf('#')+1);
 const r=await fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:candidate})});
 if(!r.ok)throw Error('Access link is invalid or expired. Use the current link from viewer-access.json.');
}
byId('login-form').addEventListener('submit',async event=>{
 event.preventDefault();
 try{await login(byId('access-link').value);byId('access-link').value='';location.reload();}
 catch(e){byId('login-error').textContent=e.message;}
});
async function boot(){
 if(supplied){try{await login(supplied);}catch(e){byId('login-error').textContent=e.message;}}
 buttons();await state();refreshFrames();
}
boot();
