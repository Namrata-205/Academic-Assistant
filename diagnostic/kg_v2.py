"""Knowledge graph v2 for Ganita Prakash Grade 6, chapters 1-5, read from the clean text.

Build (writes assets/NCERT_Knowledge_Graph/v2/, never touches the v1 files the app loads):
    python -m diagnostic.kg_v2

Each concept was listed by reading assets/extracted/{en,hi}/*_clean.txt (body pages only,
appended English solutions excluded). Hindi names are the forms printed in the Hindi book
(several are written there as "हिंदी (English)"). The builder re-checks all of this
against the text: where each concept is first introduced (EN and HI page), whether its
English and Hindi names occur at all, and whether the prerequisite graph is acyclic.

Concept kinds:
  taught   - introduced or developed in chapters 1-5
  assumed  - used by chapters 1-5 but taught in earlier grades (kept as prerequisite roots)

IDs: every v1 concept that still names a real concept keeps its v1 ID (question bank,
catalog and code references stay valid). New concepts use MATH6_C01xx. v1 concepts that
are not in the chapter text, or were chapter duplicates, are listed in RETIRED.
"""
import csv
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KG_DIR = ROOT / 'assets' / 'NCERT_Knowledge_Graph'
OUT = KG_DIR / 'v2'
VERSION = 'kg-v2-ch1-5'
CHAPTER_FILES = {1: 'fegp101', 2: 'fegp102', 3: 'fegp103', 4: 'fegp104', 5: 'fegp105'}
CHAPTER_TITLES = {1: ('Patterns in Mathematics', 'गणित में पैटर्न'), 2: ('Lines and Angles', 'रेखाएँ और कोण'),
                  3: ('Number Play', 'संख्याओं के साथ खेल'), 4: ('Data Handling and Presentation', 'आँकड़ों का प्रबंधन और प्रस्तुतीकरण'),
                  5: ('Prime Time', 'अभाज्य समय')}

