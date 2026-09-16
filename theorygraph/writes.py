"""Typed authoring commands compile to ordinary audited graph operations."""
import copy
import fcntl
import json
import os
from pathlib import Path
from . import projects

TYPED = {'claim', 'question', 'entity', 'operation', 'source', 'withdraw', 'answer', 'edge', 'set'}
KINDS = ('verbatim', 'paraphrase', 'session-paraphrase', 'assistant-proposal')


def audit_arguments(parser):
    parser.add_argument('--reason', required=True)
    parser.add_argument('--actor', default=os.environ.get('TG_ACTOR') or 'assistant')
    parser.add_argument('--dry-run', action='store_true')


def parsers(sub):
    for kind in ('claim', 'question', 'entity', 'operation', 'source'):
        parent = sub.add_parser(kind, help=f'Write a {kind}')
        p = parent.add_subparsers(dest='action', required=True).add_parser('add')
        p.add_argument('id'); p.add_argument('text'); p.add_argument('--title')
        p.add_argument('--author')
        p.add_argument('--kind', choices=KINDS if kind != 'source' else KINDS[:2],
                       required=kind == 'source', default=None)
        if kind in ('claim', 'question'):
            p.add_argument('--about', nargs='+', action='extend', default=[])
            p.add_argument('--governs', nargs='+', action='extend', default=[])
            p.add_argument('--depends-on', nargs='+', action='extend', default=[])
        if kind == 'claim':
            p.add_argument('--status', choices=('accepted', 'proposed', 'withdrawn'), default='proposed')
            p.add_argument('--source'); p.add_argument('--answers')
            p.add_argument('--coverage', choices=('full', 'partial'), default='full')
            p.add_argument('--revises'); p.add_argument('--withdraw-old', action='store_true')
            p.add_argument('--raises', nargs='+', action='extend', default=[])
            p.add_argument('--supports', nargs='+', action='extend', default=[])
        elif kind == 'question': p.add_argument('--raised-by')
        elif kind == 'entity': p.add_argument('--alias', nargs='+', action='extend', default=[])
        elif kind == 'operation': p.add_argument('--acts-on', nargs='+', action='extend', default=[])
        audit_arguments(p)
    p = sub.add_parser('withdraw', help='Withdraw a claim, retaining history')
    p.add_argument('id'); p.add_argument('--superseded-by'); audit_arguments(p)
    p = sub.add_parser('answer', help='Link a claim and declare accepted full coverage answered')
    p.add_argument('id'); p.add_argument('--with', dest='claim', required=True)
    p.add_argument('--coverage', choices=('full', 'partial'), default='full'); audit_arguments(p)
    p = sub.add_parser('edge').add_subparsers(dest='action', required=True).add_parser('add')
    p.add_argument('source'); p.add_argument('relation'); p.add_argument('target'); audit_arguments(p)
    p = sub.add_parser('set', help='Change one node field')
    p.add_argument('id'); group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--status'); group.add_argument('--text'); audit_arguments(p)


