"""Worked explanations for the original learning-check bank."""
import re


def explanation(question, language):
    saved = question.get('feedback_' + language)
    if saved:
        return saved

    key = question['answer']
    from diagnostic.curriculum import teaching_name
    topic = teaching_name(question.get('concept_en',''))
    numbers = [int(n) for n in re.findall(r'\d+', question['en'])]
    hi = language == 'hi'
    if topic == 'number pattern' and len(numbers) >= 4:
        first, second, third, last = numbers[:4]
        if second == 2 * first and third == 2 * second and last == 2 * third:
            return f'हर बार 2 से गुणा करें। {last} × 2 = {key}।' if hi else f'Double each term. {last} × 2 = {key}.'
        step = second - first
        sign = '+' if step > 0 else '−'
        equation = f'{last} {sign} {abs(step)} = {key}'
        return f'क्रम में हर बार {abs(step)} {"जोड़ें" if step > 0 else "घटाएँ"}। {equation}।' if hi else f'Apply the same change each time. {equation}.'
    if topic in ('odd number', 'even number') and len(numbers) == 4 and key in 'ABCD':
        number = numbers['ABCD'.index(key)]
        return (f'{number} को 2 से भाग देने पर शेष {number % 2} है। इसलिए विकल्प {key} सही है।' if hi
                else f'{number} ÷ 2 leaves remainder {number % 2}. That makes option {key} the {topic}.')
    if topic == 'square number' and numbers:
        side = numbers[0] if key.isdecimal() else int(numbers['ABCD'.index(key)] ** .5)
        return (f'वर्ग संख्या के लिए संख्या को उसी से गुणा करें। {side} × {side} = {side * side}।' if hi
                else f'Multiply the side by itself. {side} × {side} = {side * side}.')
    if topic == 'place value' and len(numbers) >= 2:
        digit = numbers[0]
        if digit:
            place = int(key) // digit
            return (f'स्थानीय मान के लिए {digit} को {place} से गुणा करें। {digit} × {place} = {key}।' if hi
                    else f'Each unit in that place is worth {place}. Multiply {digit} × {place} = {key}.')
    if topic == 'digit sum' and numbers:
        addition = ' + '.join(str(numbers[0]))
        return f'हर अंक को जोड़ें। {addition} = {key}।' if hi else f'Add the individual digits. {addition} = {key}.'

    geometry = {
        'line segment': ('A line segment stops at both ends, so it has two endpoints and a fixed length.',
                         'रेखाखंड के दो निश्चित अंत बिंदु होते हैं। इसलिए इसकी लंबाई निश्चित होती है।'),
        'angle': ('An angle is made of two rays. Their common endpoint is the vertex, and the rays are its arms.',
                  'कोण दो किरणों से बनता है। उनका साझा अंत बिंदु शीर्ष है और किरणें उसकी भुजाएँ हैं।'),
        'right angle': ('A right angle is one quarter of a full turn. 360° ÷ 4 = 90°.',
                        'समकोण एक पूरे घुमाव का चौथाई भाग है। 360° ÷ 4 = 90°।'),
        'acute angle': ('Compare each measure with 0° and 90°. An acute angle is strictly between those bounds.',
                        'हर माप की तुलना 0° और 90° से करें। न्यून कोण इन दोनों के बीच होता है।'),
    }
    if topic in geometry:
        return geometry[topic][hi]
    return f'सही उत्तर {key} है।' if hi else f'The correct answer is {key}.'
