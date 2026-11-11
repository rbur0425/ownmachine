// Exercise the vendored event handler without a browser or guest connection.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source = fs.readFileSync(new URL('../viewer/vendor/novnc/core/rfb.js', import.meta.url), 'utf8');
const methods = source.slice(source.indexOf('    static _convertButtonMask('), source.indexOf('    _handleMouseButton('));
const clientToElement = (x,y) => ({x,y});
const setCapture = () => {};
const dragThreshold = 10;
const RFB = eval(`(class RFB { ${methods} })`);
const rfb = new RFB();
rfb._canvas = {};
rfb.dragViewport = false;
let sent = [];
rfb._handleMouseButton = (x,y,mask) => sent.push(mask);
rfb._handleMouseMove = () => {};
function event(type, button, buttons) {
  rfb._handleMouse({type,button,buttons,clientX:10,clientY:20,
    target:rfb._canvas,stopPropagation(){},preventDefault(){}});
}
for (const [button,mask] of [[0,1],[1,2],[2,4]]) {
  sent=[];
  event('mousedown',button,0); event('mouseup',button,0);
  assert.deepEqual(sent,[mask,0],`zero-mask button ${button} must press and release`);
}
sent=[];
event('mousedown',0,1); event('mousedown',2,3); event('mouseup',2,1); event('mouseup',0,0);
assert.deepEqual(sent,[1,5,1,0],'normal chord masks remain intact');
sent=[]; event('mousedown',9,0); event('click',0,0);
assert.deepEqual(sent,[0],'unknown button and click must not invent a press');
console.log('Viewer pointer regression passed (left/middle/right, releases, chords, unknown button).');
