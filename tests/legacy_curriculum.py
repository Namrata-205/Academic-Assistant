"""Frozen v1 inputs for historical pilot and scenario regression tests.

These tests reproduce the original study protocol, not v2 curriculum accuracy.
Active curriculum integration is tested separately in test_curriculum_v2.
"""
import json
from contextlib import ExitStack,contextmanager
from unittest.mock import patch
from diagnostic import engine


@contextmanager
def frozen_v1():
    edges=engine.load_graph_rows(engine.ROOT/'assets/NCERT_Knowledge_Graph/prerequisite_edges.xlsx')
    nodes={}
    for row in edges:
        for side in ('source','target'):
            cid=row[side+'_id'];nodes[cid]=dict(id=cid,en=row[side+'_en'],hi=row[side+'_hi'],chapter=row[side+'_chapter'])
    path=engine.ROOT/'diagnostic/question_bank.json'
    bank=json.loads(path.read_text(encoding='utf-8'))
    with ExitStack() as stack:
        stack.enter_context(patch.object(engine,'load_graph',return_value=(nodes,edges)))
        stack.enter_context(patch.object(engine,'load_bank',return_value=bank))
        stack.enter_context(patch.object(engine,'BANK_PATH',path))
        yield