# (id, chapter, section, kind, name_en, name_hi, en_anchors, hi_anchors)
# Anchors are the surface forms used to find the concept in text (and to cut graph-based
# chunks). English anchors match whole words, plural -s/-es allowed, case-insensitive.
# Hindi anchors are substrings (stems), since Hindi inflects the noun ending.
CONCEPTS = [
    # ---- assumed prior knowledge -------------------------------------------------------
    ('MATH6_C0013', 0, '', 'assumed', 'counting numbers', 'गणन संख्याएँ', ['counting number', 'natural number'], ['गणन संख्या', 'प्राकृत संख्या']),
    ('MATH6_C0036', 0, '', 'assumed', 'whole numbers', 'पूर्ण संख्याएँ', ['whole number'], ['पूर्ण संख्या']),
    ('MATH6_C0037', 0, '', 'assumed', 'digit', 'अंक', ['digit'], ['अंक']),
    ('MATH6_C0038', 0, '', 'assumed', 'place value', 'स्थानीय मान', ['place value', 'hundreds', 'thousands'], ['स्थानीय मान', 'सैकड़', 'हज़ार']),
    ('MATH6_C0101', 0, '', 'assumed', 'comparing numbers', 'संख्याओं की तुलना', ['larger than', 'greater than', 'smaller than', 'largest number', 'smallest number'], ['से बड़ी', 'से छोटी', 'सबसे बड़ी', 'सबसे छोटी']),
    ('MATH6_C0046', 0, '', 'assumed', 'addition', 'जोड़', ['addition', 'add', 'adding', 'sum'], ['जोड़', 'योग']),
    ('MATH6_C0047', 0, '', 'assumed', 'subtraction', 'घटाव', ['subtraction', 'subtract', 'difference'], ['घटा', 'अंतर']),
    ('MATH6_C0102', 0, '', 'assumed', 'multiplication', 'गुणा', ['multiplication', 'multiply', 'product'], ['गुणा', 'गुणनफल']),
    ('MATH6_C0103', 0, '', 'assumed', 'division', 'भाग', ['division', 'divide', 'remainder'], ['भाग दे', 'भाग कर', 'शेषफल']),
    ('MATH6_C0012', 0, '', 'assumed', 'consecutive numbers', 'क्रमागत संख्याएँ', ['consecutive'], ['क्रमागत']),
    # ---- Chapter 1: Patterns in Mathematics -------------------------------------------
    ('MATH6_C0002', 1, '1.1 What is Mathematics?', 'taught', 'pattern', 'पैटर्न', ['pattern'], ['पैटर्न', 'प्रतिरूप']),
    ('MATH6_C0003', 1, '1.2 Patterns in Numbers', 'taught', 'number pattern', 'संख्याओं में पैटर्न', ['number pattern', 'patterns of numbers', 'patterns in numbers', 'patterns in whole numbers'], ['संख्या पैटर्न', 'संख्याओं के पैटर्न', 'संख्याओं में पैटर्न']),
    ('MATH6_C0005', 1, '1.2 Patterns in Numbers', 'taught', 'number sequence', 'संख्या अनुक्रम', ['number sequence', 'sequence'], ['संख्या अनुक्रम', 'अनुक्रम']),
    ('MATH6_C0006', 1, '1.2 Patterns in Numbers', 'taught', 'odd numbers', 'विषम संख्याएँ', ['odd number'], ['विषम संख्या']),
    ('MATH6_C0007', 1, '1.2 Patterns in Numbers', 'taught', 'even numbers', 'सम संख्याएँ', ['even number'], ['सम संख्या']),
    ('MATH6_C0008', 1, '1.2 Patterns in Numbers', 'taught', 'triangular numbers', 'त्रिभुजाकार संख्याएँ', ['triangular number'], ['त्रिभुजाकार संख्या']),
    ('MATH6_C0009', 1, '1.2 Patterns in Numbers', 'taught', 'square numbers', 'वर्ग संख्याएँ', ['square number', 'squares'], ['वर्ग संख्या']),
    ('MATH6_C0010', 1, '1.2 Patterns in Numbers', 'taught', 'cube numbers', 'घन संख्याएँ', ['cube number', 'cubes'], ['घन संख्या']),
    ('MATH6_C0011', 1, '1.2 Patterns in Numbers', 'taught', 'powers of 2', '2 की घातें', ['powers of 2', 'power of 2'], ['2 की घात']),
    ('MATH6_ADD001', 1, '1.2 Patterns in Numbers', 'taught', 'Virahānka numbers', 'विरहांक संख्याएँ', ['virahānka number', 'virahanka number'], ['विरहांक']),
    ('MATH6_C0015', 1, '1.3 Visualising Number Sequences', 'taught', 'visualising number sequences', 'संख्या अनुक्रमों का दृश्यांकन', ['pictorial representation', 'visualise', 'visualising'], ['दृश्यांकन', 'चित्रात्मक']),
    ('MATH6_C0104', 1, '1.3 Visualising Number Sequences', 'taught', 'hexagonal numbers', 'षड्भुजाकार संख्याएँ', ['hexagonal number'], ['षड्भुजाकार']),
    ('MATH6_C0105', 1, '1.4 Relations among Number Sequences', 'taught', 'relations among number sequences', 'संख्या अनुक्रमों के बीच संबंध', ['relations among number sequences', 'adding up', 'add up'], ['अनुक्रमों के बीच संबंध', 'जोड़ने पर']),
    ('MATH6_C0004', 1, '1.5 Patterns in Shapes', 'taught', 'shape sequences', 'आकारों में पैटर्न', ['patterns in shapes', 'shape sequence', 'sequence of shapes', 'geometry'], ['आकारों में पैटर्न', 'आकारों के पैटर्न', 'ज्यामिति']),
    ('MATH6_C0014', 1, '1.5 Patterns in Shapes', 'taught', 'regular polygons', 'सम बहुभुज', ['regular polygon'], ['सम बहुभुज']),
    ('MATH6_C0106', 1, '1.5 Patterns in Shapes', 'taught', 'complete graphs', 'संपूर्ण ग्राफ', ['complete graph'], ['संपूर्ण ग्राफ']),
    ('MATH6_C0107', 1, '1.5 Patterns in Shapes', 'taught', 'stacked squares', 'ढेरित वर्ग', ['stacked square'], ['ढेरित वर्ग']),
    ('MATH6_C0108', 1, '1.5 Patterns in Shapes', 'taught', 'stacked triangles', 'ढेरित त्रिभुज', ['stacked triangle'], ['ढेरित त्रिभुज']),
    ('MATH6_C0109', 1, '1.5 Patterns in Shapes', 'taught', 'Koch snowflake', 'कोच हिमकण', ['koch snowflake'], ['कोच हिमकण', 'हिमकण']),
    # ---- Chapter 2: Lines and Angles -------------------------------------------------
    ('MATH6_C0016', 2, '2.1 Point', 'taught', 'point', 'बिंदु', ['point'], ['बिंदु']),
    ('MATH6_C0018', 2, '2.2 Line Segment', 'taught', 'line segment', 'रेखाखंड', ['line segment', 'end point'], ['रेखाखंड', 'अंत्य बिंदु']),
    ('MATH6_C0017', 2, '2.3 Line', 'taught', 'line', 'रेखा', ['line'], ['रेखा']),
    ('MATH6_C0019', 2, '2.4 Ray', 'taught', 'ray', 'किरण', ['ray'], ['किरण', 'किरणों']),
    ('MATH6_C0020', 2, '2.5 Angle', 'taught', 'angle', 'कोण', ['angle'], ['कोण']),
    ('MATH6_C0021', 2, '2.5 Angle', 'taught', 'vertex of an angle', 'शीर्ष', ['vertex', 'vertices'], ['शीर्ष']),
    ('MATH6_C0022', 2, '2.5 Angle', 'taught', 'arms of an angle', 'कोण की भुजाएँ', ['arms of the angle', 'arm'], ['भुजा']),
    ('MATH6_C0110', 2, '2.6 Comparing Angles', 'taught', 'comparing angles', 'कोणों की तुलना', ['comparing angles', 'compare the angles', 'superimpos*'], ['कोणों की तुलना', 'अध्यारोपण']),
    ('MATH6_C0034', 2, '2.7 Making Rotating Arms', 'taught', 'angle as amount of turn', 'घूर्णन', ['rotating arm', 'rotation', 'amount of turn', 'turn'], ['घूर्णन', 'घुमाव']),
    ('MATH6_C0023', 2, '2.8 Special Types of Angles', 'taught', 'straight angle', 'सरल कोण', ['straight angle'], ['सरल कोण']),
    ('MATH6_C0024', 2, '2.8 Special Types of Angles', 'taught', 'right angle', 'समकोण', ['right angle'], ['समकोण']),
    ('MATH6_C0031', 2, '2.8 Special Types of Angles', 'taught', 'perpendicular lines', 'लंब रेखाएँ', ['perpendicular'], ['लंब रेखा', 'लब रेखा', 'परस्पर लंब']),
    ('MATH6_C0025', 2, '2.8 Special Types of Angles', 'taught', 'acute angle', 'न्यून कोण', ['acute angle', 'acute'], ['न्यून कोण']),
    ('MATH6_C0026', 2, '2.8 Special Types of Angles', 'taught', 'obtuse angle', 'अधिक कोण', ['obtuse angle', 'obtuse'], ['अधिक कोण']),
    ('MATH6_C0028', 2, '2.9 Measuring Angles', 'taught', 'complete angle (full turn)', 'पूर्ण कोण', ['complete angle', 'full turn'], ['पूर्ण कोण', 'पूरा चक्कर', 'पूर्ण घुमाव']),
    ('MATH6_C0029', 2, '2.9 Measuring Angles', 'taught', 'degree (angle measure)', 'डिग्री (अंश)', ['degree'], ['डिग्री']),
    ('MATH6_C0035', 2, '2.9 Measuring Angles', 'taught', 'angle bisector', 'कोण समद्विभाजक', ['bisect*', 'angle bisector'], ['समद्विभाजक', 'समद्विभाजित']),
    ('MATH6_C0030', 2, '2.9 Measuring Angles', 'taught', 'protractor', 'चाँदा', ['protractor'], ['चाँदा', 'चाँदे']),
    ('MATH6_C0111', 2, '2.10 Drawing Angles', 'taught', 'drawing angles of a given measure', 'कोणों को बनाना', ['drawing angles', 'draw an angle', 'draw angles'], ['कोणों को बनाना', 'कोण बनाना', 'कोण बनाइए']),
    ('MATH6_C0027', 2, '2.11 Types of Angles and their Measures', 'taught', 'reflex angle', 'प्रतिवर्ती कोण', ['reflex angle', 'reflex'], ['प्रतिवर्ती कोण']),
    # ---- Chapter 3: Number Play -----------------------------------------------------
    ('MATH6_C0051', 3, '3.2 Supercells', 'taught', 'supercell', 'महाकोष्ठ', ['supercell'], ['महाकोष्ठ']),
    ('MATH6_C0041', 3, '3.3 Patterns of Numbers on the Number Line', 'taught', 'number line', 'संख्या रेखा', ['number line'], ['संख्या रेखा']),
    ('MATH6_C0039', 3, '3.4 Playing with Digits', 'taught', 'digit sum', 'अंकों का योग', ['digit sum'], ['अंकों का योग', 'अंकों के योग']),
    ('MATH6_C0040', 3, '3.5 Pretty Palindromic Patterns', 'taught', 'palindromic numbers', 'पैलिंड्रोम (विलोमाक्षर) संख्याएँ', ['palindrom*'], ['पैलिंड्रोम', 'विलोमाक्षर']),
    ('MATH6_C0050', 3, '3.6 The Magic Number of Kaprekar', 'taught', 'Kaprekar constant (6174)', 'कापरेकर की जादुई संख्या', ['kaprekar', '6174'], ['कापरेकर', '6174']),
    ('MATH6_C0112', 3, '3.7 Clock and Calendar Numbers', 'taught', 'clock and calendar numbers', 'घड़ी और कैलेंडर की संख्याएँ', ['calendar', 'clock'], ['कैलेंडर', 'घड़ी']),
    ('MATH6_C0113', 3, '3.8 Mental Math', 'taught', 'mental math', 'मानसिक गणित', ['mental math'], ['मानसिक गणित']),
    ('MATH6_C0049', 3, '3.9 Playing with Number Patterns', 'taught', 'quick sums using number patterns', 'संख्या पैटर्न के साथ खेलना', ['playing with number patterns', 'quicker way'], ['संख्या पैटर्न के साथ खेल', 'शीघ्र']),
    ('MATH6_ADD002', 3, '3.10 An Unsolved Mystery — the Collatz Conjecture!', 'taught', 'Collatz conjecture', 'कोलाट्ज़ अनुमान', ['collatz'], ['कोलाट्ज़']),
    ('MATH6_C0042', 3, '3.11 Simple Estimation', 'taught', 'estimation', 'आकलन', ['estimat*'], ['आकलन']),
    ('MATH6_C0114', 3, '3.12 Games and Winning Strategies', 'taught', 'winning strategy in number games', 'जीतने की रणनीति', ['winning strateg*'], ['जीतने की रणनीति', 'रणनीति']),
    # ---- Chapter 4: Data Handling and Presentation ---------------------------------
    ('MATH6_C0115', 4, '4.1 Collecting and Organising Data', 'taught', 'data', 'आँकड़े', ['data'], ['आँकड़', 'आंकड़']),
    ('MATH6_C0116', 4, '4.1 Collecting and Organising Data', 'taught', 'tally marks', 'मिलान चिह्न', ['tally'], ['मिलान चिह्न']),
    ('MATH6_C0117', 4, '4.1 Collecting and Organising Data', 'taught', 'frequency', 'बारंबारता', ['frequency', 'frequencies'], ['बारंबारता']),
    ('MATH6_C0118', 4, '4.1 Collecting and Organising Data', 'taught', 'frequency table', 'बारंबारता सारणी', ['frequency table', 'frequency distribution table'], ['बारंबारता सारणी', 'बारंबारता बंटन सारणी']),
    ('MATH6_C0119', 4, '4.2 Pictographs', 'taught', 'pictograph', 'चित्रालेख', ['pictograph'], ['चित्रालेख']),
    ('MATH6_C0120', 4, '4.2 Pictographs', 'taught', 'scale or key of a graph', 'पैमाना या कुंजी', ['scale', 'key'], ['पैमान', 'कुंजी']),
    ('MATH6_C0121', 4, '4.3 Bar Graphs', 'taught', 'bar graph', 'दंड आलेख', ['bar graph'], ['दंड आलेख', 'दंड आरेख']),
    ('MATH6_C0122', 4, '4.4 Drawing a Bar Graph', 'taught', 'drawing a bar graph', 'दंड आलेख खींचना', ['drawing a bar graph', 'draw a bar graph', 'prepare a bar graph'], ['दंड आलेख खींच', 'दंड आलेख बना', 'दंड आलेख तैयार']),
    ('MATH6_C0123', 4, '4.5 Artistic and Aesthetic Considerations', 'taught', 'vertical and horizontal bar graphs', 'स्तंभ आलेख (ऊर्ध्वाधर दंड)', ['column graph', 'vertical bar', 'horizontal bar'], ['स्तंभ आलेख', 'ऊर्ध्वाधर दंड', 'क्षैतिज दंड']),
    ('MATH6_C0124', 4, '4.5 Artistic and Aesthetic Considerations', 'taught', 'infographics', 'इन्फोग्राफिक्स (सूचना ग्राफिक्स)', ['infographic', 'information graphic'], ['इन्फोग्राफिक्स', 'सूचना ग्राफिक्स']),
    # ---- Chapter 5: Prime Time ----------------------------------------------------
    ('MATH6_C0125', 5, '5.1 Common Multiples and Common Factors', 'taught', 'multiple', 'गुणज', ['multiple'], ['गुणज']),
    ('MATH6_C0126', 5, '5.1 Common Multiples and Common Factors', 'taught', 'common multiple', 'सार्व गुणज', ['common multiple'], ['सार्व गुणज']),
    ('MATH6_C0127', 5, '5.1 Common Multiples and Common Factors', 'taught', 'factor (divisor)', 'गुणनखंड (भाजक)', ['factor', 'divisor'], ['गुणनखंड', 'भाजक']),
    ('MATH6_C0128', 5, '5.1 Common Multiples and Common Factors', 'taught', 'common factor', 'सार्व गुणनखंड', ['common factor'], ['सार्व गुणनखंड']),
    ('MATH6_C0129', 5, '5.1 Common Multiples and Common Factors', 'taught', 'perfect number', 'संपूर्ण संख्या', ['perfect number'], ['संपूर्ण संख्या']),
    ('MATH6_C0130', 5, '5.2 Prime Numbers', 'taught', 'prime number', 'अभाज्य संख्या', ['prime number', 'prime'], ['अभाज्य संख्या', 'अभाज्य']),
    ('MATH6_C0131', 5, '5.2 Prime Numbers', 'taught', 'composite number', 'भाज्य संख्या', ['composite'], ['भाज्य संख्या']),
    ('MATH6_C0132', 5, '5.2 Prime Numbers', 'taught', 'Sieve of Eratosthenes', 'इराटोस्थेनीस की छलनी', ['sieve of eratosthenes', 'eratosthenes'], ['छलनी', 'इराटोस्थेनीस']),
    ('MATH6_C0133', 5, '5.2 Prime Numbers', 'taught', 'twin primes', 'अभाज्य युग्म (जुड़वाँ अभाज्य)', ['twin prime'], ['अभाज्य युग्म']),
    ('MATH6_C0134', 5, '5.3 Co-prime numbers for safekeeping treasures', 'taught', 'co-prime numbers', 'सह-अभाज्य संख्याएँ', ['co-prime', 'coprime'], ['सह-अभाज्य', 'सहअभाज्य']),
    ('MATH6_C0135', 5, '5.4 Prime Factorisation', 'taught', 'prime factorisation', 'अभाज्य गुणनखंडन', ['prime factorisation', 'prime factorization'], ['अभाज्य गुणनखंडन']),
    ('MATH6_C0136', 5, '5.4 Prime Factorisation', 'taught', 'prime factor', 'अभाज्य गुणनखंड', ['prime factor'], ['अभाज्य गुणनखंड']),
    ('MATH6_C0137', 5, '5.4 Prime Factorisation', 'taught', 'divisibility', 'विभाज्यता', ['divisible', 'divisibility'], ['विभाज्य']),
    ('MATH6_C0138', 5, '5.5 Divisibility Tests', 'taught', 'divisibility tests for 2, 5 and 10', '2, 5 और 10 से विभाज्यता की जाँच', ['divisibility by 10', 'divisibility by 5', 'divisibility by 2', 'last digit'], ['10 से विभाज्यता', '5 से विभाज्यता', '2 से विभाज्यता', 'अंतिम अंक']),
    ('MATH6_C0139', 5, '5.5 Divisibility Tests', 'taught', 'divisibility tests for 4 and 8', '4 और 8 से विभाज्यता की जाँच', ['divisibility by 4', 'divisibility by 8', 'last two digits', 'last three digits'], ['4 से विभाज्यता', '8 से विभाज्यता', 'अंतिम दो अंक', 'अंतिम तीन अंक']),
]

