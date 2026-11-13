"""Local multilingual sentence retrieval with scope, ambiguity and intent guards."""
import json
import re
import sys
import threading
import unicodedata
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
MODEL=ROOT/'assets'/'models'/'multilingual-minilm'
RUNTIME=ROOT/'.dist'/'semantic-runtime'
MAPPER_VERSION='semantic-v2'
MIN_SIMILARITY=.57
MIN_MARGIN=.07
LOCK=threading.RLock()

# Definition-based retrieval prototypes, not a list of exact user-question aliases.
DEFINITIONS={
 'pattern':'A rule or regularity in numbers, shapes or arrangements that repeats or changes predictably.',
 'number pattern':'A list of numbers follows a rule such as adding, subtracting, multiplying or doubling. Find the next term in the series.',
 'shape pattern':'Geometric shapes are repeated or changed in a sequence; describe the rule and draw the next shape.',
 'sequence':'An ordered list of terms or numbers, arranged according to a rule.',
 'odd number':'An integer that cannot be divided into two equal whole-number groups; remainder one on division by two. Ends in 1, 3, 5, 7, 9.',
 'even number':'An integer divisible by two with no remainder, which can be split into equal pairs. Ends in 0, 2, 4, 6, 8.',
 'triangular number':'Dots arranged in a triangle with rows of 1, 2, 3 and so on. Sequence 1, 3, 6, 10, 15.',
 'square number':'A number multiplied by itself. Dots in equal rows and columns in a square: 1, 4, 9, 16, 25.',
 'cube number':'A number multiplied by itself three times, such as 2 times 2 times 2 equals 8. Sequence 1, 8, 27, 64.',
 'powers of 2':'Repeatedly double a number: 1, 2, 4, 8, 16, 32. Each term is twice the previous term.',
 'Virahanka numbers':'Each term is the sum of the previous two terms. Sequence 1, 2, 3, 5, 8, 13, 21.',
 'consecutive number':'Numbers that follow one another without a gap, such as 5, 6, 7 or 12, 13, 14.',
 'natural number':'Counting numbers starting from one: 1, 2, 3, 4 and so on.',
 'regular polygon':'A closed polygon in which all sides and all angles are equal.',
 'visual pattern':'A mathematical rule shown using pictures, dots, arrangements and diagrams.',
 'point':'A precise position or location in geometry, represented by a dot with no length or width.',
 'line':'A straight path extending endlessly in both directions, with no endpoints.',
 'line segment':'A straight path between two endpoints with a definite finite length.',
 'ray':'A straight path with one starting endpoint that extends endlessly in one direction.',
 'angle':'Two rays sharing a common endpoint form a turn or opening. Identify the arms and the vertex.',
 'vertex':'The common endpoint where the two arms of an angle meet.',
 'arm of angle':'Each ray forming an angle; the two rays share the same starting point.',
 'straight angle':'An angle of 180 degrees, a half turn, whose two arms form a straight line.',
 'right angle':'An angle measuring exactly 90 degrees, a quarter turn, the corner of a square.',
 'acute angle':'An angle larger than zero and smaller than 90 degrees, less than a quarter turn.',
 'obtuse angle':'An angle bigger than 90 degrees and smaller than 180 degrees, between a quarter and half turn.',
 'reflex angle':'An angle greater than 180 degrees but less than 360 degrees.',
 'complete angle':'One full turn or rotation through 360 degrees.',
 'degree':'A unit for measuring angles; one complete turn contains 360 degrees.',
 'protractor':'A tool with a degree scale used to measure or draw the size of an angle.',
 'perpendicular':'Two lines that meet at 90 degrees or at a right angle.',
 'parallel lines':'Two straight lines in the same plane that never meet, remaining the same distance apart.',
 'intersecting lines':'Two straight lines that cross or meet at a common point.',
 'rotation':'Turning an object or ray about a fixed point through some angle.',
 'angle bisector':'A ray dividing one angle into two smaller angles of equal size.',
 'number':'A quantity used for counting, measuring, ordering or calculation.',
 'digit':'A single symbol from zero to nine used to write numbers.',
 'place value':'The value of a digit depends on its position: ones, tens, hundreds, thousands. The value of 4 in 3452 is 400.',
 'digit sum':'Add the individual digits of a number, ignoring place values. For 352, add 3 plus 5 plus 2.',
 'palindrome':'A number that reads the same forwards and backwards, such as 121 or 1331.',
 'number line':'Numbers represented in increasing order at positions on a straight line.',
 'estimation':'Find an approximate quantity or reasonable answer instead of calculating exactly.',
 'rounding':'Replace a number by the nearest ten, hundred, thousand or a specified place.',
 'addition':'Combine quantities or find their sum using the plus operation.',
 'subtraction':'Find what remains or the difference by taking one quantity away from another.',
 'magic square':'Numbers in a square grid so every row, column and diagonal has the same sum.',
 'Kaprekar number':'Rearrange four digits into largest and smallest numbers, subtract, and repeat to reach the Kaprekar constant 6174.',
 'supercell':'A cell in a number grid whose number is larger than all adjacent neighbouring cells.',
 'Collatz conjecture':'Start from an integer: divide by two if even; multiply by three and add one if odd; repeat toward one.',
 'plane geometry':'The study of points, lines, angles and figures in a flat two-dimensional plane.',
}
UNSUPPORTED={
 'fractions':'Adding, subtracting, multiplying or dividing fractions; numerator and denominator; equivalent fractions.',
 'algebra':'Solving an equation for an unknown letter, algebraic expressions or simultaneous equations.',
 'area':'Calculate the area or perimeter of rectangles, triangles and shapes using measurements.',
 'probability':'Find the probability or chance of an event or interpret statistics and charts.',
 'prime factors':'Find prime numbers, factors, HCF or LCM of given numbers.',
}


