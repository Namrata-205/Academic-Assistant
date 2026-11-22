"""Audit every graph concept against supplied books; never invent absent references."""
import json
import re
from pathlib import Path
import fitz
from diagnostic.engine import ROOT,load_graph
from diagnostic.build_textbook_catalog import CHAPTERS

# Concept ID, chapter, reading PDF page, practice PDF page, section, verification
# anchors in English/Hindi. Practice instructions below are original guidance.
LOCATIONS=[
 ('MATH6_C0004',1,10,11,'1.5 Patterns in Shapes','shape sequences','आकार'),
 ('MATH6_C0008',1,3,5,'1.2–1.3 Number sequences','Triangular','त्रिभुजाकार'),
 ('MATH6_C0010',1,3,5,'1.2–1.3 Number sequences','Cubes','घन'),
 ('MATH6_C0011',1,3,3,'1.2 Patterns in Numbers','Powers of 2','घातें'),
 ('MATH6_ADD001',1,3,3,'1.2 Patterns in Numbers','Virah','विरहांक'),
 ('MATH6_C0012',3,6,6,'3.4 Playing with Digits','consecutive','क्रमागत'),
 ('MATH6_C0013',1,3,3,'1.2 Counting-number row','Counting numbers','गणन'),
 ('MATH6_C0014',1,11,11,'1.6 Relation to Number Sequences','equal-length','भुजाओं'),
 ('MATH6_C0015',1,4,5,'1.3 Visualising Number Sequences','Pictorial','चित्रीय'),
 ('MATH6_C0016',2,1,3,'2.1 Point','point determines','सटीक'),
 ('MATH6_C0017',2,2,4,'2.3 Line','forever','अनिश्‍च'),
 ('MATH6_C0019',2,3,4,'2.4 Ray','endlessly','दिशा'),
 ('MATH6_C0023',2,15,18,'2.8 Special Types of Angles','straight angle','सरल कोण'),
 ('MATH6_C0026',2,39,40,'2.11 Types of Angles and their Measures','Obtuse Angle','अधिक कोण'),
 ('MATH6_C0027',2,39,40,'2.11 Types of Angles and their Measures','Reflex angle','प्रतिवर्ती'),
 ('MATH6_C0028',2,21,21,'2.9 Measuring Angles: full turn','full turn','पूर्ण घुमाव'),
 ('MATH6_C0029',2,21,28,'2.9 Measuring Angles','1 degree','1º'),
 ('MATH6_C0030',2,25,28,'2.9 Measuring Angles: protractor','protractor','चाँ'),
 ('MATH6_C0031',2,17,18,'2.8 Right angles and perpendicular lines','perpendicular','लंब'),
 ('MATH6_C0033',2,4,4,'2.4 Figure it Out: intersecting lines','intersect','प्रतिच्छेद'),
 ('MATH6_C0034',2,13,14,'2.7 Making Rotating Arms','Rotating Arms','घूर्णन'),
 ('MATH6_C0035',2,28,28,'2.9 Angle Bisector','Angle Bisector','समद्विभाजक'),
 ('MATH6_C0036',3,1,5,'3.1 Numbers can Tell us Things','Numbers are used','संख्याओं'),
 ('MATH6_C0037',3,6,6,'3.4 Playing with Digits','1-digit','1 अंक'),
 ('MATH6_C0040',3,7,7,'3.5 Pretty Palindromic Patterns','palindrome','विलोमाक्षर'),
 ('MATH6_C0041',3,5,5,'3.3 Patterns of Numbers on the Number Line','number line','संख्या रेखा'),
 ('MATH6_C0042',3,15,16,'3.11 Simple Estimation','estimate','आकलन'),
 ('MATH6_C0043',3,15,16,'3.11 Simple Estimation (related only)','estimate','आकलन'),
 ('MATH6_C0046',3,11,11,'3.8 Mental Math','added','जोड़'),
 ('MATH6_C0047',3,12,12,'3.8 Mental Math: Adding and Subtracting','subtraction','घटाना'),
 ('MATH6_C0050',3,9,9,'3.6 The Magic Number of Kaprekar','6174','6174'),
 ('MATH6_C0051',3,3,4,'3.2 Supercells','supercell','महाकोष'),
 ('MATH6_ADD002',3,15,15,'3.10 The Collatz Conjecture','Collatz','कोलाट'),
 ('MATH6_ADD003',2,1,3,'Chapter 2: plane geometry foundations','plane geometry','समतल'),
]
RELATED={'MATH6_C0012','MATH6_C0013','MATH6_C0043'}
MISSING={'MATH6_C0032':'No dedicated parallel-lines explanation or exercise located in the supplied chapters.',
         'MATH6_C0048':'No magic-square lesson or exercise located. Supercells and patterned sums are not equivalent to magic squares.'}


