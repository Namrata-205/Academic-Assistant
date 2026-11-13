"""Regression tests for diagnostic/hindi_text.py (run: python -m unittest discover -s tests)."""
import unittest
from pathlib import Path

from diagnostic import hindi_text as H

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / 'assets' / 'textbooks' / 'hi' / 'fhgp101.pdf'


class UnicodeRepair(unittest.TestCase):
    def test_deterministic_rules(self):
        cases = {'प्रदãशत': 'प्रदर्शित', 'विद्याãथयों': 'विद्यार्थियों', 'उ°र': 'उत्तर',
                 'ćृंखला': 'श्रृंखला', 'एेलब्रस': 'ऐलब्रस', 'जैकपाॅट': 'जैकपॉट', 'हुर्इं': 'हुईं',
                 '6ं से': '6 से', 'हैं?ु': 'हैं?', 'diंmensions': 'dimensions',
                 'हीी': 'ही', 'गंेद': 'गेंद', 'प्राैद्योगिकी': 'प्रौद्योगिकी',
                 'अांशिक': 'आंशिक', 'क्‍या': 'क्या', 'है।ये': 'है। ये', 'है ।': 'है।'}
        for bad, good in cases.items():
            self.assertEqual(H.repair_unicode(bad), good, bad)


class LexiconRepair(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = H.make_is_word()

    def fix(self, w):
        return H._repair_token(H.repair_unicode(w), self.lex)

    def test_doubled_and_missing(self):
        cases = {'ययह': 'यह', 'क्याया': 'क्या', 'संख्यायाएँ': 'संख्याएँ', 'चित्रोंत्रों': 'चित्रों',
                 'प्रत्येयेक': 'प्रत्येक', 'कक्ा': 'कक्षा', 'इनहें': 'इन्हें', 'सिदांत': 'सिद्धांत',
                 'कियया': 'किया', 'त्रिभजु': 'त्रिभुज', 'संख्याओ': 'संख्याओं', 'अनक्रम': 'अनुक्रम'}
        for bad, good in cases.items():
            self.assertEqual(self.fix(bad), good, bad)

    def test_glued_words_are_split(self):
        self.assertEqual(self.fix('केसाथ'), 'के साथ')
        self.assertEqual(self.fix('कोंजोड़ना'), 'को जोड़ना')

    def test_correct_words_untouched(self):
        for w in ['अध्ययन', 'व्यय', 'आनंददायक', 'बहुभुज', 'वर्गाकार', 'दृश्यांकन', 'गणन',
                  'केवल', 'हिमकण', 'संख्याएँ', 'बहुभुजों']:
            self.assertEqual(self.fix(w), w, w)

    def test_join_split_pieces(self):
        self.assertEqual(H.repair_with_lexicon('अध् ययन', self.lex), 'अध्ययन')
        self.assertEqual(H.repair_with_lexicon('संख् यायाएँ', self.lex), 'संख्याएँ')

    def test_merge_prefers_better_words(self):
        pdfium = 'से संबधित होते हैं। ऐसे सबंध एक-दसरे ग्रिड बंद से 1 से शरू होने वाली स्पष्ट कर क्या'
        mupdf = 'से संबंधित होते हैं। ऐसे संबंध एक-दूसरे ग्रिड बिंदु से 1 से शुरू होनेवाली स्पष्टकर क् या'
        merged, swaps = H.merge_candidates(pdfium, mupdf, self.lex)
        self.assertEqual(merged, 'से संबंधित होते हैं। ऐसे संबंध एक-दूसरे ग्रिड बिंदु से 1 से '
                                 'शुरू होने वाली स्पष्ट कर क्या')
        self.assertGreater(swaps, 0)

    def test_merge_chapters_2_to_5(self):
        cases = [  # (pdfium, pymupdf, expected)
            ('हम घमुाव की', 'हम घुमाव की', 'हम घुमाव की'),              # same letters, sign moved
            ('या ऊर्ध्वाध र रूप', 'या ऊर्ध्वाधर रूप', 'या ऊर्ध्वाधर रूप'),      # lone letter split off
            ('एक क्षैतिजरेखा औरएकऊर्ध्वाधररेखाखींचतेहैं।', 'एक क्षैतिज रेखा और एक ऊर्ध्वाधर रेखा खींचते हैं।',
             'एक क्षैतिज रेखा और एक ऊर्ध्वाधर रेखा खींचते हैं।'),          # lost spaces
            ('चार अक्लों वाली', 'चार अंकों वाली', 'चार अंकों वाली'),        # domain term wins
            ('कोई महाकोष्ठ न हो?', 'कोई महाकोष्ठ नन हो?', 'कोई महाकोष्ठ न हो?'),  # न is a word
            ('ऐसा हो गया', 'ऐसा होगया', 'ऐसा हो गया'),
            ('प्रारंभिक बिंदुयां आदि', 'प्रारंभिक बिंदु या आदि', 'प्रारंभिक बिंदु या आदि'),
        ]
        for a, b, want in cases:
            self.assertEqual(H.merge_candidates(a, b, self.lex)[0], want, a)

    def test_no_over_repair(self):
        for w in ['खूंटियों', 'गुणनखंडन', 'कापरेकर', 'वृत्त', 'अंकों', 'गणन', 'घुमाव', 'अभाज्य']:
            self.assertEqual(self.fix(w), w, w)
        self.assertEqual(self.fix('अनमुान)।'), 'अनुमान)।')          # punctuation after the word
        self.assertEqual(self.fix('घमुाव'), 'घुमाव')
        self.assertEqual(self.fix('गणज'), 'गुणज')                    # towards a domain word
        self.assertTrue(self.lex('उदाहरणत') and self.lex('खींचेंगे') and self.lex('गत्ते'))

    def test_real_run_chapters_2_to_5(self):
        cor = H.load_corrections()
        cases = {'सिरा जितनाा  नुकीलाा  होगाा': 'सिरा जितना नुकीला होगा',     # न is not a split point
                 'क्या आप रिहाान और शीतल': 'क्या आप रिहान और शीतल',
                 'यह परिमाणित  कर सकते': 'यह परिमाणित कर सकते',              # nor is पर
                 'कहतेे  हैं िक 48, संख्या': 'कहते हैं कि 48, संख्या',          # visual-order ि
                 'आधाारभूत संक्रियायाओं जैसे': 'आधारभूत संक्रियाओं जैसे',
                 'सर्व गुणज और सार्व गुणनखंड': 'सर्व गुणज और सार्व गुणनखंड',
                 'केसाथ और केलिए': 'के साथ और के लिए',
                 'गुलाब जमना, गुजियाँ': 'गुलाब जामुन, गुजियाँ'}
        for raw, good in cases.items():
            self.assertEqual(H.clean_block(raw, self.lex, cor), good, raw)

    def test_corrections_file(self):
        corr = {'कें': 'के', 'ऊं पर': 'ऊपर', 'पैटना': ''}   # '' = <del> in the .tsv
        self.assertEqual(H.apply_corrections('संख्याओं कें ऊं पर पैटना, गेंद', corr),
                         'संख्याओं के ऊपर , गेंद')


@unittest.skipUnless(PDF.exists() and H.have_pdfium(), 'needs fhgp101.pdf and pypdfium2')
class Chapter1(unittest.TestCase):
    def test_page1_clean(self):
        import pymupdf
        lex = H.make_is_word()
        with pymupdf.open(PDF) as doc:
            text, method, _ = H.extract_hindi_page(doc[0], lex, ocr=False)
        for good in ['ये पैटर्न', 'खरीदारी', 'इसके साथ ही यह', 'कक्षा', 'सिद्धांत', 'गेंद']:
            self.assertIn(good, text)
        for bad in ['ययह', 'हीी', 'कक्ा', 'यये']:
            self.assertNotIn(bad, text)
        self.assertLess(H.quality(text, lex)['oov_rate'], 0.02)

if __name__ == '__main__':
    unittest.main()