def normal(text):
    return unicodedata.normalize('NFKC',text).casefold().strip()


def contains(text,term):
    return bool(re.search(r'(?<!\w)'+re.escape(normal(term))+r'(?!\w)',text))


@lru_cache(maxsize=1)
def runtime():
    if not (MODEL/'model_quantized.onnx').exists():raise RuntimeError('Local semantic model has not been installed.')
    if RUNTIME.exists() and str(RUNTIME) not in sys.path:sys.path.append(str(RUNTIME))
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(MODEL/'model_quantized.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    tokenizer=Tokenizer.from_file(str(MODEL/'tokenizer.json'))
    tokenizer.enable_truncation(max_length=128)
    tokenizer.enable_padding(pad_id=0,pad_token='[PAD]')
    return np,session,tokenizer


def embed(texts):
    np,session,tokenizer=runtime()
    result=[]
    with LOCK:
        for start in range(0,len(texts),12):
            batch=tokenizer.encode_batch(texts[start:start+12])
            inputs={'input_ids':np.array([t.ids for t in batch],dtype=np.int64),
                    'attention_mask':np.array([t.attention_mask for t in batch],dtype=np.int64),
                    'token_type_ids':np.array([t.type_ids for t in batch],dtype=np.int64)}
            outputs=session.run(None,{i.name:inputs[i.name] for i in session.get_inputs()})[0]
            mask=inputs['attention_mask'][...,None]
            pooled=(outputs*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1)
            pooled=pooled/np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-12)
            result.append(pooled)
    return np.concatenate(result)


@lru_cache(maxsize=2)
def index(serialized_nodes):
    nodes=json.loads(serialized_nodes)
    keys=[];texts=[]
    for node in nodes:
        definition=DEFINITIONS.get(node['en'],node['en'])
        keys.extend([node['id'],node['id']])
        texts.extend([node['en']+'. '+definition,node['hi']+'. '+definition])
    for key,definition in UNSUPPORTED.items():keys.append('outside:'+key);texts.append(definition)
    return keys,embed(texts)


