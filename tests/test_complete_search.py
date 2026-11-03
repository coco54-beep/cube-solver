"""Resource caps must limit storage, never remove unexplored branches."""
import pytest
from solver.complete_search import deepen,Exhausted


@pytest.mark.parametrize('cache_limit',(0,1,100))
def test_search_can_take_a_temporarily_worse_route_with_a_full_cache(cache_limit):
    edges={'s':(('dead','a'),('detour','b')),'dead':(('s','back'),),
           'detour':(('middle','c'),),'middle':(('goal','d'),),'goal':()}
    h={'s':0,'dead':0,'detour':6,'middle':3,'goal':0}
    word=deepen('s',lambda s:() if s=='goal' else None,lambda s:edges[s],lambda s:h[s],cache_limit=cache_limit)
    assert word==('b','c','d')


def test_explicit_stack_has_no_python_recursion_depth_ceiling():
    word=deepen(0,lambda s:() if s==1500 else None,
                lambda s:((s+1,s+1),) if s<1500 else (),lambda s:1500-s,cache_limit=1)
    assert word==tuple(range(1,1501))


def test_exhaustion_is_a_graph_proof_and_not_a_search_quota():
    with pytest.raises(Exhausted):
        deepen(0,lambda s:None,lambda s:((1-s,'flip'),),lambda s:0,cache_limit=0)


def test_mid_search_cancellation_remains_prompt():
    calls=[0]
    def cancel():calls[0]+=1;return calls[0]>12
    with pytest.raises(InterruptedError):
        deepen(0,lambda s:None,lambda s:((s+1,'next'),),lambda s:0,cancel=cancel)
    assert calls[0]==13