def build(g, a):
    from .graph import GraphError
    work = copy.deepcopy(g)
    ops = []
    template = json.loads((Path(__file__).parent / 'template.json').read_text())

    def emit(action, collection, key, value):
        if action == 'add' and key in work[collection]:
            raise GraphError(f'Already exists: {collection}/{key}')
        ops.append({'op': action, 'collection': collection, 'id': key, 'value': value})
        old = work[collection].get(key, {})
        work[collection][key] = {**old, **value}
        if 'meta' in value:
            work[collection][key]['meta'] = {**old.get('meta', {}), **value['meta']}

    def require(nid, kinds=None):
        if nid not in work['nodes']: raise GraphError('Unknown node: ' + nid)
        n = work['nodes'][nid]
        if kinds and n['type'] not in kinds:
            raise GraphError(f'{nid} must be {" or ".join(kinds)}, not {n["type"]}')
        return n

    def link(source, kind, target, **extra):
        require(source); require(target)
        if kind not in work['edge_types']:
            if kind not in template['edge_types']: raise GraphError('Unknown relation: ' + kind)
            emit('add', 'edge_types', kind, template['edge_types'][kind])
        if kind == 'answers':
            require(source, ('claim',)); require(target, ('question',))
            extra.setdefault('coverage', 'full')
        for eid, e in work['edges'].items():
            if (e['from'], e['type'], e['to']) == (source, kind, target):
                if extra: emit('update', 'edges', eid, extra)
                return
        base = f'{source}-{kind}-{target}'; eid = base; suffix = 2
        while eid in work['edges']:
            eid = f'{base}-{suffix}'; suffix += 1
        emit('add', 'edges', eid, {'from': source, 'type': kind, 'to': target, **extra})

    def answer(question, claim, coverage):
        q = require(question, ('question',)); n = require(claim, ('claim',))
        link(claim, 'answers', question, coverage=coverage)
        if coverage == 'full' and n.get('status') == 'accepted':
            if n.get('meta', {}).get('review_state') == 'historical':
                raise GraphError('Cannot answer with historical claim: ' + claim)
            if q.get('status') != 'answered': emit('update', 'nodes', question, {'status': 'answered'})

    def withdraw(nid, successor=None):
        require(nid, ('claim',))
        if successor:
            require(successor, ('claim',))
            if successor == nid: raise GraphError('A claim cannot supersede itself: ' + nid)
        meta = {'review_state': 'historical'}
        if successor: meta['superseded_by'] = successor
        emit('update', 'nodes', nid, {'status': 'withdrawn', 'meta': meta})

    if a.cmd in ('claim', 'question', 'entity', 'operation', 'source'):
        if a.cmd in ('claim', 'question') and not (a.about or a.governs):
            raise GraphError(f'{a.cmd} {a.id} requires --about or --governs')
        if a.cmd == 'claim' and a.withdraw_old and not a.revises:
            raise GraphError('--withdraw-old requires --revises OLD')
        if a.cmd not in work['node_types']: raise GraphError('Unknown node type: ' + a.cmd)
        status = getattr(a, 'status', None) or {'question': 'open', 'source': 'recorded', 'entity': 'defined', 'operation': 'defined'}.get(a.cmd)
        states = work['node_types'][a.cmd].get('states')
        if a.cmd in ('entity', 'operation') and states and status not in states:
            status = 'declared' if 'declared' in states else states[0]
        meta = {'review_state': 'current', 'title': a.title or a.id.replace('-', ' ').replace('_', ' '),
                'author': a.author or ('speaker unknown' if a.cmd == 'source' else a.actor),
                'source_kind': a.kind or 'assistant-proposal'}
        if a.cmd == 'entity' and a.alias: meta['aliases'] = list(dict.fromkeys(a.alias))
        emit('add', 'nodes', a.id, {'type': a.cmd, 'status': status, 'text': a.text, 'meta': meta})
        if a.cmd in ('claim', 'question'):
            for nid in a.about:
                require(nid, ('entity', 'operation')); link(a.id, 'about', nid)
            for nid in a.governs:
                require(nid, ('operation',)); link(a.id, 'governs', nid)
        if a.cmd in ('claim', 'question'):
            for nid in a.depends_on:
                require(nid); link(a.id, 'depends-on', nid)
        if a.cmd == 'operation':
            for nid in a.acts_on:
                require(nid, ('entity',)); link(a.id, 'acts-on', nid)
        if a.cmd == 'question' and a.raised_by:
            require(a.raised_by, ('claim',)); link(a.raised_by, 'raises', a.id)
        if a.cmd == 'claim':
            if a.source:
                require(a.source, ('source',)); link(a.id, 'extracted-from', a.source)
            if a.revises:
                require(a.revises, ('claim',)); link(a.id, 'revises', a.revises)
                if a.withdraw_old:
                    withdraw(a.revises, a.id)
                    for eid, e in list(work['edges'].items()):
                        if e['from'] == a.revises and e['type'] == 'answers':
                            emit('update', 'edges', eid, {'from': a.id})
            if a.answers: answer(a.answers, a.id, a.coverage)
            for nid in a.raises:
                require(nid, ('question',)); link(a.id, 'raises', nid)
            for nid in a.supports:
                require(nid, ('claim',)); link(a.id, 'supports', nid)
        summary = f'added {a.cmd} {a.id}'
    elif a.cmd == 'withdraw':
        withdraw(a.id, a.superseded_by); summary = 'withdrew ' + a.id
    elif a.cmd == 'answer':
        answer(a.id, a.claim, a.coverage); summary = 'answered ' + a.id if work['nodes'][a.id].get('status') == 'answered' else 'linked answer to ' + a.id
    elif a.cmd == 'edge':
        link(a.source, a.relation, a.target); summary = f'added edge {a.source} {a.relation} {a.target}'
    else:
        require(a.id)
        emit('update', 'nodes', a.id, {'status': a.status} if a.status is not None else {'text': a.text})
        summary = 'updated ' + a.id
    if not ops: raise GraphError('No change: relation already exists')
    return ops, summary


