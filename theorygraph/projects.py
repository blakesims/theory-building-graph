"""Project registry and graph-file resolution.

A project is one graph.json. The registry maps a short name to that file so
`tg -p NAME ...` works from any directory. Resolution order for a command:

1. --file PATH
2. -p/--project NAME (registry)
3. $TG_PROJECT (registry name)
4. nearest ancestor of the working directory containing theory/graph.json or graph.json
5. the registry default project
"""
import json, os, shutil, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY = Path(os.environ.get('TG_REGISTRY') or Path.home()/'.config'/'theory-graph'/'projects.json')
DISCOVER = ('theory/graph.json', 'graph.json')


class ProjectError(Exception): pass


def read_registry():
    if not REGISTRY.exists(): return {'default': None, 'projects': {}}
    data = json.loads(REGISTRY.read_text())
    data.setdefault('default', None); data.setdefault('projects', {})
    return data


def write_registry(data):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True)+'\n'); os.replace(tmp, REGISTRY)


def lookup(name):
    reg = read_registry()
    if name not in reg['projects']:
        known = ', '.join(sorted(reg['projects'])) or 'none registered'
        raise ProjectError(f'Unknown project {name!r} (known: {known}). Use `tg new NAME` or `tg register NAME PATH`.')
    return Path(reg['projects'][name])


def discover(start=None):
    d = Path(start or os.getcwd()).resolve()
    for directory in (d, *d.parents):
        for rel in DISCOVER:
            candidate = directory/rel
            if candidate.is_file(): return candidate
    return None


def resolve(file=None, project=None):
    """Return (path, how) where how names the rule that chose it."""
    if file: return Path(file), 'file'
    if project: return lookup(project), 'project'
    env = os.environ.get('TG_PROJECT')
    if env: return lookup(env), 'env'
    found = discover()
    if found: return found, 'discovered'
    reg = read_registry()
    if reg['default']: return lookup(reg['default']), 'default'
    raise ProjectError('No graph selected. Pass --file, -p NAME, set TG_PROJECT, run inside a directory with theory/graph.json, or `tg use NAME`.')


def register(name, path, make_default=False):
    path = Path(path).resolve()
    if not path.is_file(): raise ProjectError(f'{path} is not a file')
    reg = read_registry(); reg['projects'][name] = str(path)
    if make_default or not reg['default']: reg['default'] = name
    write_registry(reg); return reg


def use(name):
    reg = read_registry()
    if name not in reg['projects']: raise ProjectError(f'Unknown project {name!r}')
    reg['default'] = name; write_registry(reg); return reg


def new(name, directory=None, register_project=True):
    """Create DIRECTORY/graph.json from the template and register it.

    Default directory: theory/ under the working directory when run inside a
    code repository, so the theory travels with the program it describes.
    """
    if not name or any(c in name for c in ' /\\'): raise ProjectError('Project name must be a single token without spaces or slashes')
    directory = Path(directory) if directory else Path.cwd()/'theory'
    target = directory/'graph.json'
    if target.exists(): raise ProjectError(f'{target} already exists')
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE/'template.json', target)
    if register_project: register(name, target)
    return target


def listing():
    reg = read_registry()
    rows = []
    for name, path in sorted(reg['projects'].items()):
        p = Path(path); info = {'name': name, 'path': path, 'exists': p.is_file(), 'default': name == reg['default']}
        if p.is_file():
            try:
                g = json.loads(p.read_text()); info['revision'] = g.get('revision'); info['nodes'] = len(g.get('nodes', {}))
            except (OSError, ValueError): info['error'] = 'unreadable'
        rows.append(info)
    return {'registry': str(REGISTRY), 'default': reg['default'], 'projects': rows}


def where(graph_path, selected_by, project=None):
    graph_path = Path(graph_path).resolve(); reg = read_registry()
    name = (project or os.environ.get('TG_PROJECT')) if selected_by in ('project', 'env') else (reg['default'] if selected_by == 'default' else None)
    if name is None: name = next((n for n, p in reg['projects'].items() if Path(p).resolve() == graph_path), None)
    return {'engine': str(HERE.parent), 'registry': str(REGISTRY), 'project': name, 'graph': str(graph_path), 'selected_by': selected_by, 'git_root': git_root(graph_path)}


def git_root(path):
    r = subprocess.run(['git', '-C', str(Path(path).resolve().parent), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def sync(graph_path, message=None):
    """Commit the graph file if it changed, pull with rebase, push. Never forces.

    The local commit happens first because a rebase refuses a dirty tree; on a
    conflict the rebase is aborted and the local commit is kept for hand merging.
    """
    graph_path = Path(graph_path).resolve(); root = git_root(graph_path)
    if not root: raise ProjectError(f'{graph_path} is not inside a git repository')
    steps = []
    def git(*args, check=True):
        r = subprocess.run(['git', '-C', root, *args], capture_output=True, text=True)
        steps.append({'command': 'git '+' '.join(args), 'exit_code': r.returncode, 'output': (r.stdout+r.stderr).strip()[-2000:]})
        if check and r.returncode: raise ProjectError(f'git {args[0]} failed: '+(r.stderr or r.stdout).strip())
        return r
    rel = str(graph_path.relative_to(Path(root).resolve()))
    committed = None
    if git('status', '--porcelain', '--', rel).stdout.strip():
        if message is None:
            try: changes = json.loads(graph_path.read_text()).get('changes', []); message = changes[-1]['reason'] if changes else f'Update {rel}'
            except (OSError, ValueError, KeyError, TypeError): message = f'Update {rel}'
        git('add', '--', rel); git('commit', '-q', '-m', message, '--', rel)
        committed = git('rev-parse', '--short', 'HEAD').stdout.strip()
    r = git('pull', '--rebase', check=False)
    if r.returncode:
        git('rebase', '--abort', check=False)
        raise ProjectError(f'Rebase conflict; aborted, local commit kept. Resolve by hand in {root} (graph file: {rel}). Output: '+(r.stderr or r.stdout).strip()[-800:])
    git('push')
    return {'repository': root, 'graph': rel, 'committed': committed, 'message': message if committed else None, 'steps': steps}