# (prerequisite, concept, reason). "Prerequisite must be learned before concept."
EDGES = [
    # assumed arithmetic chain
    ('MATH6_C0013', 'MATH6_C0036', 'Whole numbers extend the counting numbers with 0.'),
    ('MATH6_C0046', 'MATH6_C0047', 'Subtraction is introduced as the inverse of addition.'),
    ('MATH6_C0046', 'MATH6_C0102', 'Multiplication is first understood as repeated addition.'),
    ('MATH6_C0102', 'MATH6_C0103', 'Division is the inverse of multiplication.'),
    ('MATH6_C0037', 'MATH6_C0038', 'A digit\'s value depends on its place.'),
    ('MATH6_C0038', 'MATH6_C0101', 'Comparing multi-digit numbers uses place value.'),
    ('MATH6_C0013', 'MATH6_C0012', 'Consecutive numbers follow one another in the counting order.'),
    # Chapter 1
    ('MATH6_C0002', 'MATH6_C0003', 'Number patterns are a kind of pattern (1.2: patterns of numbers).'),
    ('MATH6_C0036', 'MATH6_C0003', '1.2 studies patterns in whole numbers 0, 1, 2, 3, ...'),
    ('MATH6_C0003', 'MATH6_C0005', '1.2: number sequences are the most basic type of number pattern.'),
    ('MATH6_C0013', 'MATH6_C0006', 'Odd numbers are every other counting number (Table 1).'),
    ('MATH6_C0013', 'MATH6_C0007', 'Even numbers are every other counting number (Table 1).'),
    ('MATH6_C0005', 'MATH6_C0008', 'Triangular numbers are presented as a sequence in Table 1.'),
    ('MATH6_C0046', 'MATH6_C0008', 'Triangular numbers are sums 1, 1+2, 1+2+3, ...'),
    ('MATH6_C0005', 'MATH6_C0009', 'Squares are presented as a sequence in Table 1.'),
    ('MATH6_C0102', 'MATH6_C0009', 'A square number is a number multiplied by itself.'),
    ('MATH6_C0005', 'MATH6_C0010', 'Cubes are presented as a sequence in Table 1.'),
    ('MATH6_C0102', 'MATH6_C0010', 'A cube number is a number multiplied by itself three times.'),
    ('MATH6_C0005', 'MATH6_C0011', 'Powers of 2 are presented as a sequence in Table 1.'),
    ('MATH6_C0102', 'MATH6_C0011', 'Each power of 2 is the previous one multiplied by 2.'),
    ('MATH6_C0005', 'MATH6_ADD001', 'Virahānka numbers are presented as a sequence in Table 1.'),
    ('MATH6_C0046', 'MATH6_ADD001', 'Each Virahānka number is the sum of the previous two.'),
    ('MATH6_C0005', 'MATH6_C0015', '1.3 draws pictures of the sequences listed in 1.2.'),
    ('MATH6_C0008', 'MATH6_C0015', '1.3 asks why 1, 3, 6, 10, ... are called triangular, using pictures.'),
    ('MATH6_C0009', 'MATH6_C0015', '1.3 explains square numbers with square dot arrays.'),
    ('MATH6_C0015', 'MATH6_C0104', 'Hexagonal numbers are named from their pictorial (hexagon) arrangement in 1.3.'),
    ('MATH6_C0006', 'MATH6_C0105', '1.4: adding up odd numbers 1, 1+3, 1+3+5, ... gives squares.'),
    ('MATH6_C0009', 'MATH6_C0105', '1.4 relations produce the square numbers.'),
    ('MATH6_C0008', 'MATH6_C0105', '1.4: adding consecutive triangular numbers gives squares.'),
    ('MATH6_C0015', 'MATH6_C0105', '1.4 explains each relation with a picture.'),
    ('MATH6_C0002', 'MATH6_C0004', '1.5: patterns in shapes are the second kind of pattern.'),
    ('MATH6_C0004', 'MATH6_C0014', 'Regular polygons appear as a shape sequence in Table 3.'),
    ('MATH6_C0004', 'MATH6_C0106', 'Complete graphs appear as a shape sequence in Table 3.'),
    ('MATH6_C0004', 'MATH6_C0107', 'Stacked squares appear as a shape sequence in Table 3.'),
    ('MATH6_C0009', 'MATH6_C0107', '1.6: counting little squares in stacked squares gives square numbers.'),
    ('MATH6_C0004', 'MATH6_C0108', 'Stacked triangles appear as a shape sequence in Table 3.'),
    ('MATH6_C0008', 'MATH6_C0108', '1.6: rows of stacked triangles connect to triangular numbers.'),
    ('MATH6_C0004', 'MATH6_C0109', 'The Koch snowflake appears as a shape sequence in Table 3.'),
    ('MATH6_C0102', 'MATH6_C0109', '1.6: segment counts 3, 12, 48, ... are 3 times powers of 4.'),
    # Chapter 2
    ('MATH6_C0016', 'MATH6_C0018', '2.2: a line segment is the shortest path between two points.'),
    ('MATH6_C0018', 'MATH6_C0017', '2.3: a line is a segment extended endlessly in both directions.'),
    ('MATH6_C0016', 'MATH6_C0019', '2.4: a ray starts at a point.'),
    ('MATH6_C0017', 'MATH6_C0019', '2.4: a ray goes endlessly in one direction along a line.'),
    ('MATH6_C0019', 'MATH6_C0020', '2.5: an angle is formed by two rays with a common starting point.'),
    ('MATH6_C0020', 'MATH6_C0021', '2.5: the common starting point is called the vertex of the angle.'),
    ('MATH6_C0016', 'MATH6_C0021', 'The vertex is a point.'),
    ('MATH6_C0020', 'MATH6_C0022', '2.5: the rays forming the angle are called its arms.'),
    ('MATH6_C0019', 'MATH6_C0022', 'The arms of an angle are rays.'),
    ('MATH6_C0020', 'MATH6_C0110', '2.6 compares sizes of angles.'),
    ('MATH6_C0021', 'MATH6_C0110', 'Superimposing angles places vertex on vertex.'),
    ('MATH6_C0022', 'MATH6_C0110', 'Superimposing angles places one arm on another.'),
    ('MATH6_C0020', 'MATH6_C0034', '2.7: the size of an angle is the amount of rotation of one arm.'),
    ('MATH6_C0034', 'MATH6_C0023', '2.8: a straight angle is a half turn.'),
    ('MATH6_C0017', 'MATH6_C0023', 'The arms of a straight angle lie on one line.'),
    ('MATH6_C0023', 'MATH6_C0024', '2.8: folding a straight angle into two equal angles gives right angles.'),
    ('MATH6_C0024', 'MATH6_C0031', '2.8: lines that meet at right angles are perpendicular.'),
    ('MATH6_C0017', 'MATH6_C0031', 'Perpendicularity is a relation between lines.'),
    ('MATH6_C0024', 'MATH6_C0025', '2.8: acute angles are smaller than a right angle.'),
    ('MATH6_C0110', 'MATH6_C0025', 'Classifying as acute requires comparing with a right angle.'),
    ('MATH6_C0024', 'MATH6_C0026', '2.8: obtuse angles are greater than a right angle.'),
    ('MATH6_C0023', 'MATH6_C0026', '2.8: obtuse angles are less than a straight angle.'),
    ('MATH6_C0110', 'MATH6_C0026', 'Classifying as obtuse requires comparing angles.'),
    ('MATH6_C0034', 'MATH6_C0028', 'A complete angle is one full turn of the rotating arm.'),
    ('MATH6_C0023', 'MATH6_C0028', 'Two straight angles make a full turn.'),
    ('MATH6_C0028', 'MATH6_C0029', '2.9: a full turn is divided into 360 equal parts, each 1 degree.'),
    ('MATH6_C0110', 'MATH6_C0035', 'Bisecting (by folding) produces two equal angles.'),
    ('MATH6_C0029', 'MATH6_C0035', '2.9 halves 90° to 45° and 22½° by folding.'),
    ('MATH6_C0029', 'MATH6_C0030', '2.9: the protractor is the tool for measuring degrees.'),
    ('MATH6_C0030', 'MATH6_C0111', '2.10 draws angles of a given measure with a protractor.'),
    ('MATH6_C0029', 'MATH6_C0025', '2.11: acute angles measure more than 0° and less than 90°.'),
    ('MATH6_C0029', 'MATH6_C0026', '2.11: obtuse angles measure more than 90° and less than 180°.'),
    ('MATH6_C0029', 'MATH6_C0027', '2.11: reflex angles measure more than 180° and less than 360°.'),
    ('MATH6_C0023', 'MATH6_C0027', 'Reflex angles are greater than a straight angle.'),
    ('MATH6_C0028', 'MATH6_C0027', 'Reflex angles are less than a complete angle.'),
    # Chapter 3
    ('MATH6_C0101', 'MATH6_C0051', '3.2: a supercell holds a number larger than all its neighbours.'),
    ('MATH6_C0101', 'MATH6_C0041', '3.3 places numbers on a number line in order.'),
    ('MATH6_C0038', 'MATH6_C0041', 'Placing 2180, 2754, ... between marked thousands uses place value.'),
    ('MATH6_C0037', 'MATH6_C0039', 'A digit sum adds the digits of a number.'),
    ('MATH6_C0046', 'MATH6_C0039', 'A digit sum is computed by addition.'),
    ('MATH6_C0037', 'MATH6_C0040', 'A palindrome reads the same digits left-to-right and right-to-left.'),
    ('MATH6_C0046', 'MATH6_C0040', '3.5: reverse-and-add produces palindromes.'),
    ('MATH6_C0101', 'MATH6_C0050', 'Kaprekar\'s routine forms the largest and smallest numbers from the digits.'),
    ('MATH6_C0047', 'MATH6_C0050', 'Kaprekar\'s routine subtracts the smallest from the largest.'),
    ('MATH6_C0040', 'MATH6_C0112', '3.7 looks for palindromic dates and times.'),
    ('MATH6_C0037', 'MATH6_C0112', 'Clock and calendar puzzles rearrange digits.'),
    ('MATH6_C0046', 'MATH6_C0113', '3.8 composes numbers mentally by addition.'),
    ('MATH6_C0047', 'MATH6_C0113', '3.8 also uses subtraction.'),
    ('MATH6_C0038', 'MATH6_C0113', 'Mental math in 3.8 works with hundreds and thousands.'),
    ('MATH6_C0003', 'MATH6_C0049', '3.9 uses arrangements/patterns of numbers to find sums quickly.'),
    ('MATH6_C0113', 'MATH6_C0049', '3.9 replaces one-by-one addition by quicker mental methods.'),
    ('MATH6_C0005', 'MATH6_ADD002', 'A Collatz sequence is a number sequence produced by a rule.'),
    ('MATH6_C0006', 'MATH6_ADD002', 'The Collatz rule multiplies odd numbers by 3 and adds 1.'),
    ('MATH6_C0007', 'MATH6_ADD002', 'The Collatz rule halves even numbers.'),
    ('MATH6_C0102', 'MATH6_ADD002', 'The odd step multiplies by 3.'),
    ('MATH6_C0038', 'MATH6_C0042', 'Estimates are made to the nearest ten, hundred, thousand.'),
    ('MATH6_C0113', 'MATH6_C0042', 'Estimation relies on quick mental calculation.'),
    ('MATH6_C0046', 'MATH6_C0114', '3.12 games add 1, 2 or 3 to the previous number.'),
    ('MATH6_C0003', 'MATH6_C0114', 'The winning strategy is a pattern of numbers to say.'),
    # Chapter 4
    ('MATH6_C0115', 'MATH6_C0116', '4.1 records collected data with tally marks.'),
    ('MATH6_C0115', 'MATH6_C0117', 'Frequencies are counts of occurrences of data values.'),
    ('MATH6_C0013', 'MATH6_C0117', 'A frequency is a count.'),
    ('MATH6_C0116', 'MATH6_C0118', 'A frequency table is filled using tally marks.'),
    ('MATH6_C0117', 'MATH6_C0118', 'A frequency table lists the frequency of each category.'),
    ('MATH6_C0117', 'MATH6_C0119', 'A pictograph shows the frequency of each category with pictures.'),
    ('MATH6_C0119', 'MATH6_C0120', '4.2 introduces the scale/key when one symbol stands for many students.'),
    ('MATH6_C0102', 'MATH6_C0120', 'Reading a scaled pictograph multiplies symbols by the scale (5 × 10 = 50).'),
    ('MATH6_C0117', 'MATH6_C0121', 'The length or height of a bar gives the frequency.'),
    ('MATH6_C0119', 'MATH6_C0121', '4.3: "Like pictographs, bar graphs..."'),
    ('MATH6_C0120', 'MATH6_C0121', '4.3 bar graphs use a scale when frequencies are large.'),
    ('MATH6_C0121', 'MATH6_C0122', '4.4 draws the bar graph introduced in 4.3.'),
    ('MATH6_C0118', 'MATH6_C0122', '4.4 starts from Shri Nilesh\'s frequency table.'),
    ('MATH6_C0031', 'MATH6_C0122', '4.4: "Draw two perpendicular lines, one horizontal and one vertical."'),
    ('MATH6_C0121', 'MATH6_C0123', '4.5 chooses vertical (column) or horizontal bars.'),
    ('MATH6_C0121', 'MATH6_C0124', '4.5: infographics are beautified bar graphs.'),
    # Chapter 5
    ('MATH6_C0102', 'MATH6_C0125', 'Multiples of 3 are 3 × 1, 3 × 2, 3 × 3, ...'),
    ('MATH6_C0125', 'MATH6_C0126', '5.1: numbers that are multiples of both 3 and 5 are common multiples.'),
    ('MATH6_C0103', 'MATH6_C0127', '5.1: factors divide a number exactly.'),
    ('MATH6_C0125', 'MATH6_C0127', 'Jump sizes that land on 24 are its factors (24 is their multiple).'),
    ('MATH6_C0127', 'MATH6_C0128', '5.1: jump sizes reaching both treasures are common factors.'),
    ('MATH6_C0127', 'MATH6_C0129', 'A perfect number\'s factors sum to twice the number.'),
    ('MATH6_C0046', 'MATH6_C0129', 'Perfect numbers are checked by adding the factors.'),
    ('MATH6_C0127', 'MATH6_C0130', '5.2: primes have exactly two factors.'),
    ('MATH6_C0127', 'MATH6_C0131', '5.2: composite numbers have more than two factors.'),
    ('MATH6_C0130', 'MATH6_C0132', 'The sieve circles primes.'),
    ('MATH6_C0131', 'MATH6_C0132', 'The sieve crosses out composites.'),
    ('MATH6_C0125', 'MATH6_C0132', 'The sieve crosses out all multiples of each prime.'),
    ('MATH6_C0130', 'MATH6_C0133', 'Twin primes are pairs of primes.'),
    ('MATH6_C0128', 'MATH6_C0134', '5.3: co-prime numbers have no common factor other than 1.'),
    ('MATH6_C0130', 'MATH6_C0135', '5.4: prime factorisation writes a number as a product of primes.'),
    ('MATH6_C0131', 'MATH6_C0135', '5.4 keeps breaking composite factors until only primes are left.'),
    ('MATH6_C0102', 'MATH6_C0135', 'A factorisation is a product.'),
    ('MATH6_C0135', 'MATH6_C0136', '5.4: "The individual factors are called prime factors."'),
    ('MATH6_C0103', 'MATH6_C0137', '5.4: 48 is divisible by 12 because the remainder is zero.'),
    ('MATH6_C0127', 'MATH6_C0137', '"If a number is divisible by another, the second is a factor of the first."'),
    ('MATH6_C0137', 'MATH6_C0138', '5.5 tests divisibility without long division.'),
    ('MATH6_C0125', 'MATH6_C0138', 'The tests come from patterns in the last digit of multiples of 10, 5, 2.'),
    ('MATH6_C0007', 'MATH6_C0138', 'Numbers divisible by 2 are the even numbers (end in 0, 2, 4, 6, 8).'),
    ('MATH6_C0038', 'MATH6_C0139', 'Only the last two/three places matter for divisibility by 4/8.'),
    ('MATH6_C0138', 'MATH6_C0139', '5.5: the last-digit rule fails for 4, so more digits are examined.'),
    ('MATH6_C0136', 'MATH6_C0134', '5.4: no common prime factor ⇔ co-prime (systematic check).'),
]

