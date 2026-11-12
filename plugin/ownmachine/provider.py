"""Native Hermes contract; exact guest targets, durable write gate, no CLI fallback."""
import base64
import fcntl
import json
import io
import math
import re
import shutil
import struct
import time
import uuid
from pathlib import Path
from tools.computer_use.backend import ComputerUseBackend, ComputerUseProvider, CaptureResult, ActionResult, UIElement
from .config import Config
from .lease import Lease, LeaseError
from .transport import MCPTransport, TransportError


def configured():
    from hermes_cli.config import load_config_readonly
    settings = (((load_config_readonly() or {}).get('plugins') or {}).get('entries') or {}).get('ownmachine', {}).get('settings', {})
    return Config(**{k: settings.get(k, v) for k, v in vars(Config()).items()}).validate()


def structured(reply):
    data = reply.get('structuredContent')
    if isinstance(data, dict): return data
    for part in reply.get('content', []):
        if part.get('type') == 'text':
            try:
                data = json.loads(part.get('text', ''))
                if isinstance(data, dict): return data
            except ValueError: pass
    return {}


def select_window(windows):
    """Cua 0.44: larger z_index is nearer the front; null is unknown."""
    if not windows:
        raise ValueError('window_not_found')
    candidates = [w for w in windows if w.get('on_current_space') is True] or windows
    candidates = [w for w in candidates if w.get('is_on_screen') is True] or candidates
    if len(candidates) == 1:
        return candidates[0]
    if any(type(w.get('z_index')) is not int or w['z_index'] < 0 for w in candidates):
        raise ValueError('ambiguous_window_select_explicit_id')
    front = max(w['z_index'] for w in candidates)
    selected = [w for w in candidates if w['z_index'] == front]
    if len(selected) != 1:
        raise ValueError('ambiguous_window_select_explicit_id')
    return selected[0]


class OwnMachineProvider(ComputerUseProvider):
    name = 'ownmachine'
    display_name = 'OwnMachine (private desktop VM)'

    def is_available(self):
        try: return bool(configured().control_dir and shutil.which('ssh'))
        except (ValueError, TypeError): return False

    def create_backend(self, *, permission_mode):
        return OwnMachineBackend(configured(), permission_mode)

    def doctor(self):
        from .diagnostics import diagnose, render
        try:
            from hermes_cli.config import load_config_readonly
            profile = load_config_readonly() or {}
            mode = (profile.get("computer_use") or {}).get("permission_mode", "standard")
            report = diagnose(configured(), permission_mode=mode)
        except (ValueError, TypeError):
            report = diagnose(Config())
        print(render(report))
        return 0 if report['ok'] else 1


