export const questionCopy={
  en:{progress:'Question',concept:'Practising',answer:'Your answer',choose:'Choose your answer',placeholder:'Enter a number',unsure:"I’m not sure",next:'Continue',stop:'Want to stop here?',stopHint:'You can see the evidence collected so far. Some ideas may remain unassessed.',finish:'Finish and see results'},
  hi:{progress:'प्रश्न',concept:'अभ्यास',answer:'आपका उत्तर',choose:'अपना उत्तर चुनिए',placeholder:'संख्या लिखिए',unsure:'मुझे नहीं पता',next:'आगे बढ़ें',stop:'क्या आप यहीं रुकना चाहते हैं?',stopHint:'अब तक दिए गए उत्तरों का परिणाम देख सकते हैं। कुछ अवधारणाओं का आकलन नहीं हुआ होगा।',finish:'समाप्त करें और परिणाम देखें'},
};
export function questionText(question,language){return language==='hi'?(question.hi||question.en):question.en;}
