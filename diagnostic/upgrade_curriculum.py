"""Build and audit bilingual source locations for the active ten-chapter graph."""
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path
import pymupdf
from diagnostic import engine,extraction
from diagnostic.curriculum import CHAPTERS,teaching_name

PRIOR_CHAPTER={'MATH6_C0013':1,'MATH6_C0036':1,'MATH6_C0046':3,'MATH6_C0047':3,
 'MATH6_C0102':5,'MATH6_C0103':5,'MATH6_C0037':3,'MATH6_C0038':3,'MATH6_C0101':3,
 'MATH6_C0012':3,'MATH6_C0140':8,'MATH6_C0141':8,'MATH6_C0142':6,'MATH6_C0143':6}
EXTRA={
 'MATH6_C0036':('whole numbers','पूर्ण संख्याओं'),
 'MATH6_C0101':('larger','greater','बड़ी','बड़ा'),
 'MATH6_C0049':('quick','sum','जोड़','योग'),
 'MATH6_C0104':('hexagonal','षट्भुज','षड्भुज','षट्कोण','षड्कोण'), 'MATH6_C0105':('relations','संबंध'),
 'MATH6_C0106':('complete graph','पूर्ण ग्राफ'), 'MATH6_C0107':('stacked squares','वर्गों'),
 'MATH6_C0108':('stacked triangles','त्रिभुजों'), 'MATH6_C0109':('Koch','कोख'),
 'MATH6_C0110':('comparing angles','तुलना'), 'MATH6_C0111':('drawing angles','कोण बनाना'),
 'MATH6_C0114':('winning strategies','रणनीति'), 'MATH6_C0120':('scale','पैमाना','संकेत'),
 'MATH6_C0124':('infographic','इन्फोग्राफ','सूचना'),
 'MATH6_C0123':('horizontal','vertical'),
 'MATH6_C0138':('Divisibility by 2','2 से','विभाज्य'),
 'MATH6_C0132':('Eratosthenes','एराटोस्थनीज','छलनी'),
 'MATH6_C0139':('divisibility by 8','8 से विभाज्यता'),
 'MATH6_C0160':('squared grid','वर्गांकित'), 'MATH6_C0164':('split','विभाजित'),
 'MATH6_C0143':('length','centimetre'), 'MATH6_C0162':('same perimeter','different areas','perimeter'),
 'MATH6_C0171':('fractional unit','इकाई भिन्न'), 'MATH6_C0176':('mixed fractions','मिश्र'),
 'MATH6_C0173':('parts of a whole',),
 'MATH6_C0182':('Brahmagupta','ब्रह्मगुप्त'), 'MATH6_C0183':('Egypt','मिस्र'),
 'MATH6_C0197':('equidistant','बराबर दूरी','समान दूरी'),
 'MATH6_C0191':('radius','त्रिज्या'), 'MATH6_C0194':('squares and rectangles','वर्ग','आयत'),
 'MATH6_C0204':('centre of rotation','घूर्णन केंद्र','घूर्णन केन्द्र'),
 'MATH6_C0212':('inverse','प्रतिलोम'), 'MATH6_C0218':('zero pair','शून्य युग्म'),
 'MATH6_C0211':('शून्य से छोटी',), 'MATH6_C0217':('number line','संख्या रेखा'),
 'MATH6_C0214':('comparing','greater','less than'), 'MATH6_C0216':('subtraction','घटाव','घटाने'),
 'MATH6_C0219':('temperature','तापमान'), 'MATH6_C0220':('Brahmagupta','ब्रह्मगुप्त'),
}


def normal(text):
    text=unicodedata.normalize('NFKD',text).casefold()
    return re.sub(r'\s+',' ',text.replace('\u200d','').replace('\u200c','')).strip()