# v1 concepts not carried into v2, with the reason (v1 files are left unchanged).
RETIRED = {
    'MATH6_C0032': 'parallel lines: not taught in chapters 1-5 (no occurrence in Ch2 text).',
    'MATH6_C0033': 'intersecting lines: not taught in chapters 1-5 (no occurrence in Ch2 text).',
    'MATH6_C0043': 'rounding: not taught in chapters 1-5 ("round" occurs only as "around").',
    'MATH6_C0048': 'magic square: not in chapters 1-5 ("magic" refers to Kaprekar\'s number).',
    'MATH6_ADD003': 'plane geometry: not a concept introduced in chapters 1-5.',
    'MATH6_C0044': 'odd number (CH03 duplicate): merged into MATH6_C0006.',
    'MATH6_C0045': 'even number (CH03 duplicate): merged into MATH6_C0007.',
}
MERGED = {'MATH6_C0044': 'MATH6_C0006', 'MATH6_C0045': 'MATH6_C0007'}


# ---------------------------------------------------------------------------- matching
def nfc(text):
    return unicodedata.normalize('NFC', text).replace('‍', '').replace('‌', '')


def _en_pattern(anchor):
    # 'stem*' matches any word starting with stem; otherwise whole word with optional plural.
    prefix = anchor.endswith('*')
    body = r'[\s-]*'.join(re.escape(w) for w in re.split(r'[\s-]+', anchor.rstrip('*').lower()))
    return r'(?<![a-z])' + body + (r'[a-z]*' if prefix else r'(?:s|es)?(?![a-z])')


