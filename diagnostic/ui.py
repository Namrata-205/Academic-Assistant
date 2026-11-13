"""Streamlit views for diagnostic sessions and review artifacts."""
import json
import streamlit as st
from diagnostic import engine as e


def show_report(report, nodes):
    st.subheader('Diagnostic report')
    st.warning(report['review_status'])
    st.caption(f"{report['question_count']} new questions · {report['version']}")
    st.dataframe([{'Concept': nodes[r['concept_id']]['en'], 'Role': r['role'],
                   'Assessment': r['assessment'], 'Diagnostic status': r['status']}
                  for r in report['concepts']], hide_index=True, use_container_width=True)
    for row in report['concepts']:
        with st.expander(f"{nodes[row['concept_id']]['en']} — {row['status']}"):
            if not row['observations']:
                st.write('Unassessed: no question was asked for this concept. No difficulty is inferred.')
            for observation in row['observations']:
                st.write(f"**{observation['question_id']}** · {observation['question_en']}")
                st.write(observation['question_hi'])
                st.write({'response': observation['response'], 'score': observation['score'],
                          'correct_answer': observation['correct_answer'],
                          'evidence_origin': observation['evidence_origin'],
                          'session_id': observation.get('session_id', 'pilot')})
                st.caption(observation['scoring_rule'])
                if observation['score'] == 0:
                    st.caption('Possible explanation to check: ' + observation['possible_difficulty'])
            st.write('Graph source references (unverified passage IDs):')
            st.json(row['references'])
    st.caption(report['limitations'])
    with st.expander('Reproducible selection and decision rules'):
        st.write(report['rules'])
    st.download_button('Download report JSON', json.dumps(report, ensure_ascii=False, indent=2),
                       file_name='diagnostic_report.json', mime='application/json')


def render_diagnostic():
    nodes, edges = e.load_graph()
    bank = e.load_bank()
    st.subheader('Ask, check, understand')
    st.warning('Development mode: question bank and diagnostic rules await your final review. '
               'Graph relationships and textbook references are also provisional.')
    conn = e.connect()
    learner = st.text_input('Learner code (use a pseudonym, not a name)', key='learner_code')
    if not learner.strip():
        st.info('Enter a learner code to load saved history and begin.')
        conn.close()
        return
    learner = learner.strip()
    prior_all = e.history(conn, learner)
    st.caption(f'{len(prior_all)} saved responses for this learner on the current bank version. Stored locally in diagnostic/history.sqlite3.')
    saved = conn.execute('SELECT id,target,created FROM sessions WHERE learner=? AND version=? ORDER BY created DESC', (learner, e.VERSION)).fetchall()
    with st.expander('Resume or view a saved interaction'):
        selected_session = st.selectbox('Saved interaction', [''] + [r[0] for r in saved],
                                       format_func=lambda sid: next((f'{r[2]} · {nodes[r[1]]["en"]} · {sid[:8]}' for r in saved if r[0] == sid), 'Choose an interaction'))
        if st.button('Open saved interaction', disabled=not selected_session):
            st.session_state['diagnostic_sid'] = selected_session
    with st.form('map_form'):
        text = st.text_area('Your learning question / आपका प्रश्न', placeholder='How do I identify an acute angle?')
        submitted = st.form_submit_button('Identify concept')
    if submitted:
        st.session_state['mapping'] = e.map_question(text, nodes, edges)
        st.session_state.pop('diagnostic_sid', None)
    mapping = st.session_state.get('mapping')
    target = None
    if mapping:
        if mapping['status'] == 'clarify':
            st.info(mapping['reason'])
            options = mapping['candidates'] or sorted(nodes)
            target = st.selectbox('Clarify the intended concept (including chapter)', options,
                                   format_func=lambda cid: f'{nodes[cid]["en"]} / {nodes[cid]["hi"]} [{nodes[cid]["chapter"]}]', index=None)
        else:
            target = mapping['concept_id']
        if target:
            node = nodes[target]
            st.success(f'Identified concept: {node["en"]} / {node["hi"]} ({node["chapter"]})')
            related = e.prerequisites(target, edges)
            st.write('**Proposed direct prerequisites**')
            st.write(', '.join(nodes[c]['en'] + ' / ' + nodes[c]['hi'] for c in related) or 'No direct prerequisite recorded.')
            with st.expander('Supporting textbook reference identifiers'):
                st.caption('These are identifiers from the graph, not verified quotations or textbook page links. Missing identifiers are shown explicitly.')
                st.dataframe([{'Prerequisite': nodes[r['source_id']]['en'],
                               'Passage IDs': r.get('supporting_passage_ids') or 'Not provided',
                               'Graph review': r.get('validation_status', 'PENDING')}
                              for r in edges if r['target_id'] == target], hide_index=True)
            if not e.eligible(target, bank, edges):
                st.info('No bank items cover this target or its direct prerequisites yet. No diagnosis can be made.')
            elif st.button('Start a new three-question diagnostic'):
                sid = e.new_session(conn, learner, target, 'graph-guided', prior_all)
                st.session_state['diagnostic_sid'] = sid
    sid = st.session_state.get('diagnostic_sid')
    if sid:
        session = conn.execute('SELECT target,method,prior,report FROM sessions WHERE id=? AND learner=?', (sid, learner)).fetchone()
        if session:
            target, method, prior_json, saved_report = session
            prior = json.loads(prior_json)
            current = [dict(zip(('question_id','concept_id','response','score'), row), session_id=sid)
                       for row in conn.execute('SELECT question_id,concept_id,response,score FROM responses WHERE session_id=? ORDER BY ordinal', (sid,))]
            st.divider()
            st.write(f'**Diagnostic for {nodes[target]["en"]} / {nodes[target]["hi"]}** · Interaction {sid[:8]}')
            question = e.select_question(target, bank, edges, current, prior, method) if not saved_report else None
            if question:
                st.progress(len(current) / 3, text=f'Question {len(current) + 1} of at most 3')
                st.caption(f'{question["id"]} · Assessing {question["concept_en"]}')
                st.write(question['en'])
                st.write(question['hi'])
                with st.form(f'answer_{sid}_{len(current)}'):
                    response = st.text_input('Answer: A–D for MCQ, or a number / उत्तर')
                    st.caption('An unclear or blank response is recorded as unscorable and still uses one question.')
                    send = st.form_submit_button('Submit response')
                if send:
                    e.save_response(conn, sid, question, response)
                    conn.close()
                    st.rerun()
                if st.button('Finish with evidence collected so far'):
                    report = e.make_report(target, bank, edges, current, prior)
                    with conn:
                        conn.execute('UPDATE sessions SET report=? WHERE id=?', (json.dumps(report, ensure_ascii=False), sid))
                    conn.close()
                    st.rerun()
            else:
                report = json.loads(saved_report) if saved_report else e.make_report(target, bank, edges, current, prior)
                if not saved_report:
                    with conn:
                        conn.execute('UPDATE sessions SET report=? WHERE id=?', (json.dumps(report, ensure_ascii=False), sid))
                show_report(report, nodes)
    conn.close()


