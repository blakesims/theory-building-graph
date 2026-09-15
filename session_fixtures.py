"""Authored conversational fixture operations, never inferred from live user text."""
import copy
from session_evaluation import FACTS, LINKS

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
