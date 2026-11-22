const labels={en:{simpler:'Simpler explanation',another_example:'Show another example',still_confused:'I still don’t understand',language_help:'Explain the terms'},hi:{simpler:'सरल भाषा में समझाइए',another_example:'एक और उदाहरण',still_confused:'अभी भी समझ नहीं आया',language_help:'शब्दों का अर्थ समझाइए'}};
export function displayUserText(text,language){
  if(text==='__angle_compare__')return language==='hi'?'कोणों की तुलना करें':'Compare angles';
  if(text?.startsWith('__feedback__:'))return (labels[language]||labels.en)[text.split(':')[1]]||text;
  if(text==='Explain now'&&language==='hi')return 'अभी समझाइए';
  return text;
}