def render_review():
    bank = e.load_bank()
    st.subheader('Question bank and pilot review')
    st.info('30 original bilingual development items · 10 concepts · automated/content review completed; your final review is pending. Pilot diagnoses still require independent review.')
    st.dataframe([{'ID': q['id'], 'Concept': q['concept_en'], 'English': q['en'], 'Hindi': q['hi'],
                   'Answer': q['answer'], 'Scoring': q['scoring_rule'],
                   'Possible difficulty': q['possible_difficulty'], 'Review': q['review_status']}
                  for q in bank], hide_index=True, use_container_width=True)
    st.download_button('Download bilingual bank', e.BANK_PATH.read_bytes(), 'question_bank.json', 'application/json')
    csv_bank = e.ROOT / 'reports' / 'question_bank.csv'
    if csv_bank.exists():
        st.download_button('Download review copy (CSV)', csv_bank.read_bytes(), 'question_bank.csv', 'text/csv')
    st.write('**Decision and selection rules**')
    st.write(e.RULES)
    summary = e.ROOT / 'reports' / 'pilot_summary.json'
    if summary.exists():
        pilot = json.loads(summary.read_text(encoding='utf-8'))
        st.subheader('Preliminary synthetic pilot')
        st.caption('20 synthetic cases × 2 methods. Independent expected-diagnosis review is pending. No real learner study has been conducted.')
        st.dataframe([dict(Method=method, **values) for method, values in pilot['results'].items()], hide_index=True)
        with st.expander('Observed errors and interpretation'):
            st.markdown((e.ROOT / 'reports' / 'pilot_error_analysis.md').read_text(encoding='utf-8'))
    for filename in ('review_checklist.csv', 'pilot_cases.json', 'pilot_results.csv', 'pilot_error_analysis.md', 'review_notes.md'):
        path = e.ROOT / 'reports' / filename
        if path.exists():
            st.download_button(f'Download {filename}', path.read_bytes(), filename, key=filename)
    st.caption('Final review records are kept in reports/review_checklist.csv. Record reviewer, date, decision and corrections there; no human sign-off is inferred automatically.')