def compile_anchors(concepts=None, language='en'):
    """[(concept_id, compiled regex, length)] longest anchor first, for non-overlapping matching."""
    concepts = concepts or CONCEPTS
    rows = []
    for c in concepts:
        anchors = c[6] if language == 'en' else c[7]
        for a in anchors:
            pattern = _en_pattern(a) if language == 'en' else re.escape(nfc(a))
            rows.append((c[0], re.compile(pattern, re.I if language == 'en' else 0), len(a)))
    return sorted(rows, key=lambda r: -r[2])


def find_concepts(text, compiled):
    """Concept IDs mentioned in text; longer anchors claim their span first
    (so 'न्यून कोण' is acute angle, not also angle)."""
    text = nfc(text)
    taken = [False] * len(text)
    found = []
    for cid, regex, _ in compiled:
        for m in regex.finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            if cid not in found:
                found.append(cid)
    return found


def body_pages(chapter, language):
    """Textbook body pages (appended English solutions excluded)."""
    from diagnostic.extraction import read_clean_file
    stem = CHAPTER_FILES[chapter] if language == 'en' else CHAPTER_FILES[chapter].replace('fegp', 'fhgp')
    pages = read_clean_file(ROOT / 'assets' / 'extracted' / language / f'{language}_{stem}_clean.txt')
    out = []
    for p in pages:
        if 'SOLUTIONS' in p['text'] and 'CHAPTER' in p['text']:
            break
        out.append(p)
    return out


