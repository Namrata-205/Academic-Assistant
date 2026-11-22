"""Deterministic bilingual invariants; semantic equivalence still needs review."""
import re
import unicodedata
from collections import Counter
from functools import lru_cache
import json
import ast
import operator
from diagnostic import engine as e


def numeric_text(text):
    text = unicodedata.normalize('NFKC', text)
    return ''.join(str(unicodedata.digit(c)) if c.isdecimal() else c for c in text)


def signature(text):
    text = numeric_text(text)
    numbers = Counter(re.findall(r'(?<!\w)\d+(?:\.\d+)?', text))
    units = Counter()
    for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(°|degrees?\b|अंश|डिग्री|cm\b|सेमी|सेंटीमीटर|mm\b|मिमी|मिलीमीटर|kg\b|किग्रा|किलोग्राम)',text,re.I):
        unit = match[2].lower()
        category = 'degree' if unit in ('°','degree','degrees','अंश','डिग्री') else 'cm' if unit in ('cm','सेमी','सेंटीमीटर') else 'mm' if unit in ('mm','मिमी','मिलीमीटर') else 'kg'
        units[(match[1], category)] += 1
    return numbers, units


def check_pair(english, hindi):
    a,b = signature(english),signature(hindi)
    errors = []
    if a[0] != b[0]: errors.append('numbers_differ')
    if a[1] != b[1]: errors.append('units_differ')
    if not re.search(r'[\u0900-\u097f]',hindi): errors.append('missing_hindi')
    return {'passed':not errors,'errors':errors,'semantic_review':'PENDING'}


def check_arithmetic(text):
    text = numeric_text(text)
    operations={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
    def value(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return node.value
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            return value(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        if isinstance(node,ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](value(node.left),value(node.right))
        raise ValueError('Unsupported arithmetic expression')
    number=r'[+-]?\d+(?:\.\d+)?'
    for match in re.finditer(r'(?<![\d.])('+number+r'(?:\s*[+×*−÷/–-]\s*'+number+r')+)\s*=\s*('+number+r')',text):
        expression=match[1].translate(str.maketrans({'×':'*','−':'-','–':'-','÷':'/'}))
        try:result=value(ast.parse(expression,mode='eval').body)
        except (ZeroDivisionError,SyntaxError):raise ValueError('Incorrect arithmetic example') from None
        if abs(result-float(match[2]))>1e-8:raise ValueError('Incorrect arithmetic example')


@lru_cache(maxsize=1)
def glossary():
    path=e.ROOT/'diagnostic/bilingual_glossary_v2.json'
    if not path.exists():path=e.ROOT/'diagnostic/bilingual_glossary.json'
    return json.loads(path.read_text(encoding='utf-8'))


def term(concept_id, nodes):
    row = glossary()['concepts'].get(concept_id)
    node = nodes[concept_id]
    return {'concept_id':concept_id,'en':row['en'] if row else node['en'],
            'hi':row['hi'] if row else node['hi'],
            'review_status':row['review_status'] if row else 'PENDING'}


def check_angle_claims(text):
    """Reject explicit wrong angle-measure assertions, not arbitrary example numbers."""
    text = numeric_text(text)
    patterns = [('right angle',r'\bright angle\s+(?:(?:measures|is|equals|of)\s+)+(\d+)\s*(?:°|degrees?\b)',90),
                ('straight angle',r'\bstraight angle\s+(?:(?:measures|is|equals|of)\s+)+(\d+)\s*(?:°|degrees?\b)',180),
                ('समकोण',r'समकोण\s+(?:का\s+)?(?:माप\s+)?(\d+)\s*(?:°|अंश|डिग्री)',90),
                ('सरल कोण',r'सरल कोण\s+(?:का\s+)?(?:माप\s+)?(\d+)\s*(?:°|अंश|डिग्री)',180)]
    for _,pattern,expected in patterns:
        if any(int(value)!=expected for value in re.findall(pattern,text,re.I)):
            raise ValueError('Incorrect angle measure assertion')