def mapping(text,nodes):
    text=normal(text)
    def clarify(reason,candidates=(),**extra):
        return {'status':'clarify','candidates':list(candidates),'reason':reason,'mapper_version':MAPPER_VERSION,**extra}
    if not text:return clarify('Enter a question in English or Hindi.')
    # Unsupported intent must not collapse into a generic term such as addition.
    if any(contains(text,t) for t in ['fraction','fractions','भिन्न','भिन्नों','equation','equations','समीकरण','बीजगणित','probability']):
        return clarify('This question includes a topic outside the current prerequisite graph. Rephrase for a supported concept or choose the topic you intended.',scope='outside current graph')
    if re.search(r'not\s+(?:less|smaller|greater|larger)|(?:कम|अधिक)\s+नहीं',text):
        return clarify('Please state the intended angle range explicitly. The negated comparison can describe several angle types.')
    # Mathematical constraints prevent embedding similarity from reversing inequalities
    # or confusing a ray with a finite segment. Multiple constraints remain ambiguous.
    constraints=[]
    # Natural place-value questions need not use the phrase "value of".
    # E.g. "why the 4 in 3452 means 400" or "the 6 in 268 is worth 60".
    position_question=re.search(r'(?<!\d)(\d)\s+(?:in|within)\s+(\d{2,})\s+(?:means?|represents?|is\s+worth|stands?\s+for)\b',text)
    if position_question and position_question[1] in position_question[2]:constraints.append('MATH6_C0038')
    if re.search(r'value of (?:the )?(?:digit )?\d+ (?:in|within) \d+',text) or re.search(r'\d+\s*में\s*\d+\s*का\s*(?:मान|मूल्य)',text):constraints.append('MATH6_C0038')
    if (re.search(r'(?:sum|add|adding|total).*(?:digits|each digit|individual digit)',text) or re.search(r'अंकों.*(?:योग|जोड़)',text)):
        constraints.append('MATH6_C0039')
    if re.search(r'(?:smaller|less|below).*(?:90|quarter turn|right angle)',text) or re.search(r'(?:90|समकोण).*कम',text):constraints.append('MATH6_C0025')
    if re.search(r'(?:greater|larger|more|bigger).*90.*(?:less|smaller|below).*180',text):constraints.append('MATH6_C0026')
    if re.search(r'(?:greater|larger|more|bigger).*180.*(?:less|smaller|below).*360',text):constraints.append('MATH6_C0027')
    if re.search(r'(?:one|single).*(?:start|endpoint).*(?:no end|endless|forever|infinite)',text):constraints.append('MATH6_C0019')
    if len(set(constraints))>1:return clarify('Your question refers to more than one mathematical idea. Which should we focus on?',sorted(set(constraints)))
    if constraints:
        key=constraints[0]
        return {'status':'mapped','concept_id':key,'candidates':[key],'mapper_version':MAPPER_VERSION,'method':'explicit mathematical intent constraints'}
    hits=[]
    for key,node in nodes.items():
        terms=[node['en'],node['hi']]
        if node['en'].endswith(('number','angle','segment','pattern','digit','ray','line','sum')):
            terms.append(node['en']+'s')
        matched=[t for t in terms if contains(text,t)]
        if matched:hits.append((key,max(matched,key=len)))
    hits=[(k,t) for k,t in hits if not any(normal(t)!=normal(other) and normal(t) in normal(other) for _,other in hits)]
    # Units are supporting context when a named angle type is the clear topic.
    angle_types={'right angle','acute angle','obtuse angle','straight angle','reflex angle','complete angle'}
    if any(nodes[k]['en'] in angle_types for k,_ in hits):
        hits=[(k,t) for k,t in hits if nodes[k]['en'] not in {'degree','number'}]
    ids=sorted({k for k,_ in hits})
    if set(ids)=={'MATH6_C0020','MATH6_C0021'} and (
        re.search(r"vertex\s+of\s+(?:an?\s+|the\s+)?angle|angle['’]s\s+vertex",text)
        or re.search(r'कोण\s+का\s+शीर्ष',text)):
        return {'status':'mapped','concept_id':'MATH6_C0021','candidates':['MATH6_C0021'],
                'mapper_version':MAPPER_VERSION,'method':'explicit geometric role in context'}
    if len(ids)>1:
        return clarify('More than one concept or chapter matches. Which one do you want to understand?',ids,method='explicit ambiguity guard')
    # Only distinctive explicit names take precedence over semantic retrieval.
    generic={'number','digit','pattern','angle','line','point','addition','subtraction','sequence','degree'}
    if len(ids)==1 and nodes[ids[0]]['en'] not in generic:
        return {'status':'mapped','concept_id':ids[0],'candidates':ids,'mapper_version':MAPPER_VERSION,'method':'explicit concept with scope and context guards'}
    try:
        keys,vectors=index(json.dumps(list(nodes.values()),sort_keys=True,ensure_ascii=False))
        similarities=vectors@embed([text])[0]
        ranked={}
        for key,value in zip(keys,similarities):ranked[key]=max(ranked.get(key,-1),float(value))
        ordered=sorted(ranked.items(),key=lambda pair:pair[1],reverse=True)
    except (ImportError,RuntimeError,OSError) as ex:
        if len(ids)==1:
            return clarify('Please clarify the specific idea or choose a concept. Semantic matching is unavailable for this question.',ids,semantic_available=False)
        return clarify('Please choose a concept or rephrase. The local semantic matcher is unavailable.',semantic_available=False)
    top,score=ordered[0]
    candidates=[key for key,_ in ordered if not key.startswith('outside:')][:4]
    evidence={'method':'local multilingual semantic retrieval','mapper_version':MAPPER_VERSION,
              'similarity':round(score,4),'similarity_is_probability':False,
              'ranked_candidates':[{'concept_id':key,'similarity':round(value,4)} for key,value in ordered[:5]]}
    if top.startswith('outside:'):
        return clarify('The question appears to be outside the concepts currently modelled in the graph. Please clarify the intended topic.',**evidence)
    # Equivalent names across chapters still need explicit chapter clarification.
    duplicates=[key for key,node in nodes.items() if node['en']==nodes[top]['en']]
    if len(duplicates)>1 and score>=MIN_SIMILARITY:
        return clarify('This concept appears in more than one chapter. Which chapter do you mean?',duplicates,**evidence)
    runner=next((value for key,value in ordered[1:] if key!=top),-1)
    if score<MIN_SIMILARITY or score-runner<MIN_MARGIN:
        return clarify('I am not certain which idea your question concerns. Select a suggestion or add more detail.',candidates,**evidence)
    return {'status':'mapped','concept_id':top,'candidates':[top],**evidence}
