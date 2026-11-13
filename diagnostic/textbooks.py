"""Verified local textbook locations. No PDF parsing is needed at runtime."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / 'diagnostic' / 'textbook_catalog.json'


def catalog():
    if not CATALOG.exists():
        return {'documents': [], 'concepts': {}}
    return json.loads(CATALOG.read_text(encoding='utf-8'))


def study_plan(report):
    concepts = catalog().get('concepts', {})
    plan = []
    for row in report['concepts']:
        material = concepts.get(row['concept_id'])
        if not material or not material.get('versions'):
            continue
        current = [o for o in row['observations'] if o.get('evidence_origin') != 'saved history']
        if row['assessment'] == 'Assessed' and any(o['score'] != 1 for o in current):
            reason, priority = 'Revisit the items checked here; this is practice guidance, not a new diagnosis.', 0
        elif row['concept_id'] == report['target']:
            reason, priority = ('Try this after reviewing the foundations. This topic was not checked directly.' if row['assessment'] != 'Assessed' else 'Use this to practise the target topic further.'), 1
        else:
            continue
        plan.append({'concept_id': row['concept_id'], 'reason': reason, 'priority': priority, **material})
    return sorted(plan, key=lambda item: (item['priority'], item['concept_id']))[:3]
