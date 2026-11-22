"""Original ten-chapter practice and graded exam templates; human review pending."""
import math
import random
from fractions import Fraction
from uuid import uuid4
from diagnostic.curriculum_content import fact


def label(cid,nodes,lang):
    value=nodes[cid][lang]
    return value+' (6174)' if cid=='MATH6_C0050' and '6174' not in value else value


def make(cid,nodes,seed=0,level=1,mcq=False):
    if cid not in nodes:return None
    rng=random.Random(seed);code=cid.removeprefix('MATH6_C');a=rng.randint(3,9);b=rng.randint(2,5)
    if code=='0179' and a==b:a+=1
    en=hi=key=why_en=why_hi=None;kind='numeric'
    def numeric(e,h,k,we=None,wh=None):
        return e,h,str(k),we or str(k),wh or str(k)
    def choice(e,h,answer,options,we,wh):
        options=list(dict.fromkeys([str(answer),*[str(o) for o in options]]))
        if len(options)<4:return None
        rng.shuffle(options);options=options[:4] if str(answer) in options[:4] else [str(answer),*options[:3]]
        rng.shuffle(options);letter='ABCD'[options.index(str(answer))]
        return e+' '+ '; '.join(f'{l}: {o}' for l,o in zip('ABCD',options)),h+' '+ '; '.join(f'{l}: {o}' for l,o in zip('ABCD',options)),letter,we,wh
    value=None
    if code in ('0046','0047'):
        value=numeric(f'Calculate {a+b} '+('+' if code=='0046' else '−')+f' {b}.',f'{a+b} '+('+' if code=='0046' else '−')+f' {b} निकालें।',a+2*b if code=='0046' else a)
    elif code=='0021':
        letter=chr(75+seed%12);other=chr(ord(letter)+1);third=chr(ord(letter)+2)
        value=choice(f'Rays {letter}{other} and {letter}{third} begin at the same point. Which point is the vertex?',f'किरणें {letter}{other} और {letter}{third} एक ही बिंदु से शुरू होती हैं। शीर्ष कौन-सा बिंदु है?',letter,[other,third,'A'],f'Both rays start at {letter}; that shared endpoint is the vertex.',f'दोनों किरणें {letter} से शुरू होती हैं। वही साझा अंतिम बिंदु शीर्ष है।');kind='mcq'
    elif code in ('0101','0102','0103','0143'):
        if code=='0101':value=numeric(f'Which is greater: {a*10+b} or {b*10+a}?',f'{a*10+b} और {b*10+a} में कौन बड़ी है?',max(a*10+b,b*10+a))
        elif code=='0102':value=numeric(f'There are {a} groups of {b} counters. How many counters?',f'{b} गोटियों के {a} समूह हैं। कुल गोटियाँ कितनी हैं?',a*b,f'{a} × {b} = {a*b}',f'{a} × {b} = {a*b}')
        elif code=='0103':value=numeric(f'Share {a*b} counters equally among {b} children. How many each?',f'{a*b} गोटियाँ {b} बच्चों में बराबर बाँटें। हर बच्चे को कितनी मिलेंगी?',a,f'{a*b} ÷ {b} = {a}',f'{a*b} ÷ {b} = {a}')
        else:value=numeric(f'Convert {a} metres to centimetres.',f'{a} मीटर को सेंटीमीटर में बदलें।',a*100,f'{a} × 100 = {a*100}',f'{a} × 100 = {a*100}')
    elif code in ('0104','0105','0106','0107','0108','0109','0112','0113','0114','0049'):
        if code=='0104':
            n=b;key=3*n*(n-1)+1;value=numeric(f'The hexagonal sequence follows 3n(n−1)+1. Find term n={n}.',f'षड्भुजीय अनुक्रम का नियम 3n(n−1)+1 है। n={n} का पद निकालें।',key)
        elif code=='0105':value=numeric(f'Find the sum of the first {a} positive odd numbers.',f'पहली {a} धन विषम संख्याओं का योग निकालें।',a*a,f'The sum is {a} × {a} = {a*a}.',f'योग {a} × {a} = {a*a} है।')
        elif code=='0106':value=numeric(f'Join every pair of {b+1} distinct points once. How many edges?',f'{b+1} अलग बिंदुओं के हर जोड़े को एक बार जोड़ें। किनारे कितने होंगे?',b*(b+1)//2)
        elif code=='0107':value=numeric(f'Stack square layers containing 1², 2², …, {b}² dots. Find the total.',f'1², 2², …, {b}² बिंदुओं वाली वर्गाकार परतें जमाएँ। कुल बिंदु निकालें।',sum(i*i for i in range(1,b+1)))
        elif code=='0108':value=numeric(f'Stack the first {b} triangular layers, where layer n has n(n+1)/2 dots. Find the total.',f'पहली {b} त्रिभुजाकार परतें जमाएँ। nवीं परत में n(n+1)/2 बिंदु हैं। कुल बिंदु निकालें।',sum(i*(i+1)//2 for i in range(1,b+1)))
        elif code=='0109':
            stage=level+seed%3
            value=numeric(f'A Koch pattern has {3*4**(stage-1)} segments. Each is replaced by four segments. How many now?',f'कोख पैटर्न के {3*4**(stage-1)} रेखाखंडों में से हर एक की जगह चार रेखाखंड बनते हैं। अब कुल कितने होंगे?',3*4**stage)
        elif code=='0112':value=numeric(f'On a 12-hour clock, what number is shown {b} hours after {a} o’clock?',f'12 घंटे की घड़ी पर {a} बजे के {b} घंटे बाद कौन-सी संख्या दिखेगी?',(a+b-1)%12+1)
        elif code=='0113':value=numeric(f'Calculate {10*a+2} + 9 mentally.',f'{10*a+2} + 9 का मौखिक हिसाब करें।',10*a+11,'Add 10, then subtract 1.','10 जोड़ें, फिर 1 घटाएँ।')
        elif code=='0114':value=numeric(f'A game ends at {a*3}. Players may add 1 or 2. You are at {a*3-2}. What should you add to win now?',f'खेल {a*3} पर समाप्त होता है। हर चाल में 1 या 2 जोड़ सकते हैं। आप {a*3-2} पर हैं। अभी जीतने के लिए कितना जोड़ें?',2)
        else:value=numeric(f'Add the integers from 1 to {2*a} by pairing the ends.',f'सिरों के जोड़े बनाकर 1 से {2*a} तक की पूर्ण संख्याएँ जोड़ें।',a*(2*a+1))
    elif code in ('0116','0117','0118','0119','0120','0121','0122','0123'):
        if code=='0116':value=numeric(f'There are {a} complete groups of five tally marks and {b-1} extra marks. What is the count?',f'मिलान चिह्नों के {a} पूरे पाँच-पाँच के समूह और {b-1} अतिरिक्त चिह्न हैं। कुल संख्या क्या है?',a*5+b-1)
        elif code=='0117':
            data=[a]*b+[a+1]*(b+1)+[a+2];rng.shuffle(data);value=numeric(f'Data: {data}. What is the frequency of {a}?',f'आँकड़े: {data}। {a} की बारंबारता कितनी है?',b)
        elif code=='0118':value=numeric(f'A frequency table has counts {a}, {b}, and {a+b}. Find the total observations.',f'बारंबारता सारणी की गिनतियाँ {a}, {b}, {a+b} हैं। कुल प्रेक्षण कितने हैं?',2*(a+b))
        elif code in ('0119','0120'):value=numeric(f'A pictograph shows {a} symbols. The key is {b} students per symbol. How many students?',f'चित्रालेख में {a} चिह्न हैं। हर चिह्न {b} विद्यार्थी दिखाता है। कुल विद्यार्थी कितने हैं?',a*b,f'{a} × {b} = {a*b}',f'{a} × {b} = {a*b}')
        elif code=='0121':value=numeric(f'A bar is {a} grid units high. The scale is {b} votes per unit. Find the votes.',f'दंड की ऊँचाई {a} ग्रिड इकाई है। पैमाना हर इकाई पर {b} मत है। मत कितने हैं?',a*b)
        elif code=='0122':value=numeric(f'Draw a bar for {a*b} books at {b} books per grid unit. How many units high?',f'हर ग्रिड इकाई पर {b} पुस्तकों के पैमाने से {a*b} पुस्तकों का दंड बनाएँ। ऊँचाई कितनी इकाई होगी?',a)
        else:value=numeric(f'A horizontal bar is {a} units long and represents {a*b} items. How many items per unit?',f'आड़ा दंड {a} इकाई लंबा है और {a*b} वस्तुएँ दिखाता है। प्रति इकाई कितनी वस्तुएँ हैं?',b)
    elif code in {f'{i:04}' for i in range(125,140)}:
        if code=='0125':value=numeric(f'Find the {b}th positive multiple of {a}.',f'{a} का {b}वाँ धन गुणज निकालें।',a*b)
        elif code=='0126':value=numeric(f'Find the {level}th positive common multiple of {a} and {b}.',f'{a} और {b} का {level}वाँ धन सार्व गुणज निकालें।',math.lcm(a,b)*level)
        elif code=='0127':
            n=a*b;factors=[x for x in range(1,n+1) if n%x==0];value=numeric(f'How many positive factors does {n} have?',f'{n} के कितने धन गुणनखंड हैं?',len(factors),str(factors),str(factors))
        elif code=='0128':value=numeric(f'Find the greatest common factor of {a*b} and {a*(b+1)}.',f'{a*b} और {a*(b+1)} का सबसे बड़ा सार्व गुणनखंड निकालें।',a)
        elif code in ('0129','0130','0131','0134','0137','0138','0139'):
            n=rng.choice([6,12,28,18,20,496]) if code=='0129' else a*b+rng.randrange(3)
            prime=n>1 and all(n%d for d in range(2,math.isqrt(n)+1))
            if code=='0129':e=f'Is {n} a perfect number?';h=f'क्या {n} परिपूर्ण संख्या है?';yes=sum(d for d in range(1,n) if n%d==0)==n
            elif code=='0130':e=f'Is {n} prime?';h=f'क्या {n} अभाज्य है?';yes=prime
            elif code=='0131':e=f'Is {n} composite?';h=f'क्या {n} भाज्य है?';yes=n>1 and not prime
            elif code=='0134':e=f'Are {n} and {a} co-prime?';h=f'क्या {n} और {a} सह-अभाज्य हैं?';yes=math.gcd(n,a)==1
            else:
                divisor=rng.choice([2,5,10]) if code=='0138' else rng.choice([4,8]) if code=='0139' else b
                e=f'Is {n} divisible by {divisor}?';h=f'क्या {n}, {divisor} से विभाज्य है?';yes=n%divisor==0
            kind='mcq';good='Yes' if yes else 'No';hgood='हाँ' if yes else 'नहीं'
            options=[('Yes','हाँ'),('No','नहीं')];rng.shuffle(options)
            explanation=fact(cid)
            if code in ('0130','0131','0129'):
                factors=[d for d in range(1,n+1) if n%d==0]
                details=f'Positive factors of {n}: '+', '.join(map(str,factors))+'. '
                details_hi=f'{n} के धन गुणनखंड: '+', '.join(map(str,factors))+'। '
                explanation=(details+explanation[0],details_hi+explanation[1])
            elif code=='0134':explanation=(f'The greatest common factor is {math.gcd(n,a)}. '+explanation[0],f'सबसे बड़ा सार्व गुणनखंड {math.gcd(n,a)} है। '+explanation[1])
            else:explanation=(f'{n} ÷ {divisor} leaves remainder {n%divisor}. '+explanation[0],f'{n} को {divisor} से भाग देने पर शेष {n%divisor} है। '+explanation[1])
            value=(e+' '+ '; '.join(f'{l}: {o[0]}' for l,o in zip('ABCD',options)),h+' '+ '; '.join(f'{l}: {o[1]}' for l,o in zip('ABCD',options)),'ABCD'[[o[0] for o in options].index(good)],explanation[0],explanation[1])
        elif code=='0132':
            limit=a+10;primes=[n for n in range(2,limit+1) if all(n%d for d in range(2,math.isqrt(n)+1))];value=numeric(f'Use the sieve from 2 to {limit}. How many primes remain?',f'2 से {limit} तक छलनी लगाएँ। कितनी अभाज्य संख्याएँ बचेंगी?',len(primes),str(primes),str(primes))
        elif code=='0133':
            p=rng.choice([3,5,11,17,29,41]);value=numeric(f'{p} and a larger prime are twin primes. Find the larger prime.',f'{p} और उससे बड़ी एक अभाज्य संख्या जुड़वाँ अभाज्य हैं। बड़ी संख्या निकालें।',p+2)
        elif code=='0135':
            x=level+1;y=b-1;n=2**x*3**y;value=numeric(f'Write {n} as prime factors. How many factors appear, counting repetitions?',f'{n} का अभाज्य गुणनखंडन करें। दोहराव गिनकर कुल कितने अभाज्य गुणनखंड हैं?',x+y,' × '.join(['2']*x+['3']*y),' × '.join(['2']*x+['3']*y))
        elif code=='0136':value=numeric(f'Find the smallest prime factor of {a*6}.',f'{a*6} का सबसे छोटा अभाज्य गुणनखंड निकालें।',2)
    elif code in {f'{i:04}' for i in range(150,165)}:
        l=a+level*b;w=b
        if code in ('0150','0151'):value=numeric(f'A rectangle is {l} cm long and {w} cm wide. Find its perimeter in cm.',f'आयत की लंबाई {l} सेमी और चौड़ाई {w} सेमी है। परिमाप सेमी में निकालें।',2*(l+w),f'2 × ({l} + {w}) = {2*(l+w)}',f'2 × ({l} + {w}) = {2*(l+w)}')
        elif code=='0152':value=numeric(f'A square has side {l} cm. Find its perimeter in cm.',f'वर्ग की भुजा {l} सेमी है। परिमाप सेमी में निकालें।',4*l)
        elif code in ('0153','0154'):value=numeric(f'An equilateral triangle has side {l} cm. Find its perimeter in cm.',f'समबाहु त्रिभुज की भुजा {l} सेमी है। परिमाप सेमी में निकालें।',3*l)
        elif code=='0155':value=numeric(f'A regular polygon has {b+2} sides of {a} cm. Find its perimeter in cm.',f'सम बहुभुज की {b+2} भुजाएँ हैं, हर भुजा {a} सेमी है। परिमाप सेमी में निकालें।',(b+2)*a)
        elif code in ('0156','0158'):value=numeric(f'A rectangle is {l} cm by {w} cm. Find its area in square cm.',f'आयत के माप {l} सेमी और {w} सेमी हैं। क्षेत्रफल वर्ग सेमी में निकालें।',l*w,f'{l} × {w} = {l*w}',f'{l} × {w} = {l*w}')
        elif code=='0157':value=numeric(f'{a*b} non-overlapping unit squares cover a surface. Find the area in square units.',f'{a*b} बिना चढ़ाव वाले इकाई वर्ग सतह ढकते हैं। क्षेत्रफल वर्ग इकाई में निकालें।',a*b)
        elif code=='0159':value=numeric(f'A square has side {l} cm. Find its area in square cm.',f'वर्ग की भुजा {l} सेमी है। क्षेत्रफल वर्ग सेमी में निकालें।',l*l)
        elif code=='0160':value=numeric(f'A grid shape covers {a} whole unit squares and {2*b} half-squares. Find its area in square units.',f'ग्रिड आकृति {a} पूरे इकाई वर्ग और {2*b} आधे वर्ग ढकती है। क्षेत्रफल वर्ग इकाई में निकालें।',a+b)
        elif code=='0161':value=numeric(f'Each tangram set has 7 pieces. How many pieces are in {b} complete sets?',f'हर टैंग्राम में 7 टुकड़े हैं। {b} पूरे सेटों में कितने टुकड़े होंगे?',7*b)
        elif code=='0162':value=numeric(f'Rectangles {a+3} by {b} and {a+2} by {b+1} have the same perimeter. Find the second area minus the first.',f'{a+3} गुणा {b} और {a+2} गुणा {b+1} माप वाले आयतों के परिमाप बराबर हैं। दूसरे क्षेत्रफल में से पहला घटाएँ।',(a+2)*(b+1)-(a+3)*b)
        elif code=='0163':value=numeric(f'A rectangle is {2*a} cm by {b} cm. A diagonal splits it into two equal-area triangles. Find one triangle area in square cm.',f'आयत {2*a} सेमी गुणा {b} सेमी है। विकर्ण उसे बराबर क्षेत्रफल वाले दो त्रिभुजों में बाँटता है। एक त्रिभुज का क्षेत्रफल वर्ग सेमी में निकालें।',a*b)
        else:value=numeric(f'Two non-overlapping rectangles have areas {a*b} and {a*(b+1)} square units. Find the combined area.',f'बिना चढ़ाव वाले दो आयतों के क्षेत्रफल {a*b} और {a*(b+1)} वर्ग इकाई हैं। कुल क्षेत्रफल निकालें।',a*(2*b+1))
    elif code in {f'{i:04}' for i in range(170,184)}:
        denominator=a+b;numerator=b
        if code=='0172':value=numeric(f'Share {a*b} equal counters among {b} children equally. How many per child?',f'{a*b} गोटियाँ {b} बच्चों में बराबर बाँटें। प्रति बच्चा कितनी?',a)
        elif code=='0174':value=numeric(f'In the fraction {numerator}/{denominator}, what is the denominator?',f'भिन्न {numerator}/{denominator} का हर क्या है?',denominator)
        elif code=='0176':value=numeric(f'Write {a} and {b}/{denominator} as an improper fraction with denominator {denominator}. Find its numerator.',f'{a} और {b}/{denominator} को {denominator} हर वाली भिन्न में बदलें। अंश निकालें।',a*denominator+b)
        elif code=='0177':value=numeric(f'Complete: {b}/{denominator} = ?/{denominator*level*2}.',f'पूरा करें: {b}/{denominator} = ?/{denominator*level*2}।',b*level*2)
        elif code=='0178':value=numeric(f'Reduce {a*b}/{a*(b+1)} to lowest terms. What is its numerator?',f'{a*b}/{a*(b+1)} को सरलतम रूप में लिखें। अंश क्या है?',b)
        else:
            if code=='0171':answer=Fraction(1,denominator);e=f'One whole is cut into {denominator} equal parts. What fraction is one part?';h=f'पूर्ण को {denominator} बराबर भागों में बाँटा है। एक भाग कौन-सी भिन्न है?'
            elif code=='0175':answer=Fraction(b,denominator);e=f'Divide the interval from 0 to 1 into {denominator} equal parts. Which fraction is at mark {b} after 0?';h=f'0 से 1 को {denominator} बराबर भागों में बाँटें। 0 के बाद {b}वें निशान पर कौन-सी भिन्न है?'
            elif code=='0179':answer=max(Fraction(a,denominator),Fraction(b,denominator));e=f'Which is greater: {a}/{denominator} or {b}/{denominator}?';h=f'{a}/{denominator} और {b}/{denominator} में कौन बड़ी है?'
            elif code in ('0180','0182','0183'):answer=Fraction(1,a)+Fraction(1,a+b);e=f'Find 1/{a} + 1/{a+b}.';h=f'1/{a} + 1/{a+b} निकालें।'
            elif code=='0181':answer=Fraction(1,b)-Fraction(1,a+b);e=f'Find 1/{b} − 1/{a+b}.';h=f'1/{b} − 1/{a+b} निकालें।'
            else:answer=Fraction(b,denominator);e=f'{b} of {denominator} equal parts are shaded. What fraction is shaded?';h=f'{denominator} बराबर भागों में से {b} रंगे हैं। रंगा भाग कौन-सी भिन्न है?'
            value=choice(e,h,str(answer),[str(answer+Fraction(i,denominator*(a+b))) for i in range(1,4)],fact(cid)[0],fact(cid)[1]);kind='mcq'
    elif code in ('0190','0191','0192','0195','0196','0197'):
        if code=='0190':value=numeric(f'A circle has radius {a} cm. What is its diameter in cm?',f'वृत्त की त्रिज्या {a} सेमी है। व्यास सेमी में कितना है?',2*a)
        elif code=='0191':value=numeric(f'A circle has diameter {2*a} cm. Find its radius in cm.',f'वृत्त का व्यास {2*a} सेमी है। त्रिज्या सेमी में निकालें।',a)
        elif code=='0192':value=numeric(f'You need a circle of radius {a} cm. What compass opening in cm should you use?',f'{a} सेमी त्रिज्या का वृत्त बनाने के लिए परकार का खुलाव कितने सेमी रखें?',a)
        elif code=='0195':value=numeric(f'A rectangle has one long side {a+b} cm. How long is the opposite side in cm?',f'आयत की लंबी भुजा {a+b} सेमी है। सामने की भुजा कितने सेमी है?',a+b)
        elif code=='0196':value=numeric(f'A rectangle measuring {a} cm by {b} cm is drawn. How many diagonals does it have?',f'{a} सेमी गुणा {b} सेमी का आयत है। उसके कितने विकर्ण हैं?',2)
        else:value=numeric(f'P is equally distant from A and B. PA is {a} cm. Find PB in cm.',f'P की A और B से दूरियाँ बराबर हैं। PA का माप {a} सेमी है। PB सेमी में निकालें।',a)
    elif code in ('0200','0201','0202','0203','0205'):
        if code in ('0200','0202'):value=numeric(f'A non-square rectangle is {a+b} cm by {b} cm. How many lines of symmetry?',f'{a+b} सेमी गुणा {b} सेमी का आयत वर्ग नहीं है। उसकी कितनी सममिति रेखाएँ हैं?',2)
        elif code=='0201':value=numeric(f'A square has side {a} cm. How many lines of symmetry?',f'वर्ग की भुजा {a} सेमी है। उसकी कितनी सममिति रेखाएँ हैं?',4)
        else:
            sides=rng.choice([3,4,6,8]);value=numeric(f'A regular {sides}-sided polygon turns about its centre. '+('Find its rotational order.' if code=='0203' else 'Find its smallest positive angle of symmetry in degrees.'),f'सम {sides}-भुज अपने केंद्र के चारों ओर घूमता है। '+('घूर्णन क्रम निकालें।' if code=='0203' else 'सबसे छोटा धन सममिति कोण अंश में निकालें।'),sides if code=='0203' else 360//sides)
    elif code in {f'{i:04}' for i in range(210,221)}:
        if code=='0210':value=numeric(f'How many positive numbers are in [{a}, 0, −{b}, {a+b}]?',f'[{a}, 0, −{b}, {a+b}] में कितनी धन संख्याएँ हैं?',2)
        elif code=='0211':value=numeric(f'How many negative numbers are in [−{a}, {b}, 0, −{a+b}]?',f'[−{a}, {b}, 0, −{a+b}] में कितनी ऋण संख्याएँ हैं?',2)
        elif code=='0212':value=numeric(f'Find the additive inverse of {a}.',f'{a} का योगात्मक प्रतिलोम निकालें।',-a)
        elif code=='0213':value=numeric(f'How many integers are in [−{a}, 0, {b}, 1/2]?',f'[−{a}, 0, {b}, 1/2] में कितने पूर्णांक हैं?',3)
        elif code=='0214':value=numeric(f'Which is greater: −{a+b} or −{b}?',f'−{a+b} और −{b} में कौन बड़ा है?',-b)
        elif code=='0215':value=numeric(f'Calculate (−{a}) + {b}.',f'(−{a}) + {b} निकालें।',b-a)
        elif code in ('0216','0220'):value=numeric(f'Calculate {a} − (−{b}).',f'{a} − (−{b}) निकालें।',a+b,f'Subtracting −{b} means adding {b}.',f'−{b} घटाने का अर्थ {b} जोड़ना है।')
        elif code=='0217':value=numeric(f'How many unit steps to the right take you from −{a} to {b}?',f'−{a} से {b} तक पहुँचने के लिए दाईं ओर कितने इकाई कदम लें?',a+b)
        elif code=='0218':value=numeric(f'Cancel zero pairs among {a} positive and {b} negative tokens. What integer remains?',f'{a} धन और {b} ऋण टोकनों के शून्य युग्म हटाएँ। कौन-सा पूर्णांक बचता है?',a-b)
        else:value=numeric(f'Temperature starts at −{a}°C and rises by {b}°C. Find the final temperature.',f'तापमान −{a}°C से {b}°C बढ़ता है। अंतिम तापमान निकालें।',b-a)
    if value:
        en,hi,key,why_en,why_hi=value
        if kind=='numeric' and mcq:
            value=choice(en,hi,key,[str(int(key)+i) for i in (1,2,3)],why_en,why_hi)
            en,hi,key,why_en,why_hi=value;kind='mcq'
    else:
        info=fact(cid)
        if not info:return None
        peers=[other for other in nodes if fact(other) and nodes[other]['chapter']==nodes[cid]['chapter'] and other!=cid]
        peers+= [other for other in nodes if fact(other) and other!=cid and other not in peers]
        rng.shuffle(peers);choices=[cid,*peers[:3]];rng.shuffle(choices)
        key='ABCD'[choices.index(cid)];kind='mcq'
        if seed%2:
            en=f'Which concept is described here? {info[0]}';hi=f'यह किस अवधारणा का वर्णन है? {info[1]}'
            en+=' '+ '; '.join(f'{l}: {label(c,nodes,"en")}' for l,c in zip('ABCD',choices));hi+=' '+ '; '.join(f'{l}: {label(c,nodes,"hi")}' for l,c in zip('ABCD',choices))
        else:
            en=f'Which statement describes {label(cid,nodes,"en")}?';hi=f'{label(cid,nodes,"hi")} का सही वर्णन कौन-सा है?'
            en+=' '+ '; '.join(f'{l}: {fact(c)[0]}' for l,c in zip('ABCD',choices));hi+=' '+ '; '.join(f'{l}: {fact(c)[1]}' for l,c in zip('ABCD',choices))
        why_en,why_hi=info
    return dict(id='curriculum-'+uuid4().hex,concept_id=cid,concept_en=nodes[cid]['en'],concept_hi=nodes[cid]['hi'],
        en=en,hi=hi,type=kind,answer=str(key),feedback_en=why_en,feedback_hi=why_hi,
        difficulty=level,format=kind,review_status='PENDING',source_references=[],
        scoring_rule='Exact numeric or option-letter key; other input unscorable.',
        possible_difficulty='One original practice observation; not a diagnosis.',
        provenance='Original curriculum-v2 teaching draft; teacher review pending.')