# ------------------------------------------------------------------------------ build
def validate():
    ids = [c[0] for c in CONCEPTS]
    assert len(ids) == len(set(ids)), 'duplicate concept id'
    known = set(ids)
    for a, b, _ in EDGES:
        assert a in known and b in known, (a, b)
        assert a != b, a
    pairs = [(a, b) for a, b, _ in EDGES]
    assert len(pairs) == len(set(pairs)), 'duplicate edge'
    # Kahn topological sort; any leftover node is in a cycle.
    indeg = {i: 0 for i in ids}
    out = defaultdict(list)
    for a, b in pairs:
        indeg[b] += 1
        out[a].append(b)
    queue = [i for i in ids if indeg[i] == 0]
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    cyclic = [i for i in ids if i not in order]
    return order, cyclic


def first_mentions(language):
    """concept -> (chapter, pdf_page, sentence) of its first mention across chapters 1-5."""
    from diagnostic.extraction import split_sentences
    compiled = compile_anchors(language=language)
    seen = {}
    for ch in sorted(CHAPTER_FILES):
        for page in body_pages(ch, language):
            for sentence in split_sentences(page['text'], language):
                for cid in find_concepts(sentence, compiled):
                    if cid not in seen:
                        seen[cid] = (ch, page['page'], ' '.join(sentence.split())[:300])
    return seen


