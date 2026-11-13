"""Server-only Gemini configuration and REST generation; no learner records."""
import json
import os
import re
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
from diagnostic.engine import ROOT

DEFAULT_GEMINI_MODEL='gemini-3.5-flash-lite'
ENV_NAMES={'GEMINI_API_KEY','GOOGLE_API_KEY','ATLAS_CHAT_PROVIDER','ATLAS_CHAT_MODEL'}


class ProviderError(RuntimeError):pass


def configuration(env_path=None):
    """Simple KEY=value .env entries; process environment wins, no interpolation."""
    path=env_path if env_path is not None else ROOT/'.env';values={}
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line:continue
            name,value=line.removeprefix('export ').split('=',1);name=name.strip();value=value.strip()
            if name not in ENV_NAMES:continue
            if len(value)>=2 and value[0]==value[-1] and value[0] in '\"\'':value=value[1:-1]
            values[name]=value
    for name in ENV_NAMES:
        if name in os.environ:values[name]=os.environ[name]
    return values


def gemini_generate(system,prompt,model,key,schema=None,max_output_tokens=3072):
    if not key:raise ProviderError('missing_api_key')
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+',model):raise ProviderError('invalid_model_name')
    schema=schema or {'type':'object','properties':{'paragraphs':{'type':'array','maxItems':6,
        'items':{'type':'object','properties':{'text':{'type':'string'},
            'citations':{'type':'array','items':{'type':'string'}},'evidence':{'type':'string'}},
            'required':['text','citations','evidence']}}},'required':['paragraphs']}
    body={'systemInstruction':{'parts':[{'text':system}]},
          'contents':[{'role':'user','parts':[{'text':prompt}]}],
          'generationConfig':{'temperature':0,'maxOutputTokens':max_output_tokens,
                              'responseMimeType':'application/json','responseJsonSchema':schema}}
    request=Request('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',
                    data=json.dumps(body,ensure_ascii=False).encode('utf-8'),
                    headers={'Content-Type':'application/json','x-goog-api-key':key})
    try:
        with urlopen(request,timeout=45) as response:raw=json.loads(response.read(1024*1024))
    except HTTPError as error:
        code={400:'invalid_request',401:'authentication_failed',403:'permission_denied',
              404:'model_unavailable',429:'quota_or_rate_limit'}.get(error.code,'provider_error')
        raise ProviderError(code) from None
    except (URLError,TimeoutError,OSError):raise ProviderError('network_or_timeout') from None
    candidates=raw.get('candidates',[])
    if not candidates or candidates[0].get('finishReason')!='STOP':raise ProviderError('blocked_or_incomplete_response')
    text=''.join(p.get('text','') for p in candidates[0].get('content',{}).get('parts',[]) if not p.get('thought'))
    try:return json.loads(text)
    except (ValueError,TypeError):raise ProviderError('invalid_json_response') from None