class OwnMachineBackend(ComputerUseBackend):
    def __init__(self, config, permission_mode='standard', transport=None):
        if permission_mode != 'standard': raise ValueError('ownmachine_requires_standard_permission_mode')
        self.config = config.validate()
        if not config.control_dir: raise ValueError('shared_control_directory_required')
        self.permission_mode = permission_mode
        self.lease = Lease(Path(config.control_dir)/'lease.db')
        self.transport = transport or MCPTransport(config)
        self.session = 'ownmachine-'+uuid.uuid4().hex[:12]
        self.owner = None
        self._clear()

    def _clear(self):
        self.generation = None
        self.tokens = {}
        self.element_actions = {}
        self.element_roles = {}
        self.target = None
        self.has_pixels = False
        self.capture_id = None
        self.pixel_size = (0, 0)
        self._last_target = None
        self._last_app = None

    def is_available(self): return shutil.which('ssh') is not None

    def start(self):
        if self.owner: return
        self.owner = open(Path(self.config.control_dir)/'session.lock', 'a')
        try:
            fcntl.flock(self.owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._connect()
        except Exception:
            self.stop()
            raise

    def stop(self):
        # Closing the authenticated stream releases driver session resources.
        self.transport.stop()
        if self.owner:
            self.owner.close(); self.owner = None
        self._clear()

    def _call(self, name, args):
        schema = self.transport.tools.get(name)
        if not isinstance(schema, dict): raise ValueError('unsupported_action')
        args = dict(args)
        props = schema.get('properties', {})
        if 'session' in props: args['session'] = self.session
        if schema.get('additionalProperties') is False and set(args)-set(props):
            raise ValueError('unsupported_action_parameters')
        if set(schema.get('required', []))-set(args): raise ValueError('missing_action_parameters')
        try: return self.transport.call(name, args)
        except TransportError:
            self._clear()
            raise

    def _read(self, name, args=None):
        # Reconnect only for an explicitly requested read. A failed input is
        # never replayed, and its durable uncertainty marker survives this.
        if self.owner and hasattr(self.transport, 'process') and self.transport.process is None:
            self._clear()
            self.session = 'ownmachine-'+uuid.uuid4().hex[:12]
            self._connect()
        reply = self._call(name, args or {})
        if reply.get('isError'): raise RuntimeError('driver_read_failed')
        return reply

    def _connect(self):
        # Every new stream must pass the same compatibility/session checks.
        # Failed recovery retains the lease's durable uncertain-outcome marker.
        try:
            self.transport.start()
            from .diagnostics import REQUIRED_TOOLS
            if not REQUIRED_TOOLS <= self.transport.tools.keys():
                raise RuntimeError('incompatible_driver_tools')
            established = self._call('start_session', {'session': self.session})
            if established.get('isError'):
                raise RuntimeError('driver_session_failed')
        except Exception:
            self._clear()
            self.transport.stop()
            raise

    def list_apps(self):
        return structured(self._read('list_apps')).get('apps', [])

    def list_windows(self):
        return structured(self._read('list_windows')).get('windows', [])

    def capture(self, mode='som', app=None, pid=None, window_id=None):
        self._clear()
        before = self.lease.status()['generation']
        if mode not in {'som','ax','vision'}: raise ValueError('unsupported_capture_mode')
        desktop = app in {'desktop','screen','fullscreen','full_screen'}
        target = None
        if desktop:
            reply = self._read('get_desktop_state', {'max_image_dimension': 1456})
        else:
            windows = self.list_windows()
            matches = [w for w in windows if (pid is None or w.get('pid')==pid)
                       and (window_id is None or w.get('window_id')==window_id)
                       and (not app or app.lower() in {str(w.get('app_name','')).lower(), str(w.get('bundle_id','')).lower()})]
            w = select_window(matches)
            target = {'pid': w['pid'], 'window_id': w['window_id']}
            reply = self._read('get_window_state', {**target, 'tree_format':'elements',
                'max_elements':200, 'include_screenshot':mode!='ax',
                'include_accessibility_tree':mode!='vision', 'max_image_dimension':1456})
        data = structured(reply)
        image = next((p for p in reply.get('content', []) if p.get('type')=='image'), None)
        encoded = image.get('data') if image else data.get('screenshot_png_b64')
        raw = base64.b64decode(encoded, validate=True) if encoded else b''
        if mode != 'ax' and (len(raw)<24 or raw[:8]!=b'\x89PNG\r\n\x1a\n'):
            raise ValueError('capture_missing_png')
        width,height = struct.unpack('>II',raw[16:24]) if raw else (0,0)
        if raw and (not 0 < width <= 8192 or not 0 < height <= 8192 or width*height > 32000000):
            raise ValueError('capture_dimensions_invalid')
        elements = []
        for row in data.get('elements', []):
            index, token = row.get('element_index'), row.get('element_token')
            if type(index) is not int or not isinstance(token,str) or not re.fullmatch(r's[0-9a-f]{8}:[0-9]+',token): continue
            frame = row.get('frame') or {}
            # AX frames are global points; expose only proven screenshot-local
            # bounds. AX-only captures deliberately have unknown pixel bounds.
            origin = data.get('window_bounds') or (w.get('bounds', {}) if target else {})
            shot_frame = row.get('screenshot_frame')
            if raw and isinstance(shot_frame,dict) and all(type(shot_frame.get(k)) in (int,float) and math.isfinite(shot_frame[k]) for k in ('x','y','w','h')):
                bounds=tuple(int(shot_frame[k]) for k in ('x','y','w','h'))
                if bounds[0]<0 or bounds[1]<0 or bounds[2]<=0 or bounds[3]<=0 or bounds[0]+bounds[2]>width or bounds[1]+bounds[3]>height:
                    bounds=(0,0,0,0)
            elif raw and origin.get('width',0)>0 and origin.get('height',0)>0:
                sx,sy=width/origin['width'],height/origin['height']
                bounds=(int((frame.get('x',0)-origin.get('x',0))*sx),
                        int((frame.get('y',0)-origin.get('y',0))*sy),
                        int(frame.get('w',0)*sx),int(frame.get('h',0)*sy))
                if bounds[0]<0 or bounds[1]<0 or bounds[0]+bounds[2]>width or bounds[1]+bounds[3]>height:
                    bounds=(0,0,0,0)
            else: bounds=(0,0,0,0)
            elements.append(UIElement(index=index+1, role=row.get('role',''), label=row.get('label') or row.get('value') or '',
                bounds=bounds, app=app or '', pid=(target or {}).get('pid',0), window_id=(target or {}).get('window_id',0),
                element_token=token, attributes={k:row[k] for k in ('actions','value','enabled','focused') if k in row}))
        if before != self.lease.status()['generation']: raise LeaseError('stale_capture')
        self.generation = before
        self.has_pixels = bool(raw)
        self.capture_id = data.get("capture_id") if raw else None
        self.pixel_size = (width, height)
        self.target = target or {'scope':'desktop'}
        self.tokens = {e.index:e.element_token for e in elements}
        self.element_actions = {e.index:e.attributes['actions'] for e in elements if isinstance(e.attributes.get('actions'),list)}
        self.element_roles = {e.index:e.role for e in elements}
        self._last_target = target
        self._last_app = app or data.get('app_name')
        output_mode = mode
        note = 'Pixel coordinates are local to this exact screenshot. Take a fresh capture after every pixel click; its capture binding is single-use. Element clicks invoke AXPress, not mouse focus. For a field without AXPress, use set_value or a fresh screenshot-grounded pixel click. Popup set_value selects only an existing menu option: inspect the open menu first, never guess a destination. File-location popups can list ancestors rather than destinations; use the dialog navigation controls or keyboard shortcuts for other folders. Any operator_review_required result overrides generic retry advice; stop until the operator inspects and acknowledges it. Each new capture replaces earlier tokens.\n'
        note += '\n'.join(f'#{e.index} actions: '+', '.join(str(a) for a in e.attributes['actions']) for e in elements if 'actions' in e.attributes)
        if self.config.guest_profile == 'omarchy':
            note += '\nLinux text/entry elements: use set_value to edit their contents; do not use element click to focus them. Foreground compositor input requires the explicitly enabled ABI-matched Hyprland module.\n'
        if mode == 'som' and raw:
            try:
                from PIL import Image, ImageDraw
                with Image.open(io.BytesIO(raw)) as screenshot:
                    annotated = screenshot.convert('RGB')
                draw = ImageDraw.Draw(annotated)
                for element in elements:
                    x,y,wid,hei = element.bounds
                    if wid<=0 or hei<=0: continue
                    label = str(element.index)
                    x,y = max(0,min(x,width-30)),max(0,min(y,height-16))
                    draw.rectangle((x,y,x+max(18,len(label)*7+4),y+14),fill='#ffe066')
                    draw.text((x+2,y+1),label,fill='black')
                stream=io.BytesIO();annotated.save(stream,format='PNG')
                raw=stream.getvalue();encoded=base64.b64encode(raw).decode()
            except ImportError:
                output_mode='vision'
                note+='\nPillow unavailable: AX indices refer to the tree; image has no numbered overlays.'
        return CaptureResult(mode=output_mode, width=width,height=height,
            png_b64=encoded, png_bytes_len=len(raw), image_mime_type='image/png' if raw else None,
            elements=elements, app=app or data.get('app_name',''), window_title=data.get('window_title',''),
            ax_max_elements=200, note=note)

    def _write(self, name, args):
        try:
            if self.generation is None:
                return ActionResult(False, name, code='capture_required', message='Capture the desktop or intended window before launch, focus or input.')
            # Unknown operations and parameters never enter the dispatch gate.
            schema = self.transport.tools.get(name, {})
            props = schema.get('properties', {})
            if name not in self.transport.tools or (schema.get('additionalProperties') is False and set(args)-set(props)):
                raise ValueError('unsupported_action')
            with self.lease.write(self.generation):
                reply = self._call(name,args)
                data = structured(reply)
                if reply.get('isError') is True or data.get('ok') is False:
                    raise LeaseError('driver_action_failed_review_required')
                if data.get('code') in {'transport_outcome_unknown','timeout_outcome_unknown'}:
                    raise TransportError('transport_outcome_unknown')
            failed = reply.get('isError') is True or data.get('ok') is False
            message = data.get('summary') or data.get('message') or ''
            if not message:
                message = '\n'.join(p.get('text','') for p in reply.get('content',[]) if p.get('type')=='text')[:1200]
            return ActionResult(ok=not failed, action=name, message=message,
                effect=data.get('effect'), verified=data.get('verified'), code=data.get('code'),
                escalation=data.get('escalation'), path=data.get('path') or data.get('route'),
                delivery_mode=args.get('delivery_mode'), degraded=data.get('degraded'))
        except (ValueError, LeaseError, TransportError) as e:
            if str(e)=='driver_action_failed_review_required':
                return ActionResult(False,name,code=str(e),message='Driver action failed. All further writes are blocked. Stop for operator inspection and acknowledgement; do not retry or escalate input.',
                    effect=data.get('effect'),verified=data.get('verified'),
                    meta={'operator_review_required': True, 'ownmachine_control_gate': True, 'driver_code': data.get('code'),
                          'driver_message': (data.get('summary') or data.get('message') or '\n'.join(p.get('text','') for p in reply.get('content',[]) if p.get('type')=='text'))[:1200]},
                    path=data.get('path') or data.get('route'))
            if isinstance(e, LeaseError) and str(e) == 'transport_outcome_unknown':
                return ActionResult(False, name, code=str(e), message='No new action was dispatched. A previous action requires operator inspection and acknowledgement. Do not retry or escalate input.', meta={'dispatched': False, 'operator_review_required': True, 'ownmachine_control_gate': True})
            return ActionResult(ok=False, action=name, code=str(e), message=str(e),
                meta={'operator_review_required': True, 'ownmachine_control_gate': True} if str(e)=='transport_outcome_unknown' else {})

    def _input(self, name, args, delivery_mode=None, bring_to_front=False):
        if self.target is None: return ActionResult(False,name,code='capture_required',message='Capture a target first.')
        if ('x' in args or 'y' in args) and not self.has_pixels:
            return ActionResult(False,name,code='pixel_capture_required')
        if delivery_mode not in {None,'background','foreground'}:
            return ActionResult(False,name,code='unsupported_delivery_mode')
        if self.config.guest_profile == 'omarchy':
            if delivery_mode == 'background':
                return ActionResult(False,name,code='linux_background_input_not_certified',meta={'dispatched':False})
            delivery_mode = 'foreground'
        if name == 'click' and 'x' in args:
            if not isinstance(self.capture_id, str) or not self.capture_id:
                return ActionResult(False,name,code='fresh_pixel_capture_required',message='Capture a fresh screenshot before this pixel click.',meta={'dispatched':False})
            if 'capture_id' not in self.transport.tools.get(name,{}).get('properties',{}):
                return ActionResult(False,name,code='capture_binding_unsupported',message='This driver cannot bind pixel clicks to captures.',meta={'dispatched':False})
            if any(type(args.get(k)) not in (int,float) or not math.isfinite(args[k]) or not 0 <= args[k] < limit for k,limit in zip(('x','y'),self.pixel_size)):
                return ActionResult(False,name,code='pixel_coordinates_out_of_bounds',meta={'dispatched':False})
            args = {**args, 'capture_id':self.capture_id}
            self.capture_id = None  # Never replay a consumed or uncertain frame.
        if bring_to_front:
            if 'pid' not in self.target: return ActionResult(False,name,code='window_capture_required')
            front = self._write('bring_to_front', self.target)
            if not front.ok: return front
        payload = {**self.target, **args}
        if 'element_token' in args:
            props=self.transport.tools.get(name,{}).get('properties',{})
            for key in ('pid','window_id'):
                if key not in props: payload.pop(key,None)
        if delivery_mode: payload['delivery_mode'] = delivery_mode
        return self._write(name,payload)

    def _element(self, element):
        if element is None: return {}
        if element not in self.tokens: raise ValueError('stale_element')
        return {'element_token':self.tokens[element]}

    def click(self, *, element=None,x=None,y=None,button='left',click_count=1,modifiers=None,delivery_mode=None,bring_to_front=False):
        if modifiers or button not in {'left','right'} or click_count not in {1,2} or (button=='right' and click_count!=1):
            return ActionResult(False,'click',code='unsupported_action')
        name = 'right_click' if button=='right' else 'double_click' if click_count==2 else 'click'
        try:
            args = self._element(element) if element is not None else {'x':x,'y':y}
            if (element is not None and self.config.guest_profile == 'omarchy'
                    and self.element_roles.get(element) in {'text','entry','password text'}):
                return ActionResult(False,name,code='element_press_unsupported',message='Linux text elements are not activation targets. No input was dispatched. Use set_value for text or a fresh screenshot-grounded foreground pixel click to focus.',meta={'dispatched':False})
            if element is not None and name == 'click' and 'AXPress' not in self.element_actions.get(element, ['AXPress']):
                return ActionResult(False, name, code='element_press_unsupported', message='This element does not advertise AXPress. No input was dispatched. Use an appropriate value action or a fresh screenshot-grounded pixel click.', meta={'dispatched':False})
            if element is None and (x is None or y is None): raise ValueError('coordinates_required')
            if element is None:
                name = 'click'
                args.update(button=button,count=click_count)
            return self._input(name,args,delivery_mode,bring_to_front)
        except ValueError as e: return ActionResult(False,name,code=str(e))

    def type_text(self,text,*,delivery_mode=None,bring_to_front=False):
        return self._input('type_text',{'text':text},delivery_mode,bring_to_front)

    def key(self,keys,*,delivery_mode=None,bring_to_front=False):
        parts = keys.split('+')
        return self._input('hotkey' if len(parts)>1 else 'press_key',
            {'keys':parts} if len(parts)>1 else {'key':keys},delivery_mode,bring_to_front)

    def scroll(self,*,direction,amount=3,element=None,x=None,y=None,modifiers=None,delivery_mode=None,bring_to_front=False):
        if modifiers: return ActionResult(False,'scroll',code='unsupported_action')
        try:
            args = {'direction':direction,'amount':amount,**self._element(element)}
            if x is not None and y is not None: args.update(x=x,y=y)
            return self._input('scroll',args,delivery_mode,bring_to_front)
        except ValueError as e: return ActionResult(False,'scroll',code=str(e))

    def set_value(self,value,element=None):
        try:
            if element is None: raise ValueError('element_required')
            return self._input('set_value',{'value':value,**self._element(element)})
        except ValueError as e: return ActionResult(False,'set_value',code=str(e))

    def drag(self,**kwargs):
        return ActionResult(False,'drag',code='unsupported_action',message='Drag is not supported in this release.')

    def focus_app(self,app,raise_window=False):
        try:
            matches = [a for a in self.list_apps() if app.lower() in {str(a.get('name','')).lower(),str(a.get('bundle_id','')).lower()}]
            if len(matches)!=1: return ActionResult(False,'focus_app',code='app_not_unique')
            pid = matches[0].get('pid')
            if not pid:
                bundle_id = matches[0].get('bundle_id')
                launch = {'bundle_id':bundle_id}
                if self.config.guest_profile == 'omarchy':
                    # Linux desktop discovery provides a launch_path; the
                    # macOS bundle_id argument alone cannot launch Linux apps.
                    path = matches[0].get('launch_path')
                    if not isinstance(path,str) or not path or any(ord(c)<32 for c in path):
                        return ActionResult(False,'focus_app',code='linux_launch_identity_missing')
                    launch = {'launch_path':path}
                result = self._write('launch_app', launch)
                if not result.ok or not raise_window: return result
                # Launch is background-only. Honor an explicitly requested raise,
                # resolving the new process/window rather than reusing the capture's
                # old target. Poll reads only; never replay launch or bypass the gate.
                deadline = time.monotonic() + self.config.action_timeout_seconds
                while True:
                    launched = [a for a in self.list_apps() if a.get('bundle_id') == bundle_id and a.get('pid')]
                    windows = self.list_windows() if len(launched)==1 else []
                    windows = [w for w in windows if w.get('pid') == launched[0]['pid']] if len(launched)==1 else []
                    if windows: break
                    if time.monotonic() >= deadline:
                        return ActionResult(False,'focus_app',code='launched_window_not_ready',
                            message='App launch was dispatched, but no unique process with a window was observed before the action timeout. Capture fresh state before retrying focus; do not assume launch failed.')
                    time.sleep(0.1)
            else:
                windows = [w for w in self.list_windows() if w.get('pid')==pid]
            if not windows: return ActionResult(False,'focus_app',code='window_not_found')
            try: window = select_window(windows)
            except ValueError as error:
                return ActionResult(False,'focus_app',code=str(error),message='List windows and capture the intended window by explicit ID.')
            target = {'pid':window['pid'],'window_id':window['window_id']}
            return (self._write('bring_to_front',target) if raise_window else
                    ActionResult(True,'focus_app',message='Target selected; capture before input.'))
        finally:
            # Launch/focus (including failed selection) invalidates prior targets.
            self._clear()
