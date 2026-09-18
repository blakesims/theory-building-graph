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


def project_name(graph_path, preferred=None):
    reg = read_registry(); target = Path(graph_path).resolve()
    if preferred and preferred in reg['projects'] and Path(reg['projects'][preferred]).resolve() == target:
        return preferred
    return next((name for name, path in reg['projects'].items() if Path(path).resolve() == target), None)


def autosync(graph_path, project=None):
    name = project_name(graph_path, project)
    return read_registry().get('settings', {}).get(name, {}).get('autosync', False) is True


def configure_autosync(graph_path, enabled, project=None):
    name = project_name(graph_path, project)
    if name is None: raise ProjectError('Autosync requires a registered project. Use tg register NAME PATH first.')
    reg = read_registry()
    reg.setdefault('settings', {}).setdefault(name, {})['autosync'] = enabled
    write_registry(reg)
    return {'project': name, 'autosync': 'on' if enabled else 'off'}


def git_root(path):
    r = subprocess.run(['git', '-C', str(Path(path).resolve().parent), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def sync(graph_path, message=None):
    """Commit the graph file if it changed, pull with rebase when behind, push. Never forces.

    Only the graph is staged and committed. Autostash preserves unrelated dirty
    work during rebase. On conflict the local commit is kept for hand merging.
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
    # Pull only when the upstream has commits we lack: a no-op rebase still trips
    # repositories whose hooks refuse any rebase of their main branch.
    git('fetch')
    behind = git('rev-list', '--count', 'HEAD..@{u}', check=False)
    r = git('pull', '--rebase', '--autostash', check=False) if behind.returncode or behind.stdout.strip() != '0' else behind
    if r.returncode:
        conflicts = git('diff', '--name-only', '--diff-filter=U', check=False).stdout.strip()
        git('rebase', '--abort', check=False)
        raise ProjectError(f'Pull/rebase failed; local commit kept. Conflicting files: {conflicts or "none reported"}. Repository: {root}, graph: {rel}. '+(r.stderr or r.stdout).strip()[-800:])
    conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.strip()
    if conflicts:
        raise ProjectError(f'Autostash restore conflicted; not pushed. Conflicting files: {conflicts}. Repository: {root}. Resolve the working tree before retrying sync.')
    git('push')
    return {'repository': root, 'graph': rel, 'committed': committed, 'message': message if committed else None, 'steps': steps}