def build():
    root=engine.ROOT;path=root/'diagnostic/textbook_catalog.json'
    cat=json.loads(path.read_text(encoding='utf-8'));nodes,edges=engine.load_graph()
    docs={(d['language'],d['chapter']):d for d in cat['documents'] if d.get('chapter')}
    pages={};offsets={};sections={}
    for ch in range(1,11):
        for lang,prefix in [('en','fegp'),('hi','fhgp')]:
            file=root/f'assets/textbooks/{lang}/{prefix}1{ch:02}.pdf'
            document=docs[(lang,ch)]
            if hashlib.sha256(file.read_bytes()).hexdigest()!=document['sha256']:raise ValueError('Textbook changed: '+str(file))
            stop=document.get('appended_solutions_start_pdf_page')
            pages[(lang,ch)]=[p for p in extraction.get_pages(file,lang) if not stop or p['page']<stop]
            candidates=[];headings={};current=CHAPTERS[ch-1][1 if lang=='en' else 2]
            with pymupdf.open(file) as pdf:
                for i,p in enumerate(pdf):
                    if stop and i+1>=stop:break
                    for b in p.get_text('blocks'):
                        t=b[4].strip()
                        if re.fullmatch(r'\d{1,3}',t) and (b[1]>p.rect.height*.85 or b[3]<p.rect.height*.15):candidates.append(int(t)-(i+1))
            offsets[(lang,ch)]=collections.Counter(candidates).most_common(1)[0][0] if candidates else 0
            for p in pages[(lang,ch)]:
                match=re.search(r'(?m)^\s*'+str(ch)+r'\.\d+\s+[^\n]+',p['text'])
                if match:current=' '.join(match[0].split())
                headings[p['page']]=current
            sections[(lang,ch)]=headings
    audit=[]
    for cid,node in nodes.items():
        ch=PRIOR_CHAPTER[cid] if node['chapter']=='PRIOR' else int(node['chapter'][2:])
        old=cat['concepts'].get(cid)
        if old and all(lang in old.get('versions',{}) for lang in ('en','hi')) and not old.get('verified_by','').startswith('Normalized term') and cid not in ('MATH6_C0036','MATH6_C0049'):
            audit.append({'concept_id':cid,'chapter':node['chapter'],'status':'existing_source_locations','languages':list(old['versions'])})
            continue
        versions={};matches={}
        for lang,prefix in [('en','fegp'),('hi','fhgp')]:
            terms=[node[lang].split('(')[0].strip()]
            if lang=='en':terms.append(teaching_name(node['en']))
            terms.extend(t for t in EXTRA.get(cid,()) if bool(re.search('[\u0900-\u097f]',t))==(lang=='hi'))
            ranked=[]
            for p in pages[(lang,ch)]:
                text=normal(p['text']);heading=normal(sections[(lang,ch)][p['page']]);best=None
                for term in terms:
                    term=normal(term)
                    if len(term)<2:continue
                    found=re.search(re.escape(term),text)
                    if found:
                        score=10+min(len(term),60)*2+(2 if term in heading else 0)
                        if best is None or score>best[0]:best=(score,term,p['page'])
                if best:ranked.append(best)
            ranked.sort(key=lambda x:(-x[0],x[2]))
            if not ranked:
                matches[lang]='no_exact_anchor';continue
            _,anchor,page=ranked[0];matched_pages=list(dict.fromkeys(v[2] for v in ranked))[:3]
            offset=offsets[(lang,ch)];file=f'{prefix}1{ch:02}.pdf'
            versions[lang]={'chapter':ch,'chapter_title':CHAPTERS[ch-1][1 if lang=='en' else 2],
                'section':sections[(lang,ch)][page],'read_pdf_page':page,'read_printed_page':page+offset,
                'supporting_pdf_pages':matched_pages,'practice_pdf_page':page,'practice_printed_page':page+offset,
                'practice_label':'Original practice in the application' if lang=='en' else 'ऐप में मौलिक अभ्यास',
                'instruction':('Read the explanation and example on this page.' if lang=='en' else 'इस पृष्ठ की व्याख्या और उदाहरण पढ़ें।'),
                'read_url':f'/api/textbooks/{lang}/{file}#page={page}',
                'practice_url':f'/api/textbooks/{lang}/{file}#page={page}',
                'verification_anchor':anchor,'source_match':'exact normalized term; semantic review pending'}
            matches[lang]='anchored'
        cat['concepts'][cid]={'relation':'direct' if versions else 'unavailable','location_verified':bool(versions),
            'versions':versions,'verified_by':'Normalized term found on source page; human semantic review pending'}
        audit.append({'concept_id':cid,'en':node['en'],'hi':node['hi'],'chapter':node['chapter'],'status':matches})
    counts=collections.Counter(n['chapter'] for n in nodes.values())
    cat['coverage_audit']={'graph_file':engine.graph_source_path().name,'concept_count':len(nodes),
        'chapters':dict(sorted(counts.items())),'linked_count':sum(all(lang in cat['concepts'][cid]['versions'] for lang in ('en','hi')) for cid in nodes),
        'note':'Exact source-location anchors are machine checked; pedagogical validity and prerequisite relationships need human review.'}
    archive=cat.setdefault('archived_concepts',{})
    for cid in set(cat['concepts'])-set(nodes):archive[cid]=cat['concepts'].pop(cid)
    path.write_text(json.dumps(cat,ensure_ascii=False,indent=2),encoding='utf-8')
    out=root/'reports/curriculum_v2';out.mkdir(parents=True,exist_ok=True)
    (out/'source_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(cat['coverage_audit'],ensure_ascii=True))
    print('MISSING',json.dumps([(r['concept_id'],r.get('en'),r['status']) for r in audit if isinstance(r['status'],dict) and 'no_exact_anchor' in r['status'].values()],ensure_ascii=True))


if __name__=='__main__':build()
