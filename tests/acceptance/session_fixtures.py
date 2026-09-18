"""Authored conversational fixture operations, never inferred from live user text."""

FACTS=[
 {'id':'source-1','type':'source','text':'Session paraphrase: Blake initially allowed operator-approved orchestrator replacement to avoid a relay when the orchestrator already had the context.','status':'recorded','source_kind':'session-paraphrase'},
 {'id':'source-2','type':'source','text':'Session paraphrase: Blake later chose the simpler rule: steward always chooses the work. Orchestrator can ask keep trying versus mark failed and let steward decide next.','status':'recorded','source_kind':'session-paraphrase'},
 {'id':'source-3','type':'source','text':'Only summaries of M1688 and M1689 are supplied. M1688 describes repeated useful reviews without an effective ruling. M1689 describes planning a proposed solution instead of reassessing the original performance concern. The primary postmortems are unavailable in this fixture.','status':'recorded','source_kind':'summary'},
 {'id':'steward-role','type':'entity','text':'Steward is the role responsible for selecting and sequencing work for a continuing intention.','status':'declared'},
 {'id':'choose-next-work','type':'operation','text':'Decide which subsequent work should pursue the intention. This decision is distinct from mechanically inserting a record.','status':'declared'},
 {'id':'replacement-exception','type':'claim','text':'Operator-approved orchestrator replacement can bypass steward.','status':'withdrawn','review_state':'historical','sources':['source-1'],'rationale':'Avoid a relay when the orchestrator has context; later rejected in favor of one owner of next-work choice.'},
 {'id':'atomic-replacement','type':'claim','text':'Orchestrator replacement is atomic archive/add and does not wake steward until new work completes.','status':'withdrawn','review_state':'historical','sources':['source-1','source-2'],'rationale':'An explored exception, retired when steward always choosing was selected.'},
 {'id':'steward-next-work','type':'claim','text':'Steward always chooses next work after a failed attempt.','status':'accepted','review_state':'current','sources':['source-2'],'rationale':'Keep a clean responsibility boundary; orchestrator may end a failed attempt and return it to steward.'},
 {'id':'consultation','type':'question','text':'Must the orchestrator consult the operator before ending degraded work, or may it end autonomously within a configured threshold?','status':'open','review_state':'current','sources':['source-2'],'rationale':'May ask does not establish mandatory consultation. This is not settled by next-work ownership.'},
 {'id':'cancellation','type':'question','text':'Does every arbitrary cancellation wake steward, beyond the agreed failed terminal result?','status':'open','review_state':'current','sources':['source-2']},
 {'id':'concern-persists','type':'claim','text':'Ending a failed record attempt does not itself satisfy or withdraw the underlying intention.','status':'accepted','review_state':'current','sources':['source-2']},
]
LINKS=[
 {'from':'steward-next-work','type':'about','to':'steward-role'},
 {'from':'steward-next-work','type':'governs','to':'choose-next-work'},
 {'from':'steward-next-work','type':'revises','to':'replacement-exception'},
 {'from':'steward-next-work','type':'revises','to':'atomic-replacement'},
 {'from':'replacement-exception','type':'governs','to':'choose-next-work'},
]

def base_graph():
    nodes={}
    for fact in FACTS:
        n={'type':fact['type'],'text':fact['text'],'status':fact['status'],'meta':{k:v for k,v in fact.items() if k not in ('id','type','text','status')}}
        if fact.get('review_state'):n['meta']['review_state']=fact['review_state']
        nodes[fact['id']]=n
    edges={f'link-{i}':dict(e) for i,e in enumerate(LINKS)}
    for fact in FACTS:
        for j,source in enumerate(fact.get('sources',[])):
            edges[f'source-{fact["id"]}-{j}']={'from':fact['id'],'type':'extracted-from','to':source}
    return {'version':1,'revision':0,'nodes':nodes,'edges':edges,'changes':[],
            'node_types':{k:{} for k in ('claim','question','entity','operation','source','extraction','trace')},
            'edge_types':{k:{} for k in ('about','governs','revises','answers','extracted-from','potential-conflict','depends-on')}}

def update(i,**value):return {'op':'update','collection':'nodes','id':i,'value':value}
def add(i,**value):return {'op':'add','collection':'nodes','id':i,'value':value}

def replacement_session():
    g=base_graph()
    g['nodes']['steward-next-work']['text']='Steward normally chooses work; operator-approved orchestrator replacement is an exception.'
    for key in ('replacement-exception','atomic-replacement'):
        g['nodes'][key]['status']='proposed';g['nodes'][key]['meta']['review_state']='current'
    g['nodes']['replacement-exception']['status']='accepted'
    g['nodes']['replacement-question']={'type':'question','text':'Should replacement bypass steward?','status':'open'}
    # Final decision's revision edges do not exist before it is chosen.
    g['edges']={i:e for i,e in g['edges'].items() if e['type']!='revises'}
    return g,[
      {'source':'User proposes atomic replacement without waking steward.','ops':[update('atomic-replacement',status='proposed',meta={'rationale':'Avoid relaying context; proposal only.'})]},
      {'source':'User considers always returning failed work; has not yet chosen.','ops':[add('return-proposal',type='claim',text='Always return failed work to steward for choosing next.',status='proposed',meta={'author':'assistant','sources':['source-2']})]},
      {'source':'User explicitly chooses steward always selects next work.','ops':[
        update('steward-next-work',text='Steward always chooses next work after a failed attempt.',status='accepted',meta={'review_state':'current','rationale':'User chose simpler responsibility boundary.','sources':['source-2']}),
        update('replacement-exception',status='withdrawn',meta={'review_state':'historical','rationale':'Retired in favor of steward choosing all subsequent work.'}),
        update('atomic-replacement',status='withdrawn',meta={'review_state':'historical','rationale':'Retired with replacement bypass.'}),
        update('return-proposal',status='withdrawn',meta={'review_state':'historical','rationale':'Consolidated into accepted steward-next-work.'}),
        update('replacement-question',status='retired',meta={'review_state':'historical','rationale':'Answered by steward-next-work.'}),
        {'op':'add','collection':'edges','id':'revision-exception','value':{'from':'steward-next-work','to':'replacement-exception','type':'revises'}},
        {'op':'add','collection':'edges','id':'revision-atomic','value':{'from':'steward-next-work','to':'atomic-replacement','type':'revises'}}
      ]}]
