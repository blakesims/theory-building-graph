#!/usr/bin/env python3
"""Live browser smoke test of the viewer on a temporary synthetic graph.

Requires Node and `npx agent-browser@0.27.0`; not part of `make test`.
Run with `make browser-smoke` or `python3 -m tests.acceptance.browser_smoke [--out DIR]`.
Screenshots and the command log go to --out (default: a temporary directory).
"""
import argparse, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from theorygraph import graph

log = []


def browser(out, *args):
    cmd = ['npx', '--yes', 'agent-browser@0.27.0', '--session', 'theory-smoke', *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    log.append({'command': cmd, 'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr})
    (out/'commands.json').write_text(json.dumps(log, indent=2)+'\n')
    if r.returncode: raise RuntimeError(r.stderr or r.stdout)
    return r.stdout


def tg(path, *args):
    r = subprocess.run([sys.executable, str(ROOT/'tg'), '--file', str(path), *args], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr or r.stdout)
    return r.stdout


def build_graph(path):
    """A small synthetic graph: one entity, one claim, one open question that depends on the claim."""
    path.write_bytes((ROOT/'theorygraph'/'template.json').read_bytes())
    tg(path, 'entity', 'add', 'owner', 'Owner', '--reason', 'Smoke anchor')
    tg(path, 'claim', 'add', 'owner-approves', 'The owner approves releases.', '--about', 'owner', '--status', 'accepted', '--reason', 'Smoke claim')
    tg(path, 'question', 'add', 'release-cadence', 'How often are releases cut?', '--about', 'owner', '--depends-on', 'owner-approves', '--reason', 'Smoke question')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=None, help='Directory for screenshots and the command log')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='theory-browser-') as d:
        out = args.out or Path(d)/'out'
        out.mkdir(parents=True, exist_ok=True)
        path = Path(d)/'graph.json'
        build_graph(path)
        seed = graph.load(path)
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]; sock.close()
        # An empty temporary registry keeps the viewer on this graph only.
        env = {**os.environ, 'TG_REGISTRY': str(Path(d)/'registry.json')}
        proc = subprocess.Popen([sys.executable, str(ROOT/'tg'), '--file', str(path), 'serve', '--port', str(port)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        url = f'http://127.0.0.1:{port}'
        try:
            for _ in range(100):
                try: urllib.request.urlopen(url+'/api/status', timeout=1); break
                except OSError: time.sleep(.05)
            browser(out, 'open', url)
            browser(out, 'wait', '--text', 'Live · r'+str(seed['revision']))
            question = 'release-cadence'
            expected = json.load(urllib.request.urlopen(url+'/api/readiness?id='+question, timeout=5))
            browser(out, 'fill', '#search', question)
            browser(out, 'wait', '--fn', "document.querySelector('#results button') !== null")
            browser(out, 'click', '#results button')
            browser(out, 'wait', '--text', 'Readiness:')
            body = browser(out, 'get', 'text', '#detail')
            assert f"Readiness: {expected['readiness']} · Resolution: {expected['resolution']}" in body, body
            browser(out, 'find', 'role', 'button', 'click', '--name', 'Show affected dependencies')
            browser(out, 'wait', '--text', 'Declared dependency impact')
            browser(out, 'find', 'role', 'button', 'click', '--name', 'Inspect checks')
            browser(out, 'wait', '--text', 'Findings about this node')
            browser(out, 'screenshot', str(out/'readiness.png'))
            edits = [{'op': 'add', 'collection': 'nodes', 'id': 'ui-observability-fixture', 'value': {'type': 'question', 'status': 'open', 'text': 'SYNTHETIC: can the user see this new question?'}},
                     {'op': 'add', 'collection': 'edges', 'id': 'ui-fixture-about', 'value': {'type': 'about', 'from': 'ui-observability-fixture', 'to': 'owner'}}]
            (out/'edits.json').write_text(json.dumps(edits, indent=2)+'\n')
            tg(path, 'apply', str(out/'edits.json'), '--actor', 'browser-smoke', '--reason', 'Synthetic visual observability check', '--expect', str(seed['revision']))
            browser(out, 'wait', '--text', f"Live · r{seed['revision']+1}")
            browser(out, 'fill', '#search', 'ui-observability-fixture')
            browser(out, 'wait', '--fn', "document.querySelector('#results button')?.textContent.includes('ui-observability-fixture')")
            browser(out, 'click', '#results button')
            browser(out, 'wait', '--text', 'SYNTHETIC: can the user see this new question?')
            browser(out, 'screenshot', str(out/'live-change.png'))
            browser(out, 'click', '#history-button')
            browser(out, 'wait', '--text', 'Synthetic visual observability check')
            history = browser(out, 'get', 'text', '#activity-body')
            assert 'ui-observability-fixture' in history and 'ui-fixture-about' in history, history
            browser(out, 'screenshot', str(out/'change-history.png'))
            browser(out, 'click', '#theme'); browser(out, 'click', '#theme')
            browser(out, 'wait', '--fn', "document.documentElement.dataset.theme==='dark'")
            browser(out, 'screenshot', str(out/'dark-mode.png'))
            print('Browser smoke passed' + (f': {out}' if args.out else ''))
        finally:
            try: browser(out, 'close')
            except RuntimeError: pass
            proc.terminate(); proc.wait(timeout=10)
    return 0


if __name__ == '__main__':
    if not shutil.which('npx'): sys.exit('browser_smoke needs npx (Node.js) for agent-browser')
    sys.exit(main())
