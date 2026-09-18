"""Independent finite-domain oracle checks for the small comparison fragment."""
import copy
import itertools
import unittest
from theorygraph import formalcheck as f

class MetamorphicChecks(unittest.TestCase):
    def test_cardinality_against_enumerated_domain(self):
        slot={'subject_type':'Port','relation':'owns','target_type':'Service','direction':'out','identity_key':['host','number'],'count':'distinct'}
        model={'scopes':{'all':{'members':['witness']}},'subjects':[{'id':'p','type':'Port','scopes':['all']}]}
        bounds=[(lo,hi) for lo in range(5) for hi in range(lo,5)]
        for (lo,hi),(other_lo,other_hi) in itertools.product(bounds,repeat=2):
            a={'kind':'cardinality','slot':slot,'scope':'all','min':lo,'max':hi}
            b={**a,'min':other_lo,'max':other_hi}
            valid=[n for n in range(5) if lo<=n<=hi and other_lo<=n<=other_hi]
            expected='compatible' if valid else 'cardinality-conflict'
            with self.subTest(a=(lo,hi),b=(other_lo,other_hi)):
                self.assertEqual(f.compare_patterns(a,b,model)['outcome'],expected)
                self.assertEqual(f.compare_patterns(b,a,model)['outcome'],expected)

    def test_authority_order_and_identity_renaming(self):
        model={'scopes':{'scope':{'members':['event']}},'role_disjoint':[['r1','r2']]}
        policies=[{'kind':'authority','modality':m,'role':r,'operation':'choose','scope':'scope'} for m in ['only','may','must','never'] for r in ['r1','r2']]
        for a,b in itertools.product(policies,repeat=2):
            first=f.compare_patterns(a,b,model)
            self.assertEqual(first['outcome'],f.compare_patterns(b,a,model)['outcome'])
            renamed=copy.deepcopy(model);renamed['role_disjoint']=[['alpha','beta']]
            name={'r1':'alpha','r2':'beta'}
            self.assertEqual(first['outcome'],f.compare_patterns({**a,'role':name[a['role']]},{**b,'role':name[b['role']]},renamed)['outcome'])

    def test_duplicate_cardinality_report_cannot_increase_distinct_count(self):
        p={'kind':'cardinality','scope':'all','min':1,'max':1,'slot':{'identity_key':['host','number'],'count':'distinct'}}
        report={'subject':{'host':'example','number':8767},'target':'server'}
        for copies in [1,2,20]:
            actual=f.evaluate_cardinality(p,[copy.deepcopy(report) for _ in range(copies)],complete=True)
            self.assertEqual(actual['outcome'],'satisfies')
            self.assertEqual(actual['subjects'][0]['distinct_count'],1)

if __name__=='__main__':unittest.main()
