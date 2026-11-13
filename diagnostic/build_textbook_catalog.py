"""Create the catalog from inspected sections of the user-supplied chapter PDFs."""
import hashlib
import json
from pathlib import Path
import fitz
from diagnostic.engine import ROOT

CHAPTERS = [
    ('Patterns in Mathematics', 'गणित में पैटर्न'), ('Lines and Angles', 'रेखाएँ और कोण'),
    ('Number Play', 'संख्याओं का खेल'), ('Data Handling and Presentation', 'आँकड़ों का प्रबंधन और प्रस्तुतीकरण'),
    ('Prime Time', 'अभाज्य समय'), ('Perimeter and Area', 'परिमाप और क्षेत्रफल'),
    ('Fractions', 'भिन्न'), ('Playing with Constructions', 'रचनाओं के साथ खेलना'),
    ('Symmetry', 'सममिति'), ('The Other Side of Zero', 'शून्य के दूसरी ओर'),
]


def build():
    documents = []
    for language, prefix in [('en', 'fegp'), ('hi', 'fhgp')]:
        for path in sorted((ROOT/'assets'/'textbooks'/language).glob('*.pdf')):
            doc = fitz.open(path)
            chapter = int(path.stem[-2:]) if path.stem[-2:].isdigit() else None
            solutions = next((i+1 for i, p in enumerate(doc) if 'CHAPTER' in p.get_text() and 'SOLUTIONS' in p.get_text()), None)
            documents.append({'language':language, 'filename':path.name, 'chapter':chapter,
                              'pages':len(doc), 'appended_solutions_start_pdf_page':solutions,
                              'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                              'edition_marker':'Reprint 2026-27', 'origin':'User-supplied ZIP; textbook pages may be watermarked',
                              'url':f'/api/textbooks/{language}/{path.name}'})
    concepts = {}
    def add(ids, chapter, section, read, practice, english, hindi, label, section_hi, relation='direct'):
        # Page positions here were read from the corresponding uploaded PDFs.
        for cid in ids:
            versions = {}
            for lang,prefix,task,title in [('en','fegp',english,CHAPTERS[chapter-1][0]),('hi','fhgp',hindi,CHAPTERS[chapter-1][1])]:
                file=f'{prefix}1{chapter:02}.pdf'
                versions[lang]={'chapter':chapter,'chapter_title':title,'section':section if lang=='en' else section_hi,
                                'read_pdf_page':read[0],'read_printed_page':read[1],
                                'practice_pdf_page':practice[0],'practice_printed_page':practice[1],
                                'practice_label':label if lang=='en' else label.replace('Figure it Out','आइए, पता लगाएँ').replace('Q','प्रश्न'),
                                'instruction':task,
                                'read_url':f'/api/textbooks/{lang}/{file}#page={read[0]}',
                                'practice_url':f'/api/textbooks/{lang}/{file}#page={practice[0]}'}
            concepts[cid]={'relation':relation,'location_verified':True,'verified_by':'AI text and page inspection; human pedagogical review pending', 'versions':versions}
    add(['MATH6_C0002','MATH6_C0003','MATH6_C0005','MATH6_C0049'],1,'1.2 Patterns in Numbers',(3,3),(3,3),
        'Read Table 1. Try Figure it Out Q1-2: identify the rules and continue the sequences.',
        'सारणी 1 पढ़िए। आइए, पता लगाएँ के प्रश्न 1-2 में नियम पहचानकर अनुक्रमों को आगे बढ़ाइए।',
        'Figure it Out Q1-2','1.2 संख्याओं में पैटर्न')
    add(['MATH6_C0006','MATH6_C0044'],1,'1.2 Patterns in Numbers',(3,3),(3,3),
        'Focus on the odd-number row of Table 1. For Q1-2, explain its rule and write the next three terms.',
        'सारणी 1 की विषम संख्याओं वाली पंक्ति देखिए। प्रश्न 1-2 में इसका नियम समझाकर अगली तीन संख्याएँ लिखिए।',
        'Figure it Out Q1-2 (odd-number row)','1.2 संख्याओं में पैटर्न')
    add(['MATH6_C0007','MATH6_C0045'],1,'1.2 Patterns in Numbers',(3,3),(3,3),
        'Focus on the even-number row of Table 1. For Q1-2, explain its rule and write the next three terms.',
        'सारणी 1 की सम संख्याओं वाली पंक्ति देखिए। प्रश्न 1-2 में इसका नियम समझाकर अगली तीन संख्याएँ लिखिए।',
        'Figure it Out Q1-2 (even-number row)','1.2 संख्याओं में पैटर्न')
    add(['MATH6_C0009'],1,'1.3 Visualising Number Sequences',(4,4),(5,5),
        'Study the square-dot patterns in Table 2. Try Q2, focusing on why square numbers are called squares.',
        'सारणी 2 में वर्गाकार बिंदुओं के पैटर्न देखिए। प्रश्न 2 में समझाइए कि वर्ग संख्याएँ वर्ग क्यों कहलाती हैं।',
        'Figure it Out Q2 (square numbers)','1.3 संख्या अनुक्रमों का दृश्यांकन')
    add(['MATH6_C0018'],2,'2.2 Line Segment',(2,14),(4,16),
        'Review the two endpoints of a segment. Try Q2: identify the segments and points in Figure 2.4.',
        'रेखाखंड के दोनों अंत्य बिंदुओं को समझिए। प्रश्न 2 में आकृति 2.4 के रेखाखंड और बिंदु पहचानिए।',
        'Figure it Out Q2','2.2 रेखाखंड')
    add(['MATH6_C0020','MATH6_C0021','MATH6_C0022'],2,'2.5 Angle',(5,17),(7,19),
        'Read Figure 2.8 to locate the common endpoint and two arms. Try Q1: draw rays for one pictured angle and name its vertex.',
        'आकृति 2.8 में उभयनिष्ठ बिंदु और दोनों भुजाएँ पहचानिए। प्रश्न 1 में एक कोण की किरणें बनाकर उसके शीर्ष का नाम लिखिए।',
        'Figure it Out Q1','2.5 कोण')
    add(['MATH6_C0024'],2,'2.9 Measuring Angles',(21,33),(17,29),
        'Read why a right angle is 90 degrees. Then try section 2.8 Q1: find right angles around your classroom.',
        'पढ़िए कि समकोण 90 डिग्री का क्यों होता है। फिर खंड 2.8 का प्रश्न 1 कीजिए: कक्षा में समकोण पहचानिए।',
        'Section 2.8, Figure it Out Q1','2.9 कोणों को मापना')
    add(['MATH6_C0025'],2,'2.8 Special Types of Angles: Classifying Angles',(19,31),(19,31),
        'Compare acute angles with a right angle. Try Q1-2: classify the pictured angles and draw acute and obtuse angles in different orientations.',
        'न्यून कोण की समकोण से तुलना कीजिए। प्रश्न 1-2 में कोणों को पहचानिए और विभिन्न दिशाओं में न्यून तथा अधिक कोण बनाइए।',
        'Figure it Out Q1-2 (Classifying Angles)','2.8 विशेष प्रकार के कोण: कोणों का वर्गीकरण')
    add(['MATH6_C0039'],3,'3.4 Playing with Digits: Digit sums of numbers',(6,60),(6,60),
        'Review the digit-sum examples. Start with Q1(a): make numbers whose digits total 14. Then try Q2 with numbers 40 to 70.',
        'अंकों के योग के उदाहरण पढ़िए। प्रश्न 1(a) में अंकों का योग 14 वाली संख्याएँ बनाइए। फिर प्रश्न 2 में 40 से 70 तक की संख्याएँ देखिए।',
        'Figure it Out Q1(a), Q2','3.4 अंकों के साथ खेल: संख्याओं के अंकों के योग')
    add(['MATH6_C0038'],3,'3.2 Supercells (related number-ordering activity)',(4,58),(4,58),
        'Related practice only: compare five-digit numbers in the supercells table. Discuss how a digit’s position changes the number. This page is not a standalone place-value lesson.',
        'संबंधित अभ्यास: महाकोष्ठ सारणी की पाँच अंकों वाली संख्याओं की तुलना कीजिए। चर्चा कीजिए कि अंक का स्थान बदलने से संख्या कैसे बदलती है। यह स्थानीय मान का स्वतंत्र पाठ नहीं है।',
        'Try This: Table 2 (related practice)','3.2 महाकोष्ठ: संबंधित अभ्यास','related')
    output={'title':'Ganita Prakash / गणित प्रकाश - Grade 6','edition':'Reprint 2026-27',
            'documents':documents,'concepts':concepts,
            'scope':'All ten chapters archived in both languages. Selected textbook locations mapped to the existing diagnostic scope. Source locations verified, graph edges and diagnostic rules remain provisional.'}
    (ROOT/'diagnostic'/'textbook_catalog.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(documents)} PDFs catalogued, {len(concepts)} concept locations mapped')


if __name__ == '__main__':
    build()
    from diagnostic.extend_textbook_catalog import extend
    extend()