def synchronize(path, message=None):
    with open(str(path) + '.write.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return projects.sync(path, message)


def sync_result(path, reason, result, project=None, no_sync=False):
    if projects.autosync(path, project):
        if no_sync:
            # The write is saved; the operator syncs the whole burst with one `tg sync`.
            result['sync_skipped'] = True
            return result
        try:
            synced = projects.sync(path, reason)
            result['sync'] = {'committed': synced['committed'], 'pushed': True}
        except projects.ProjectError as exc:
            raise projects.ProjectError(f'r{result["revision"]} saved locally; sync failed: {exc}') from exc
    return result


def evaluate_and_save(path, a, project=None):
    from . import graph, tracecheck
    with open(str(path) + '.write.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        g = graph.load(path)
        checked = tracecheck.evaluate(g, graph.resolve(g, a.claim), graph.resolve(g, a.trace))
        result = graph.save_evaluation(path, g, checked, a.save or None, a.actor, a.reason)
        result.update(revision=result['saved_revision'], summary='saved evaluation ' + result['saved_as'])
        return sync_result(path, a.reason, result, project, getattr(a, 'no_sync', False))


def execute(path, a, project=None):
    """Serialize CLI writers through compile/apply/sync; apply retains its own lock."""
    from . import graph

    def run():
        g = graph.load(path)
        expected = getattr(a, 'expect', None)
        if expected is None: expected = g['revision']
        if a.cmd in TYPED: ops, summary = build(g, a)
        elif a.cmd == 'reviewed':
            for nid in a.ids:
                if nid not in g['nodes']: raise graph.GraphError('Unknown node: ' + nid)
            ops = [{'op': 'update', 'collection': 'nodes', 'id': nid,
                    'value': {'meta': {'review_state': 'current', 'review_reason': a.reason}}}
                   for nid in dict.fromkeys(a.ids)]
            summary = 'reviewed ' + ', '.join(dict.fromkeys(a.ids))
        else:
            import sys
            ops = json.load(sys.stdin) if a.operations == '-' else json.loads(Path(a.operations).read_text())
            summary = 'applied batch'
        if a.dry_run: return graph.dry_run(path, ops, a.actor, a.reason, expected)
        result = graph.apply(path, ops, a.actor, a.reason, expected)
        result['summary'] = summary
        if a.cmd == 'reviewed': result['reviewed'] = list(dict.fromkeys(a.ids))
        return sync_result(path, a.reason, result, project, getattr(a, 'no_sync', False))

    if a.dry_run: return run()
    with open(str(path) + '.write.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return run()
