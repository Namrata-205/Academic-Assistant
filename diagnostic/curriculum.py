"""Shared curriculum metadata and compatibility names for stable concept IDs."""
CHAPTERS = [
 ('CH01','Patterns in Mathematics','गणित में पैटर्न'),
 ('CH02','Lines and Angles','रेखाएँ और कोण'),
 ('CH03','Number Play','संख्याओं का खेल'),
 ('CH04','Data Handling and Presentation','आँकड़ों का प्रबंधन और प्रस्तुतीकरण'),
 ('CH05','Prime Time','अभाज्य समय'),
 ('CH06','Perimeter and Area','परिमाप और क्षेत्रफल'),
 ('CH07','Fractions','भिन्न'),
 ('CH08','Playing with Constructions','रचनाओं के साथ खेलना'),
 ('CH09','Symmetry','सममिति'),
 ('CH10','The Other Side of Zero','शून्य के दूसरी ओर'),
]
ALIASES = {
 'number sequence':'sequence','odd numbers':'odd number','even numbers':'even number',
 'triangular numbers':'triangular number','square numbers':'square number','cube numbers':'cube number',
 'Virahānka numbers':'Virahanka numbers','consecutive numbers':'consecutive number',
 'counting numbers':'natural number','regular polygons':'regular polygon',
 'shape sequences':'shape pattern','visualising number sequences':'visual pattern',
 'vertex of an angle':'vertex','arms of an angle':'arm of angle',
 'angle as amount of turn':'rotation','complete angle (full turn)':'complete angle',
 'degree (angle measure)':'degree','perpendicular lines':'perpendicular',
 'palindromic numbers':'palindrome','Kaprekar constant (6174)':'Kaprekar number',
 'whole numbers':'number',
}


def teaching_name(name):
    return ALIASES.get(name,name)


def search_terms(node):
    names=[node['en'],node['hi'],teaching_name(node['en']),node['en'].split('(')[0].strip()]
    names.extend(name[:-1] for name in list(names) if name.endswith('s') and not name.endswith('ss'))
    return list(dict.fromkeys(names))


def chapters():
    return [dict(id=cid,en=en,hi=hi) for cid,en,hi in CHAPTERS]