def mention_counts(language):
    compiled = compile_anchors(language=language)
    counts = defaultdict(lambda: defaultdict(int))
    for ch in sorted(CHAPTER_FILES):
        for page in body_pages(ch, language):
            for cid, regex, _ in compiled:
                counts[cid][ch] += len(regex.findall(nfc(page['text'])))
    return counts


def name_found(name, language, chapters=None):
    """Is the concept's own name (not just an anchor) printed in the chapter text?"""
    chapters = chapters or sorted(CHAPTER_FILES)
    text = nfc(' '.join(p['text'] for ch in chapters for p in body_pages(ch, language)))
    if language == 'en':
        core = re.sub(r'\s*\(.*?\)', '', name)
        return bool(re.search(_en_pattern(core), text, re.I))
    core = re.sub(r'\s*\(.*?\)', '', nfc(name))
    stem = core[:-2] if core.endswith('एँ') else core     # plural ending
    return stem in text


def build():
    order, cyclic = validate()
    en_first, hi_first = first_mentions('en'), first_mentions('hi')
    en_counts, hi_counts = mention_counts('en'), mention_counts('hi')
    by_id = {c[0]: c for c in CONCEPTS}
    nodes = []
    for cid, ch, section, kind, en, hi, en_a, hi_a in CONCEPTS:
        chapters = [ch] if ch else None
        nodes.append({
            'id': cid, 'name_en': en, 'name_hi': hi, 'chapter': f'CH{ch:02d}' if ch else 'PRIOR',
            'section': section, 'kind': kind, 'anchors_en': en_a, 'anchors_hi': hi_a,
            'first_mention_en': dict(zip(('chapter', 'pdf_page', 'sentence'), en_first[cid])) if cid in en_first else None,
            'first_mention_hi': dict(zip(('chapter', 'pdf_page', 'sentence'), hi_first[cid])) if cid in hi_first else None,
            'mentions_en': sum(en_counts[cid].values()), 'mentions_hi': sum(hi_counts[cid].values()),
            'name_en_in_text': name_found(en, 'en', chapters), 'name_hi_in_text': name_found(hi, 'hi', chapters),
            'topological_rank': order.index(cid) if cid in order else None,
            'v1_id_reused': cid.startswith('MATH6_C00') or cid.startswith('MATH6_ADD'),
        })
    node_by_id = {n['id']: n for n in nodes}
    edges = []
    for a, b, reason in EDGES:
        ca, cb = by_id[a], by_id[b]
        edges.append({'source_id': a, 'target_id': b, 'source_en': ca[4], 'target_en': cb[4],
                      'source_hi': ca[5], 'target_hi': cb[5],
                      'source_chapter': node_by_id[a]['chapter'], 'target_chapter': node_by_id[b]['chapter'],
                      'relation': 'prerequisite_of', 'reasoning': reason,
                      'evidence': 'section reference' if re.search(r'\b[1-5]\.\d+\b|Table|"', reason) else 'definitional',
                      'cross_chapter': node_by_id[a]['chapter'] != node_by_id[b]['chapter'],
                      'validation_status': 'PENDING_HUMAN_REVIEW', 'model': 'claude-opus-5-5 (manual reading of clean text)'})
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {'version': VERSION, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'assets/extracted/{en,hi}/*_clean.txt chapters 1-5 (body pages; appended solutions excluded)',
            'review_status': 'AI-authored from the textbook text; independent human review pending',
            'concepts': len(nodes), 'taught': sum(n['kind'] == 'taught' for n in nodes),
            'assumed': sum(n['kind'] == 'assumed' for n in nodes), 'edges': len(edges),
            'cross_chapter_edges': sum(e['cross_chapter'] for e in edges), 'nodes_in_cycles': cyclic,
            'retired_v1_concepts': RETIRED, 'merged_v1_concepts': MERGED}
    (OUT / 'knowledge_graph_v2.json').write_text(json.dumps({'meta': meta, 'nodes': nodes, 'edges': edges},
                                                            ensure_ascii=False, indent=2), encoding='utf-8')
    with (OUT / 'concepts_v2.csv').open('w', encoding='utf-8-sig', newline='') as f:
        cols = ['id', 'name_en', 'name_hi', 'chapter', 'section', 'kind', 'mentions_en', 'mentions_hi',
                'name_en_in_text', 'name_hi_in_text', 'first_page_en', 'first_page_hi']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for n in nodes:
            w.writerow({**{k: n[k] for k in cols if k in n},
                        'first_page_en': n['first_mention_en'] and f"CH{n['first_mention_en']['chapter']}p{n['first_mention_en']['pdf_page']}",
                        'first_page_hi': n['first_mention_hi'] and f"CH{n['first_mention_hi']['chapter']}p{n['first_mention_hi']['pdf_page']}"})
    # Same column names as v1 prerequisite_edges so engine.load_graph_rows(path) can read it.
    with (OUT / 'prerequisite_edges_v2.csv').open('w', encoding='utf-8-sig', newline='') as f:
        cols = ['source_id', 'target_id', 'source_en', 'source_hi', 'target_en', 'target_hi', 'source_chapter',
                'target_chapter', 'confidence', 'reasoning', 'supporting_passage_ids', 'needs_review',
                'cycle_flag', 'validation_status', 'model']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for e in edges:
            w.writerow({**{k: e[k] for k in cols if k in e}, 'confidence': '', 'supporting_passage_ids': '',
                        'needs_review': 'True', 'cycle_flag': 'False'})
    write_graphml(nodes, edges, OUT / 'knowledge_graph_v2.graphml')
    return meta, nodes, edges


