import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat,chat_context,semantic_chunks


class ChatRAGTests(unittest.TestCase):
    def test_natural_plural_question_and_specific_foundations(self):
        nodes,edges=e.load_graph()
        mapping=e.map_question('I do not understand acute angles. Explain them simply and tell me what to learn first.',nodes,edges)
        self.assertEqual(mapping['concept_id'],'MATH6_C0025')
        context=chat_context.context(None,None,mapping['concept_id'],nodes,edges)
        self.assertEqual(set(context['selected_prerequisites']),{'MATH6_C0024','MATH6_C0029'})

    def test_connected_angle_vertex_question_does_not_force_topic_choice(self):
        with patch.object(book_chat,'generate',side_effect=RuntimeError('offline')):
            output=book_chat.answer('Explain angle and vertex.','en')
        self.assertEqual(output['status'],'answered')
        self.assertEqual(output['concept']['id'],'MATH6_C0020')
        self.assertEqual(book_chat.answer('Explain acute angle and place value together.','en')['status'],'clarify')
        nodes,edges=e.load_graph()
        self.assertEqual(e.map_question('What is the vertex of an angle?',nodes,edges)['concept_id'],'MATH6_C0021')

    def test_semantic_boundaries_preserve_sentences_and_page_ranking(self):
        import numpy as np
        def encode(texts):
            return np.array([[1.,0.] if 'angle' in t.lower() else [0.,1.] for t in texts])
        blocks=['An angle has two arms. An angle has a vertex.','Numbers can be odd.']
        chunks=semantic_chunks.split_semantically(blocks,encode)
        self.assertEqual(chunks,['An angle has two arms. An angle has a vertex.','Numbers can be odd.'])
        with patch.object(semantic_chunks.sm,'embed',side_effect=encode),patch.object(semantic_chunks,'page_index',return_value=(chunks,encode(chunks))):
            result=semantic_chunks.rank_pages([('book.pdf',3,1,{'url':'/book#page=3'})],'angle',1)
        self.assertIn('angle',result[0]['excerpt']);self.assertEqual(result[0]['similarity'],1.)
        self.assertEqual(result[0]['url'],'/book#page=3')

    def test_evidence_prioritisation_separation_and_no_cross_learner_leak(self):
        nodes,edges=e.load_graph();target='MATH6_C0025';foundation='MATH6_C0024'
        self.assertIn(foundation,e.prerequisites(target,edges))
        with tempfile.TemporaryDirectory() as tmp:
            conn=e.connect(Path(tmp)/'test.db')
            sid=e.new_session(conn,'alice',target,'graph-guided',[])
            questions=[q for q in e.load_bank() if q['concept_id']==foundation][:2]
            for q in questions:
                conn.execute('INSERT INTO responses VALUES (?,?,?,?,?,?)',(sid['id'] if isinstance(sid,dict) else sid,questions.index(q),q['id'],foundation,'wrong',0))
            conn.commit()
            imported={'items':[{'concept_ids':[target],'topic':'Angles','source_signal':'Source report suggests further checking','source_status':'pending'}]}
            with patch('diagnostic.chat_context.imported_reports.linked_context',return_value=imported):
                own=chat_context.context(conn,'alice',target,nodes,edges)
            other=chat_context.context(conn,'bob',target,nodes,edges)
            self.assertEqual(own['selected_prerequisites'][0],foundation)
            self.assertEqual(next(c for c in own['learning_evidence'] if c['concept_id']==foundation)['status'],'Possible prerequisite difficulty')
            self.assertTrue(all(c['status']=='Unassessed' for c in other['learning_evidence']))
            self.assertEqual(own['imported_background'][0]['source_status'],'pending')
            self.assertNotIn('alice',json.dumps(own));conn.close()

    def test_generation_receives_graph_and_learner_context_without_identifiers(self):
        source={'id':'S1','excerpt':'An angle has two arms sharing a common endpoint called the vertex.','concept_id':'MATH6_C0020'}
        payload={'message':{'content':json.dumps({'paragraphs':[{'text':'An angle has two arms.','citations':['S1'],'evidence':source['excerpt']}]})}}
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return json.dumps(payload).encode()
        context={'selected_prerequisites':['MATH6_C0020'],'learning_evidence':[{'status':'Unassessed'}]}
        with patch.object(book_chat,'model_status',return_value={'generation_available':True,'model':'test'}),patch.object(book_chat,'urlopen',return_value=Response()) as request:
            book_chat.generate('Briefly explain angle','angle','en',[source],[],context)
        body=json.loads(request.call_args.args[0].data)
        prompt=json.loads(body['messages'][1]['content'])
        self.assertEqual(prompt['learning_context'],context)
        self.assertEqual(prompt['sources'][0]['concept_id'],'MATH6_C0020')


if __name__=='__main__':unittest.main()
