import copy
import unittest
from theorygraph.formalcheck import (compare_patterns, compare_graph, evaluate_authority,
                         evaluate_cardinality, evaluate_obligation, review_formalization, scope_overlap)

class FormalChecks(unittest.TestCase):
    def setUp(self):
        self.model={'scopes':{'all':{'members':['x','y']},'quick':{'members':['x']},'research':{'members':['y']}},
                    'role_disjoint':[['steward','orchestrator']]}
        self.only={'kind':'authority','modality':'only','role':'steward','operation':'choose','scope':'all'}
        self.may={**self.only,'modality':'may','role':'orchestrator'}
        self.slot={'subject_type':'Port','relation':'owners','target_type':'Service','direction':'out','identity_key':['host','number'],'count':'distinct'}
        self.exact={'kind':'cardinality','slot':self.slot,'min':1,'max':1,'scope':'all'}
        self.model['subjects']=[{'id':'p','type':'Port','scopes':['all']}]
    def compare(self,a,b): return compare_patterns(a,b,self.model)
    def event_trace(self,roles):
        return {'complete':True,'events':[{'id':'end','operation':'end-attempt','attempt':'a'},
            {'id':'choose','operation':'choose','attempt':'a','after':'end','actor':'person','actor_roles':roles}]}
    def test_missing_scope_pair_names_ids_and_remedy_without_inventing_overlap(self):
        p={**self.only,'scope':'undeclared-left'}
        q={**self.may,'scope':'undeclared-right'}
        outcome=self.compare(p,q)
        self.assertEqual(outcome['outcome'],'not-checked')
        self.assertEqual(outcome['missing_scopes'],['undeclared-left','undeclared-right'])
        self.assertIn('formal_model.scopes',outcome['reason'])
        self.assertIn('justified nonempty evidence',outcome['reason'])
        self.assertNotIn('witnesses',outcome)
        self.assertEqual(self.compare(q,p),outcome)
    def test_A01_steward_event(self):
        p={**self.only,'scope':'after_attempt_ended'}
        self.assertEqual(evaluate_authority(p,self.event_trace(['steward']))['outcome'],'satisfies')
    def test_A02_nonsteward_witness(self):
        r=evaluate_authority({**self.only,'scope':'after_attempt_ended'},self.event_trace(['orchestrator']))
        self.assertEqual(r['outcome'],'violates'); self.assertEqual(r['witnesses'],['choose'])
    def test_A03_permission_conflict(self):
        r=self.compare(self.only,self.may)
        self.assertEqual(r['outcome'],'policy-conflict'); self.assertEqual(r['witness']['operation'],'choose')
        self.model['role_disjoint']=[]
        self.assertEqual(self.compare(self.only,self.may)['outcome'],'role-overlap-unknown')
    def test_A04_dual_restrictions_vacuity(self):
        r=self.compare(self.only,{**self.may,'modality':'only'})
        self.assertEqual(r['outcome'],'no-inconsistency-established'); self.assertTrue(r['possible_overconstraint'])
    def test_A05_dual_roles(self):
        trace=self.event_trace(['steward','orchestrator'])
        for role in ['steward','orchestrator']:
            self.assertEqual(evaluate_authority({**self.only,'role':role},trace)['outcome'],'satisfies')
        self.model['role_disjoint']=[]
        self.assertFalse(self.compare(self.only,{**self.may,'modality':'only'})['possible_overconstraint'])
    def test_A06_scope_changes(self):
        self.assertEqual(self.compare(self.only,{**self.may,'scope':'quick'})['outcome'],'policy-conflict')
        self.assertEqual(self.compare({**self.only,'scope':'research'},{**self.may,'scope':'quick'})['outcome'],'no-overlap')
        m={'scopes':{'a':{'nonempty':True},'b':{}},'scope_subset':[['a','b']]}
        self.assertEqual(scope_overlap('a','b',m)['outcome'],'overlap')
        m['scope_subset'].append(['b','a'])
        self.assertEqual(scope_overlap('a','b',m)['outcome'],'schema-error')
    def test_A07_may_ask_not_must(self):
        ask={**self.may,'operation':'ask'}
        self.assertEqual(self.compare(ask,{**self.may,'operation':'end'})['outcome'],'independent')
        empty={'events': [], 'complete': True, 'complete_through_tick': 6}
        permission=evaluate_authority(ask,empty)
        self.assertEqual(permission['outcome'],'satisfies')
        self.assertTrue(permission['permission_only'])
        obligation={'kind':'bounded_obligation','trigger':'blocked','response':'ask',
                    'role':'orchestrator','within_ticks':5}
        empty['events']=[{'id':'b','operation':'blocked','tick':0}]
        required=evaluate_obligation(obligation,empty)
        self.assertEqual(required['outcome'],'violates')
        self.assertEqual(required['witnesses'][0]['event'],'b')

    def test_only_and_never_same_role_exposes_overconstraint(self):
        never={**self.only,'modality':'never'}
        for a,b in [(self.only,never),(never,self.only)]:
            checked=self.compare(a,b)
            self.assertEqual(checked['outcome'],'no-inconsistency-established')
            self.assertTrue(checked['possible_overconstraint'])
        self.assertEqual(self.compare(self.only,{**never,'role':'orchestrator'})['outcome'],'compatible')

    def test_A08_withdrawal_filters_current(self):
        g={'revision':1,'formal_model':self.model,'nodes':{'a':{'type':'claim','status':'accepted','pattern':self.only},'b':{'type':'claim','status':'accepted','pattern':self.may}}}
        receipt=compare_graph(g)
        self.assertEqual(receipt[0]['code'],'policy-conflict')
        g['nodes']['b']['status']='withdrawn';g['revision']=2
        before=copy.deepcopy(g)
        self.assertEqual(compare_graph(g),[]); self.assertEqual(g,before)
        self.assertEqual(receipt[0]['computed_revision'],1)
    def test_A09_must_never(self):
        r=self.compare({**self.may,'modality':'must'},{**self.may,'modality':'never'})
        self.assertEqual(r['outcome'],'policy-conflict')
    def test_A10_may_must(self):
        self.assertEqual(self.compare(self.may,{**self.may,'modality':'must'})['outcome'],'compatible')
    def test_A11_may_without_event(self):
        self.assertEqual(evaluate_authority(self.may,{'events':[],'complete':True})['outcome'],'satisfies')
    def test_A12_unbounded_eventuality(self):
        p={'kind':'bounded_obligation','trigger':'complete','response':'consider'}
        self.assertEqual(evaluate_obligation(p,{'events':[{'id':'c','operation':'complete','tick':0}],'complete_through_tick':100})['outcome'],'insufficient-information')
    def test_A13_expired_obligation(self):
        p={'kind':'bounded_obligation','trigger':'complete','response':'consider','role':'steward','within_ticks':5}
        t={'events':[{'id':'c','operation':'complete','tick':0}],'complete_through_tick':6}
        r=evaluate_obligation(p,t)
        self.assertEqual(r['outcome'],'violates');self.assertEqual(r['witnesses'],[{'event':'c','deadline':5,'complete_through_tick':6}])
        t['events'].append({'id':'r','operation':'consider','tick':4,'responds_to':'c','actor_roles':['steward']})
        self.assertEqual(evaluate_obligation(p,t)['outcome'],'satisfies')
        t['events'][-1]['responds_to']='different'
        self.assertEqual(evaluate_obligation(p,t)['outcome'],'violates')
        t['complete_through_tick']=3
        self.assertEqual(evaluate_obligation(p,t)['outcome'],'insufficient-information')
    def test_A14_unknown_overlap(self):
        self.model['scopes'].update({'exceptional':{},'repair':{}})
        self.assertEqual(self.compare({**self.only,'scope':'exceptional'},{**self.may,'scope':'repair'})['outcome'],'overlap-unknown')
    def test_A15_extraction_not_acceptance(self):
        source={**self.only,'scope':'failure'}
        broad={**source,'scope':'all','operation':'insert'}
        original=copy.deepcopy(source)
        r=review_formalization(broad,source)
        self.assertEqual(r['outcome'],'extraction-review'); self.assertEqual(r['fields'],['operation','scope'])
        self.assertEqual(r['pattern_standing'],'proposed');self.assertEqual(source,original)
    def test_A16_free_text_scope(self):
        self.assertEqual(evaluate_authority({**self.only,'scope':'when things seem bad'},self.event_trace(['steward']))['outcome'],'not-checked')
    def test_C01_exact_one_atmost_two(self):
        r=self.compare(self.exact,{**self.exact,'min':0,'max':2})
        self.assertEqual(r['outcome'],'compatible');self.assertEqual(r['intersection'],[1,1])
    def test_C02_exact_one_atleast_two(self):
        r=self.compare(self.exact,{**self.exact,'min':2,'max':None})
        self.assertEqual(r['outcome'],'cardinality-conflict');self.assertEqual(r['witnesses'][0]['id'],'p')
    def test_C03_exact_one_atleast_one(self):
        self.assertEqual(self.compare(self.exact,{**self.exact,'max':None})['intersection'],[1,1])
    def test_C04_empty_subject_domain(self):
        self.model['subjects']=[]
        r=self.compare(self.exact,{**self.exact,'min':2,'max':None})
        self.assertEqual(r['outcome'],'no-inconsistency-established'); self.assertTrue(r['conditional_unsatisfiability'])
    def reports(self):
        return [{'subject':{'host':'A','number':8080},'target':'a','sources':['log1']},
                {'subject':{'host':'B','number':8080},'target':'b','sources':['log2']}]
    def test_C05_host_scoped_identity(self):
        unknown={**self.exact,'slot':{**self.slot,'identity_key':None}}
        self.assertEqual(evaluate_cardinality(unknown,self.reports(),True)['reason'],'identity-gap')
        r=evaluate_cardinality(self.exact,self.reports(),True)
        self.assertEqual(r['outcome'],'satisfies');self.assertEqual(len(r['subjects']),2)
        self.assertEqual([s['distinct_count'] for s in r['subjects']],[1,1])
    def test_C06_unknown_identity(self):
        p={**self.exact,'slot':{**self.slot,'identity_key':None}}
        r=evaluate_cardinality(p,self.reports(),True)
        self.assertEqual(r['outcome'],'insufficient-information');self.assertIn('identity',r['question'])
    def test_C07_distinct_not_reports(self):
        reports=[self.reports()[0],{**self.reports()[0],'sources':['log2']}]
        r=evaluate_cardinality(self.exact,reports,True)
        self.assertEqual(r['outcome'],'satisfies');self.assertEqual(r['subjects'][0]['distinct_count'],1)
        self.assertEqual(r['subjects'][0]['sources'],['log1','log2'])
    def test_C08_open_world(self):
        reports=[{'subject':{'host':'A','number':8080}}]
        self.assertEqual(evaluate_cardinality(self.exact,reports,False)['outcome'],'insufficient-information')
        self.assertEqual(evaluate_cardinality(self.exact,reports,True)['outcome'],'violates')
    def test_known_violation_dominates_missing_evidence(self):
        t=self.event_trace(['orchestrator']);t['events'].append({'id':'unknown','operation':'choose'})
        r=evaluate_authority({**self.only,'scope':'after_attempt_ended'},t)
        self.assertEqual(r['outcome'],'violates');self.assertTrue(r['diagnostics'])
    def test_unknown_scope_identity_and_invalid_bounds(self):
        self.assertEqual(self.compare({**self.exact,'scope':'undefined'},self.exact)['outcome'],'not-checked')
        self.assertEqual(self.compare({**self.exact,'min':3,'max':2},self.exact)['outcome'],'schema-error')
        self.assertEqual(self.compare({**self.exact,'slot':{**self.slot,'identity_key':None}},self.exact)['outcome'],'insufficient-information')

    def test_invalid_input_and_boolean_ticks(self):
        self.assertEqual(compare_patterns([],{},self.model)['outcome'],'schema-error')
        p={'kind':'bounded_obligation','trigger':'complete','response':'consider','within_ticks':5}
        self.assertEqual(evaluate_obligation(p,{'events':[],'complete_through_tick':True})['outcome'],'schema-error')
        self.assertEqual(evaluate_obligation(p,{'events':[{'id':'c','operation':'complete','tick':True}],'complete_through_tick':6})['outcome'],'insufficient-information')
    def test_event_identity_ambiguity(self):
        t=self.event_trace(['steward']);t['events'][-1]['id']='end'
        self.assertEqual(evaluate_authority(self.only,t)['outcome'],'insufficient-information')
        t=self.event_trace(['steward']);del t['events'][-1]['actor']
        self.assertEqual(evaluate_authority(self.only,t)['outcome'],'insufficient-information')
    def test_formalization_standing_visible(self):
        g={'nodes':{'a':{'type':'claim','status':'accepted','pattern':self.only,'meta':{'pattern_standing':'proposed'}},'b':{'type':'claim','status':'accepted','pattern':self.may}},'formal_model':self.model}
        r=compare_graph(g)[0]
        self.assertEqual(r['pattern_standing']['a'],'proposed');self.assertIn('prose',r['formalization_scope'])
    def test_contradictory_model_assumptions(self):
        self.model['actors']={'a':{'roles':['steward','orchestrator']}}
        self.assertEqual(self.compare(self.only,self.may)['outcome'],'schema-error')

if __name__=='__main__': unittest.main()
