"""Five synthetic end-to-end demo profiles plus the rotated-angle demonstration."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from diagnostic import engine as e,book_chat as chat,chat_tutor as tutor
from diagnostic.tutor_bank import load


def run():
    output=e.ROOT/'reports/phase2_demo_transcripts.json'
    if output.exists():raise FileExistsError('Preserve the existing demonstration record.')
    demos=[];bank={q['id']:q for q in load()}
    with tempfile.TemporaryDirectory() as tmp,patch('diagnostic.chat_router.plan',return_value={'action':'check','concept_id':'MATH6_C0025','planner':'preset_demo_topic'}),patch.object(chat,'generate',side_effect=RuntimeError('offline demo')):
        conn=e.connect(Path(tmp)/'demo.sqlite3')
        try:
            for language in ('en','hi'):
                for profile in ('prerequisite_gap','no_apparent_gap','calculation_slip','language_confusion','insufficient_evidence','right_straight_transfer'):
                    query=('I confuse a right angle with a straight angle.' if language=='en' else 'मुझे समकोण और सरल कोण में भ्रम होता है।') if profile=='right_straight_transfer' else (
                           'Help me understand acute angles.' if language=='en' else 'न्यून कोण समझने में मदद कीजिए।')
                    start=chat.send(conn,'synthetic-demo-'+profile+'-'+language,query,language)
                    thread=start['thread_id'];out=start['message'];asked=0
                    while out.get('check_question'):
                        q=bank[out['check_question']['id']]
                        response=q['answer']
                        if (profile in ('prerequisite_gap','right_straight_transfer') and asked<2) or (profile=='calculation_slip' and asked==0):
                            response=str(int(q['answer'])+1) if q['type']=='numeric' else next(c for c in 'ABCD' if c!=q['answer'])
                        if profile=='insufficient_evidence' or (profile=='language_confusion' and asked==0):response='not sure' if language=='en' else 'मुझे नहीं पता'
                        asked+=1
                        if asked>3:raise AssertionError('Diagnostic question budget exceeded')
                        out=chat.send(conn,'synthetic-demo-'+profile+'-'+language,response,language,thread)['message']
                    summary=out.get('tutor_summary')
                    if not summary:raise AssertionError('Demo did not reach an explanation')
                    action='language_help' if profile=='language_confusion' else 'still_confused' if profile=='prerequisite_gap' else 'another_example' if profile=='right_straight_transfer' else 'simpler'
                    chat.send(conn,'synthetic-demo-'+profile+'-'+language,'__feedback__:'+action,language,thread)
                    state=json.loads(conn.execute('SELECT payload FROM book_chat_tutoring WHERE thread_id=?',(thread,)).fetchone()[0])
                    if state.get('practice'):chat.send(conn,'synthetic-demo-'+profile+'-'+language,state['practice']['answer'],language,thread)
                    demos.append({'profile':profile,'language':language,'questions_asked':asked,
                                  'interpretation':'Author-controlled synthetic responses; a slip/language cause is not established by score patterns.',
                                  'diagnostic_summary':summary,'messages':chat.messages(conn,'synthetic-demo-'+profile+'-'+language,thread)})
        finally:conn.close()
    report={'kind':'Functional demonstration transcripts, not learner results','generation':'Offline; generic topics show labelled textbook excerpts. The angle contrast uses a cited local template.',
            'topic_mapping':'Preset for generic profiles; explicit angle contrast uses the local contrast router.',
            'demonstrations':demos}
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'demonstrations':len(demos),'max_diagnostic_questions':max(d['questions_asked'] for d in demos)}))
    return report


if __name__=='__main__':run()