def write_graphml(nodes, edges, path):
    ns = 'http://graphml.graphdrawing.org/xmlns'
    root = ET.Element('graphml', xmlns=ns)
    keys = [('d0', 'node', 'name_en'), ('d1', 'node', 'name_hi'), ('d2', 'node', 'chapter'), ('d3', 'node', 'section'),
            ('d4', 'node', 'kind'), ('d5', 'edge', 'reasoning'), ('d6', 'edge', 'validation_status'),
            ('d7', 'edge', 'evidence')]
    for kid, target, name in keys:
        ET.SubElement(root, 'key', id=kid, attrib={'for': target, 'attr.name': name, 'attr.type': 'string'})
    graph = ET.SubElement(root, 'graph', edgedefault='directed')
    for n in nodes:
        el = ET.SubElement(graph, 'node', id=n['id'])
        for kid, field in (('d0', 'name_en'), ('d1', 'name_hi'), ('d2', 'chapter'), ('d3', 'section'), ('d4', 'kind')):
            ET.SubElement(el, 'data', key=kid).text = n[field]
    for e in edges:
        el = ET.SubElement(graph, 'edge', source=e['source_id'], target=e['target_id'])
        for kid, field in (('d5', 'reasoning'), ('d6', 'validation_status'), ('d7', 'evidence')):
            ET.SubElement(el, 'data', key=kid).text = e[field]
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    meta, nodes, edges = build()
    print(json.dumps({k: v for k, v in meta.items() if k not in ('retired_v1_concepts', 'merged_v1_concepts')}, indent=2))
    for n in nodes:
        if n['kind'] == 'taught' and not (n['name_en_in_text'] and n['name_hi_in_text']):
            print('NAME NOT FOUND', n['id'], n['name_en'], n['name_en_in_text'], n['name_hi'], n['name_hi_in_text'])
        if n['kind'] == 'taught' and (not n['mentions_en'] or not n['mentions_hi']):
            print('NO MENTIONS', n['id'], n['name_en'], n['mentions_en'], n['mentions_hi'])
