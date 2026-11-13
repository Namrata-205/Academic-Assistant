export async function studentApi(path,body){
  const response=await fetch('/api'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Please try again.');return data;
}
export function currentLearner(){let code=localStorage.getItem('atlas-learner-code');if(!code){code='learner-'+crypto.randomUUID();localStorage.setItem('atlas-learner-code',code);}return code;}
