#!/usr/bin/env python3
"""Operator-only, bounded read-only native stability checks; no GUI writes."""
import argparse
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugin'))
from ownmachine.config import Config


def state(directory):
    # Refuse uninitialized state instead of initializing or resetting a gate.
    path = Path(directory) / 'lease.db'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1) as db:
        row = db.execute('SELECT controller,generation FROM lease WHERE id=1').fetchone()
    if not row or row[0] not in {'human', 'paused', 'agent'} or type(row[1]) is not int or row[1] < 0:
        raise ValueError('invalid_control_state')
    return row


def run(config, *, samples=30, interval=2, capture=False, backend_factory=None,
        sleep=time.sleep, clock=time.monotonic):
    config.validate()
    if not config.control_dir or type(samples) is not int or not 1 <= samples <= 10000:
        raise ValueError('invalid_soak_configuration')
    if not isinstance(interval, (int, float)) or isinstance(interval, bool) or not math.isfinite(interval) or not .1 <= interval <= 300:
        raise ValueError('invalid_soak_configuration')
    report = {'format': 1, 'ok': False, 'requested_samples': samples, 'completed_samples': 0,
              'interval_seconds': interval, 'capture_requested': bool(capture), 'status': 'not_started',
              'gui_writes_sent': 0, 'latency_seconds': {},
              'scope': 'Read-only native transport/capture stability. No GUI-write, semantic-task, persistence, browser-stream or firewall certification.'}
    backend = None; timings = []; started = clock()
    try:
        initial = state(config.control_dir)
        if backend_factory is None:
            from ownmachine.provider import OwnMachineBackend
            backend_factory = OwnMachineBackend
        backend = backend_factory(config)
        backend.start()
        for index in range(samples):
            if state(config.control_dir) != initial:
                report['status'] = 'control_changed'; break
            tick = clock()
            backend.list_apps()
            if capture:
                image = backend.capture(mode='vision', app='screen')
                if image.width <= 0 or image.height <= 0 or not image.png_bytes_len:
                    raise ValueError('invalid_capture')
                del image  # Never save images, AX data, app names or window titles.
            else:
                backend.list_windows()
            timings.append(clock() - tick)
            report['completed_samples'] += 1
            if state(config.control_dir) != initial:
                report['status'] = 'control_changed'; break
            if index + 1 < samples:
                sleep(interval)  # No catch-up burst or overlapping requests.
        else:
            report['status'] = 'completed'; report['ok'] = True
    except KeyboardInterrupt:
        report['status'] = 'interrupted'
    except BlockingIOError:
        report['status'] = 'native_session_busy'
    except (sqlite3.Error, OSError, ValueError):
        report['status'] = 'read_or_configuration_failed'
    except Exception:
        # Raw driver/SSH failures can contain private data. Never emit them.
        report['status'] = 'native_read_failed'
    finally:
        if backend is not None:
            try: backend.stop()
            except Exception:
                report['status'] = 'cleanup_failed'; report['ok'] = False
        report['elapsed_seconds'] = round(clock() - started, 3)
        if timings:
            ordered = sorted(timings)
            report['latency_seconds'] = {
                'minimum': round(ordered[0], 3), 'maximum': round(ordered[-1], 3),
                'p50': round(ordered[math.ceil(len(ordered) * .50) - 1], 3),
                'p95': round(ordered[math.ceil(len(ordered) * .95) - 1], 3)}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-alias', required=True)
    parser.add_argument('--guest-profile', choices=['macos','omarchy'], default='macos')
    parser.add_argument('--vm-name', default='ownmachine')
    parser.add_argument('--control-dir', required=True)
    parser.add_argument('--connect-timeout-seconds', type=int, default=15)
    parser.add_argument('--action-timeout-seconds', type=int, default=30)
    parser.add_argument('--samples', type=int, default=30)
    parser.add_argument('--interval-seconds', type=float, default=2)
    parser.add_argument('--capture', action='store_true', help='Request desktop PNGs in memory; never save or print them')
    parser.add_argument('--output', required=True, help='New private report file outside source; existing files are refused')
    args = vars(parser.parse_args())
    output = Path(args.pop('output')).expanduser().absolute()
    options = {'samples': args.pop('samples'), 'interval': args.pop('interval_seconds'), 'capture': args.pop('capture')}
    try:
        config = Config(**args).validate()
        if ROOT == output.resolve() or ROOT in output.resolve().parents:
            raise ValueError('output_inside_source')
        # Reserve a private output before connecting; never overwrite a report.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except (OSError, ValueError):
        print('Soak refused: use valid configuration and a new report path outside source with an existing parent.')
        return 1
    with os.fdopen(fd, 'w') as stream:
        try: report = run(config, **options)
        except ValueError:
            report = {'ok': False, 'status': 'invalid_soak_configuration'}
        stream.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps(report, sort_keys=True))
    return 130 if report['status'] == 'interrupted' else 0 if report['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