def compact(text):return re.sub(r'[\s\u200c\u200d\u00ad]+','',text).casefold()


def extend():
    if (ROOT/'assets/NCERT_Knowledge_Graph/prerequisite_edges_v2.csv').exists():
        from diagnostic.upgrade_curriculum import build
        return build()
    path=ROOT/'diagnostic/textbook_catalog.json'
    cat=json.loads(path.read_text(encoding='utf-8'))
    nodes,_=load_graph();audit=[]
    for cid,ch,read,practice,section,en_anchor,hi_anchor in LOCATIONS:
        versions={}
        relation='related' if cid in RELATED else 'direct'
        for lang,prefix,anchor in [('en','fegp',en_anchor),('hi','fhgp',hi_anchor)]:
            file=f'{prefix}1{ch:02}.pdf'
            with fitz.open(ROOT/'assets/textbooks'/lang/file) as doc:
                source_text=doc[read-1].get_text()
                if compact(anchor) not in compact(source_text):
                    raise ValueError(f'Anchor not found: {cid} {lang} page {read}: {anchor}')
                if 'CHAPTER' in source_text and 'SOLUTIONS' in source_text:
                    raise ValueError('A source location points to appended solutions')
            offset=0 if ch==1 else 12 if ch==2 else 54
            task=(f'Review {section}, focusing on {nodes[cid]["en"]}. Then work through the example or activity on printed page {practice+offset}.' if lang=='en' else
                  f'{nodes[cid]["hi"]} की व्याख्या पढ़िए। फिर मुद्रित पृष्ठ {practice+offset} के उदाहरण या गतिविधि पर अभ्यास कीजिए।')
            if relation=='related':task+=(' This is related practice, not a dedicated definition of this concept.' if lang=='en' else ' यह संबंधित अभ्यास है; इस अवधारणा की स्वतंत्र परिभाषा नहीं है।')
            versions[lang]={'chapter':ch,'chapter_title':CHAPTERS[ch-1][0 if lang=='en' else 1],
                            'section':section,'read_pdf_page':read,'read_printed_page':read+offset,
                            'practice_pdf_page':practice,'practice_printed_page':practice+offset,
                            'practice_label':'Example/activity on this page','instruction':task,
                            'read_url':f'/api/textbooks/{lang}/{file}#page={read}',
                            'practice_url':f'/api/textbooks/{lang}/{file}#page={practice}',
                            'verification_anchor':anchor}
        cat['concepts'][cid]={'relation':relation,'location_verified':True,'versions':versions,
                              'verified_by':'Source page text and anchor check; human pedagogical review pending'}
    for cid,reason in MISSING.items():
        cat['concepts'][cid]={'relation':'unavailable','location_verified':False,'versions':{},'reason':reason}
    for cid,node in sorted(nodes.items()):
        material=cat['concepts'].get(cid)
        if not material:raise ValueError('Concept not audited: '+cid)
        audit.append({'concept_id':cid,'concept':node['en'],'relation':material['relation'],
                      'english_reference':material['versions'].get('en',{}).get('read_url'),
                      'hindi_reference':material['versions'].get('hi',{}).get('read_url'),
                      'location_verified':material['location_verified'],'reason':material.get('reason','')})
    cat['coverage_audit']={'concept_count':len(nodes),'linked_count':sum(bool(r['english_reference'] and r['hindi_reference']) for r in audit),
                           'unavailable':list(MISSING),'note':'Coverage is source-location coverage, not graph validation. Related activities are labelled.'}
    path.write_text(json.dumps(cat,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'reports/textbook_coverage_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(cat['coverage_audit'],indent=2))

if __name__=='__main__':extend()
