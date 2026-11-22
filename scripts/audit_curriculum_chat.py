"""Real retrieval, offline-generation smoke audit across all chapters/languages."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostic import book_chat,engine

representatives=['MATH6_C0106','MATH6_C0111','MATH6_C0113','MATH6_C0117','MATH6_C0130',
 'MATH6_C0158','MATH6_C0180','MATH6_C0191','MATH6_C0203','MATH6_C0216']
rows=[];nodes,_=engine.load_graph()
with tempfile.TemporaryDirectory() as tmp:
    conn=engine.connect(Path(tmp)/'smoke.sqlite3')
    try:
        with patch('diagnostic.book_chat.generate',side_effect=RuntimeError('offline audit')):
            for cid in representatives:
                for lang in ('en','hi'):
                    try:
                        result=book_chat.answer(nodes[cid][lang],lang,cid,conn=conn,learner='synthetic-curriculum-audit')
                        passed=result['status']=='answered' and bool(result.get('paragraphs')) and bool(result.get('sources'))
                        rows.append(dict(concept_id=cid,chapter=nodes[cid]['chapter'],language=lang,passed=passed,
                            status=result['status'],mode=result.get('mode'),paragraphs=result.get('paragraphs',[]),
                            sources=[s['url'] for s in result.get('sources',[])]))
                    except Exception as error:rows.append(dict(concept_id=cid,language=lang,passed=False,error=str(error)))
                    print(cid,lang,rows[-1]['passed'],flush=True)
    finally:conn.close()
out=engine.ROOT/'reports/curriculum_v2/chat_smoke.json'
out.write_text(json.dumps({'scope':'Real local retrieval and offline teaching; not a measured learning-effectiveness result.',
    'passed':all(r['passed'] for r in rows),'cases':rows},ensure_ascii=False,indent=2),encoding='utf-8')
raise SystemExit(not all(r['passed'] for r in rows))
