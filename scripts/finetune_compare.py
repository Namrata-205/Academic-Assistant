"""Run a real, small GPU comparison. All checkpoints remain local and ignored."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import sys
import time
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
MODEL='Qwen/Qwen3-0.6B'
SEED=42


def write(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def download(args):
    from huggingface_hub import HfApi,snapshot_download
    if (args.root/'base_manifest.json').exists():raise FileExistsError('Base model revision is already frozen.')
    revision=HfApi().model_info(MODEL).sha
    args.base.mkdir(parents=True,exist_ok=True)
    snapshot_download(MODEL,revision=revision,local_dir=str(args.base),
                      allow_patterns=['*.json','*.safetensors','*.jinja','LICENSE','*.txt'],max_workers=2)
    manifest={'model':MODEL,'revision':revision,'files':{p.name:sha(p) for p in args.base.iterdir() if p.is_file()}}
    write(args.root/'base_manifest.json',manifest)
    print(json.dumps({'downloaded':MODEL,'revision':revision}),flush=True)


def tokenizer(args):
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(str(args.base),local_files_only=True)
    if tok.pad_token_id is None:tok.pad_token=tok.eos_token
    return tok


def prompt(tok,messages):
    return tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,enable_thinking=False)


def encode(args):
    if (args.root/'encoded_dataset.json').exists():raise FileExistsError('Encoded data is already frozen.')
    tok=tokenizer(args);data=json.loads((args.root/'dataset.json').read_text(encoding='utf-8'))
    encoded={'train':[],'validation':[],'test':data['test']};dropped=[]
    for split in ('train','validation'):
        pending=[]
        for sample in data[split]:
            messages=sample['messages']
            ids=None
            target=tok.encode(sample['target']+tok.eos_token,add_special_tokens=False)
            for limit in (180,120,80,60):
                payload=json.loads(messages[1]['content'])
                payload['sources']=[dict(s,text=s['text'][:limit]) for s in payload['sources']]
                texts=[messages[0],{'role':'user','content':json.dumps(payload,ensure_ascii=False)}]
                prefix=tok.encode(prompt(tok,texts),add_special_tokens=False)
                if len(prefix)+len(target)<=args.max_seq:
                    ids=prefix+target;break
            if ids is None:dropped.append(sample['id']);continue
            pending.append({'id':sample['id'],'family':sample['family'],'language':sample['language'],
                            'input_ids':ids,'labels':[-100]*len(prefix)+target})
        # Keep language pairs together even if one would exceed the token budget.
        for sample in pending:
            partner=sample['id'].replace('-en-','-hi-') if sample['language']=='en' else sample['id'].replace('-hi-','-en-')
            if partner not in {row['id'] for row in pending}:dropped.append(sample['id']);continue
            encoded[split].append(sample)
    if not encoded['train'] or not encoded['validation']:raise ValueError('No paired training/validation data fits the shared token budget.')
    encoded['config']={'seed':SEED,'epochs':1,'max_sequence_tokens':args.max_seq,'micro_batch':1,'gradient_accumulation':4,
                       'learning_rate':1e-4,'optimizer':'bitsandbytes AdamW8bit, all three methods',
                       'lora_rank':8,'lora_alpha':16,'lora_dropout':.05,'training_dtype':'bfloat16',
                       'evaluation_dtype':'bfloat16, including QLoRA adapter on an unquantized base',
                       'generation_max_new_tokens':320,'generation_do_sample':False,
                       'dropped_for_shared_length_or_pairing':sorted(set(dropped)),
                       'dataset_sha256':sha(args.root/'dataset.json')}
    encoded['config']['base_manifest_sha256']=sha(args.root/'base_manifest.json')
    write(args.root/'encoded_dataset.json',encoded)
    print(json.dumps({'train':len(encoded['train']),'validation':len(encoded['validation']),'dropped':len(set(dropped))}),flush=True)


def setup_cuda():
    import torch
    torch.set_num_threads(4)
    if not torch.cuda.is_available():raise RuntimeError('CUDA training is required for this comparison.')
    if not torch.cuda.is_bf16_supported():raise RuntimeError('This experiment requires BF16 support.')
    random.seed(SEED);torch.manual_seed(SEED);torch.cuda.manual_seed_all(SEED)
    return torch


def load_model(args,training=False):
    torch=setup_cuda()
    from transformers import AutoModelForCausalLM,BitsAndBytesConfig
    from peft import LoraConfig,get_peft_model,prepare_model_for_kbit_training,PeftModel
    config={'torch_dtype':torch.bfloat16,'local_files_only':True,'attn_implementation':'sdpa','device_map':{'':0}}
    if training and args.method=='qlora':
        config['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16)
    path=args.checkpoints/'full' if args.method=='full' and not training else args.base
    model=AutoModelForCausalLM.from_pretrained(str(path),**config)
    if training and args.method in ('lora','qlora'):
        if args.method=='qlora':model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,
                                         gradient_checkpointing_kwargs={'use_reentrant':False})
        torch.manual_seed(SEED)
        model=get_peft_model(model,LoraConfig(task_type='CAUSAL_LM',r=8,lora_alpha=16,lora_dropout=.05,
            target_modules=['q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj']))
    elif not training and args.method in ('lora','qlora'):
        model=PeftModel.from_pretrained(model,str(args.checkpoints/args.method),is_trainable=False)
    if training:
        model.config.use_cache=False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
        model.enable_input_require_grads()
    return model


def tensor_sample(torch,sample):
    return {'input_ids':torch.tensor([sample['input_ids']],device='cuda'),
            'attention_mask':torch.ones((1,len(sample['input_ids'])),dtype=torch.long,device='cuda'),
            'labels':torch.tensor([sample['labels']],device='cuda')}


def loss_on(torch,model,samples):
    model.eval();total=0.;tokens=0
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
        for sample in samples:
            n=sum(label!=-100 for label in sample['labels'])
            loss=model(**tensor_sample(torch,sample)).loss
            total+=float(loss)*n;tokens+=n
    return total/tokens


def train(args):
    torch=setup_cuda();import bitsandbytes as bnb
    output=args.root/(args.method+'_training.json')
    if output.exists() or (args.checkpoints/args.method).exists():raise FileExistsError('Refusing to overwrite a training run.')
    data=json.loads((args.root/'encoded_dataset.json').read_text(encoding='utf-8'));model=load_model(args,training=True)
    if hasattr(model,'get_nb_trainable_parameters'):
        trainable,total=model.get_nb_trainable_parameters()
    else:
        total=sum(p.numel() for p in model.parameters());trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)
    if args.method=='full' and trainable!=total:raise AssertionError('Full FT must update every model parameter.')
    if args.method!='full' and trainable>=total:raise AssertionError('Adapter methods must freeze base parameters.')
    before=loss_on(torch,model,data['validation'])
    parameters=[p for p in model.parameters() if p.requires_grad]
    optimizer=bnb.optim.AdamW8bit(parameters,lr=1e-4,betas=(.9,.999),weight_decay=0.)
    samples=list(data['train']);random.Random(SEED).shuffle(samples)
    accumulation=4;model.train();optimizer.zero_grad(set_to_none=True)
    torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();started=time.perf_counter();loss_sum=0.;token_count=0;steps=0
    print(json.dumps({'method':args.method,'trainable':trainable,'total':total,'examples':len(samples),'validation_before':before}),flush=True)
    for i,sample in enumerate(samples):
        group_start=(i//accumulation)*accumulation
        group_size=min(accumulation,len(samples)-group_start)
        with torch.autocast('cuda',dtype=torch.bfloat16):loss=model(**tensor_sample(torch,sample)).loss
        raw=float(loss.detach());n=sum(label!=-100 for label in sample['labels'])
        if not math.isfinite(raw):raise RuntimeError('Non-finite loss; refusing to report a successful run.')
        loss_sum+=raw*n;token_count+=n
        (loss/group_size).backward()
        if (i+1)%accumulation==0 or i+1==len(samples):
            torch.nn.utils.clip_grad_norm_(parameters,1.)
            optimizer.step();optimizer.zero_grad(set_to_none=True);steps+=1
            print(json.dumps({'method':args.method,'step':steps,'examples_seen':i+1,'loss':round(raw,5),
                              'allocated_gib':round(torch.cuda.memory_allocated()/2**30,3)}),flush=True)
    torch.cuda.synchronize();seconds=time.perf_counter()-started
    peak_allocated=torch.cuda.max_memory_allocated()/2**30;peak_reserved=torch.cuda.max_memory_reserved()/2**30
    after=loss_on(torch,model,data['validation'])
    destination=args.checkpoints/args.method;destination.mkdir(parents=True)
    model.save_pretrained(str(destination),safe_serialization=True)
    tokenizer(args).save_pretrained(str(destination))
    metrics={'method':args.method,'status':'completed','examples':len(samples),'epochs':1,'optimizer_steps':steps,
             'total_parameters':total,'trainable_parameters':trainable,'trainable_percent':100*trainable/total,
             'train_seconds':seconds,'peak_allocated_gib':peak_allocated,'peak_reserved_gib':peak_reserved,
             'training_loss':loss_sum/token_count,'validation_loss_before':before,'validation_loss_after':after,
             'validation_precision':'NF4 base for QLoRA; BF16 otherwise. Common-BF16 validation is reported separately at evaluation.',
             'training_base_precision':'4-bit NF4, double quantization' if args.method=='qlora' else 'BF16 (not weight quantized)',
             'optimizer':'AdamW8bit','checkpoint_bytes':sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()),
             'encoded_dataset_sha256':sha(args.root/'encoded_dataset.json'),'config':data['config'],
             'base_manifest_sha256':sha(args.root/'base_manifest.json'),
             'gpu':torch.cuda.get_device_name(),'torch':torch.__version__}
    write(output,metrics);print(json.dumps(metrics),flush=True)


def score_response(raw,sample):
    from diagnostic.book_chat import validate_generation,canonical
    result={'json_valid':False,'source_checked':False,'terminology_present':False,'error':None}
    try:parsed=json.loads(raw);result['json_valid']=True
    except (ValueError,TypeError):result['error']='invalid_json';return result
    try:
        paragraphs=validate_generation(parsed,sample['sources'],sample['language'],sample['terms'])
        result['source_checked']=True;result['terminology_present']=True
    except (ValueError,TypeError,KeyError,AttributeError) as error:
        result['error']=str(error)
        text=' '.join(str(p.get('text','')) for p in parsed.get('paragraphs',[]) if isinstance(p,dict)) if isinstance(parsed,dict) else ''
        label=sample['terms'][0][sample['language']] if sample.get('terms') else ''
        result['terminology_present']=bool(label and canonical(label).casefold() in canonical(text).casefold())
    return result


def strip_single_fence(raw):
    """Secondary formatting diagnostic only: no JSON or content repair."""
    text=raw.strip()
    match=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',text,re.S|re.I)
    return match[1].strip() if match and text.count('```')==2 else text


def evaluate(args):
    torch=setup_cuda();output=args.root/(args.method+'_evaluation.json')
    if output.exists():raise FileExistsError('Refusing to overwrite evaluation results.')
    data=json.loads((args.root/'encoded_dataset.json').read_text(encoding='utf-8'))
    model=load_model(args);model.eval();model.config.use_cache=True;tok=tokenizer(args)
    val_loss=loss_on(torch,model,data['validation']);rows=[]
    # One common, unscored warm-up; latency below excludes model loading.
    warm=tok(prompt(tok,data['test'][0]['messages']),return_tensors='pt').to('cuda')
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
        model.generate(**warm,max_new_tokens=1,do_sample=False,pad_token_id=tok.pad_token_id)
    for sample in data['test']:
        if sample['pipeline_status']!='model':
            rows.append({'id':sample['id'],'language':sample['language'],'pipeline_status':sample['pipeline_status'],
                         'model_called':False,'deterministic_output':sample['deterministic_output']});continue
        inputs=tok(prompt(tok,sample['messages']),return_tensors='pt').to('cuda')
        if inputs['input_ids'].shape[1]>2048:raise ValueError('Shared prompt exceeds frozen evaluation context budget.')
        torch.cuda.synchronize();started=time.perf_counter()
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
            generated=model.generate(**inputs,max_new_tokens=320,do_sample=False,pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize();seconds=time.perf_counter()-started
        continuation=generated[0,inputs['input_ids'].shape[1]:];raw=tok.decode(continuation,skip_special_tokens=True)
        row={'id':sample['id'],'language':sample['language'],'pipeline_status':'model','model_called':True,
             'latency_seconds':seconds,'generated_tokens':len(continuation),'output':raw,
             'prompt_sha256':hashlib.sha256(prompt(tok,sample['messages']).encode('utf-8')).hexdigest(),
             **score_response(raw,sample)}
        rows.append(row);print(json.dumps({'method':args.method,'case':sample['id'],'source_checked':row['source_checked'],'seconds':round(seconds,2)}),flush=True)
    active=[r for r in rows if r['model_called']]
    def summary(subset):
        return {'cases':len(subset),**{k:sum(r[k] for r in subset)/len(subset) if subset else None for k in ('json_valid','source_checked','terminology_present')},
                'json_valid_count':sum(r['json_valid'] for r in subset),'source_checked_count':sum(r['source_checked'] for r in subset),
                'mean_latency_seconds':sum(r['latency_seconds'] for r in subset)/len(subset) if subset else None}
    write(output,{'method':args.method,'status':'completed','evaluation_precision':'BF16 for all methods',
                  'validation_loss_common_precision':val_loss,'summary':summary(active),
                  'by_language':{lang:summary([r for r in active if r['language']==lang]) for lang in ('en','hi')},
                  'deterministic_pipeline_cases':len(rows)-len(active),'encoded_dataset_sha256':sha(args.root/'encoded_dataset.json'),
                  'base_manifest_sha256':sha(args.root/'base_manifest.json'),'rows':rows})


def report(args):
    if (args.root/'comparison.json').exists() or (args.root/'blind_quality_review.csv').exists():
        raise FileExistsError('Preserve previous comparisons and reviews.')
    data=json.loads((args.root/'dataset.json').read_text(encoding='utf-8'));rows=[];review=[]
    for method in ('baseline','lora','qlora','full'):
        evaluation=json.loads((args.root/(method+'_evaluation.json')).read_text(encoding='utf-8'))
        training=json.loads((args.root/(method+'_training.json')).read_text(encoding='utf-8')) if method!='baseline' else {}
        if training and (training['encoded_dataset_sha256']!=evaluation['encoded_dataset_sha256'] or
                         training['base_manifest_sha256']!=evaluation['base_manifest_sha256']):
            raise AssertionError('Training/evaluation model or dataset mismatch')
        rows.append({'method':method,**evaluation['summary'],'validation_loss':evaluation['validation_loss_common_precision'],
                     **{key:training.get(key) for key in ('trainable_parameters','trainable_percent','train_seconds','peak_allocated_gib','checkpoint_bytes')},
                     'by_language':evaluation['by_language']})
        normalized=[]
        for result in evaluation['rows']:
            if result['model_called']:
                sample=next(s for s in data['test'] if s['id']==result['id'])
                normalized.append({'id':result['id'],'language':result['language'],
                                   **score_response(strip_single_fence(result['output']),sample)})
                review.append({'blind_id':hashlib.sha256((method+result['id']).encode()).hexdigest()[:12],
                               'case_id':result['id'],'language':result['language'],'question':sample['question'],
                               'sources':json.dumps(sample['sources'],ensure_ascii=False),'response':result['output'],
                               'math_correctness_1_to_5':'','source_support_1_to_5':'','terminology_1_to_5':'',
                               'difficulty_alignment_1_to_5':'','reviewer':'','notes':''})
        rows[-1]['fence_normalized_secondary']={'cases':len(normalized),
            'json_valid_count':sum(r['json_valid'] for r in normalized),
            'source_checked_count':sum(r['source_checked'] for r in normalized),
            'checks':normalized,
            'interpretation':'Post-hoc formatting diagnostic, uniformly applied to saved outputs; only a single surrounding Markdown fence is removed. Primary strict metrics are unchanged.'}
    # Verify that every model saw byte-identical prompts and the same examples.
    evaluations=[json.loads((args.root/(m+'_evaluation.json')).read_text(encoding='utf-8')) for m in ('baseline','lora','qlora','full')]
    hashes=[[(r['id'],r.get('prompt_sha256')) for r in v['rows']] for v in evaluations]
    if any(h!=hashes[0] for h in hashes[1:]):raise AssertionError('Unfair prompt comparison')
    if len({v['encoded_dataset_sha256'] for v in evaluations})!=1:raise AssertionError('Dataset mismatch')
    if len({v['base_manifest_sha256'] for v in evaluations})!=1:raise AssertionError('Base model mismatch')
    encoded=json.loads((args.root/'encoded_dataset.json').read_text(encoding='utf-8'))
    write(args.root/'comparison.json',{'model':json.loads((args.root/'base_manifest.json').read_text())['model'],
        'model_revision':json.loads((args.root/'base_manifest.json').read_text())['revision'],
        'rows':rows,'config':encoded['config'],
        'data_counts':{'train':len(encoded['train']),'validation':len(encoded['validation']),
                       'model_evaluation':evaluations[0]['summary']['cases'],
                       'deterministic_pipeline':evaluations[0]['deterministic_pipeline_cases'],
                       'training_languages':{lang:sum(r['language']==lang for r in encoded['train']) for lang in ('en','hi')}},
        'same_prompt_hashes':True,'limitations':data['limitations']+[
          'One epoch and one seed with equal learning rate/budget; not separately tuned method optima.',
          'Full FT updates every BF16 model weight with an 8-bit optimizer to fit the 6 GB GPU; it is not adapter tuning.',
          'QLoRA trains on NF4 but is evaluated on BF16 base weights plus its adapter, so inference precision is controlled.',
          'Memory columns are PyTorch peak allocated bytes, not total physical GPU residency. Peak reserved allocator bytes are also recorded; Windows WDDM can use shared system memory.',
          'Latency is generation-only after one unscored warm-up; it excludes model loading, tokenization, retrieval and diagnosis.',
          'Source-checked rate is structural citation/evidence/arithmetic validation, not human mathematical accuracy.']})
    csv_keys=['method','cases','json_valid','source_checked','terminology_present','validation_loss',
              'trainable_parameters','trainable_percent','train_seconds','peak_allocated_gib','checkpoint_bytes','mean_latency_seconds']
    with (args.root/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=csv_keys);writer.writeheader()
        writer.writerows({key:row.get(key) for key in csv_keys} for row in rows)
    random.Random(SEED).shuffle(review)
    review_path=args.root/'blind_quality_review.csv'
    if review_path.exists():raise FileExistsError('Do not overwrite human reviews.')
    with review_path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(review[0]));writer.writeheader();writer.writerows(review)
    mapping=[{'method':method,'case_id':r['id'],'blind_id':hashlib.sha256((method+r['id']).encode()).hexdigest()[:12]}
             for method,v in zip(('baseline','lora','qlora','full'),evaluations) for r in v['rows'] if r['model_called']]
    write(args.root/'blind_review_key.json',mapping)
    lines=['# Local fine-tuning development comparison','',
           'Actual GPU runs of Qwen3-0.6B. Synthetic draft training content; independent human review pending.','',
           '| Method | JSON valid | Source checked | Term present | Validation loss | Train seconds | Peak allocated GiB | Mean generation seconds |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in rows:
        fmt=lambda key:'—' if row.get(key) is None else f'{row[key]:.3f}'
        lines.append('| '+row['method']+' | '+' | '.join(fmt(k) for k in ('json_valid','source_checked','terminology_present','validation_loss','train_seconds','peak_allocated_gib','mean_latency_seconds'))+' |')
    lines+=['','## Language-specific structural checks','',
            '| Method | English passes / model cases | Hindi passes / model cases | English latency seconds | Hindi latency seconds |',
            '| --- | ---: | ---: | ---: | ---: |']
    for row in rows:
        en=row['by_language']['en'];hi=row['by_language']['hi']
        lines.append(f"| {row['method']} | {en['source_checked_count']} / {en['cases']} | {hi['source_checked_count']} / {hi['cases']} | {en['mean_latency_seconds']:.3f} | {hi['mean_latency_seconds']:.3f} |")
    lines+=['','## Secondary Markdown-fence diagnostic','',
            'The base model often wraps JSON in Markdown. The primary contract requires raw JSON. To avoid treating wrapper compliance as mathematical improvement, the following post-hoc diagnostic removes only a single surrounding Markdown fence from every saved response. It does not repair JSON or content.','',
            '| Method | Normalized JSON passes | Normalized source-check passes |',
            '| --- | ---: | ---: |']
    for row in rows:
        secondary=row['fence_normalized_secondary']
        lines.append(f"| {row['method']} | {secondary['json_valid_count']} / {secondary['cases']} | {secondary['source_checked_count']} / {secondary['cases']} |")
    lines+=['','## Parameters and saved artifacts','',
            '| Method | Trainable parameters | Trainable percent | Saved checkpoint MiB (including tokenizer) |',
            '| --- | ---: | ---: | ---: |']
    for row in rows:
        if row['method']=='baseline':lines.append('| baseline | 0 | 0 | Base weights shared by all arms |')
        else:lines.append(f"| {row['method']} | {row['trainable_parameters']:,} | {row['trainable_percent']:.3f} | {row['checkpoint_bytes']/2**20:.2f} |")
    lines+=['',f"Rates are proportions from 0 to 1. {evaluations[0]['deterministic_pipeline_cases']} deterministic pipeline cases are not attributed to the model.",'',
            'English and Hindi results, all raw responses, training details and prompt hashes are in the JSON files. The blind review sheet contains no method names; keep its key separate.','',
            '## Limits','',*['- '+s for s in json.loads((args.root/'comparison.json').read_text())['limitations']],
            '', '## References','',
            '- Qwen model: https://huggingface.co/Qwen/Qwen3-0.6B',
            '- PEFT quantization: https://huggingface.co/docs/peft/en/developer_guides/quantization',
            '- bitsandbytes: https://huggingface.co/docs/bitsandbytes/installation']
    (args.root/'comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    analyse(args)
    print(json.dumps(rows),flush=True)


def analyse(args):
    """Describe observed failures without assigning human quality ratings."""
    path=args.root/'failure_analysis.json'
    if path.exists():raise FileExistsError('Preserve the existing failure analysis.')
    failures={}
    for method in ('baseline','lora','qlora','full'):
        evaluation=json.loads((args.root/(method+'_evaluation.json')).read_text(encoding='utf-8'))
        active=[row for row in evaluation['rows'] if row['model_called']]
        failures[method]={'error_counts':dict(Counter(row.get('error') or 'none' for row in active if not row['source_checked'])),
                          'reached_output_token_limit':[row['id'] for row in active if row['generated_tokens']==320],
                          'failed_cases':[{'id':row['id'],'language':row['language'],'error':row['error']} for row in active if not row['source_checked']]}
    write(path,{'kind':'Validator failure analysis, not independent correctness labels','methods':failures})
    lines=['','## Observed failure cases','',
           '| Method | Validator rejection reasons | Cases reaching output limit |',
           '| --- | --- | --- |']
    for method,stats in failures.items():
        reasons='; '.join(f'{key}: {value}' for key,value in stats['error_counts'].items())
        lines.append(f"| {method} | {reasons} | {', '.join(stats['reached_output_token_limit']) or 'None'} |")
    lines+=['','These are parser/validator observations, not human correctness labels. In case R06, both adapter models output a Hindi assertion that a right angle measures 180 degrees; the angle-measure guard rejected it (a right angle is 90 degrees). The saved outputs and supporting passages should be reviewed together. R12 remains a failed Hindi digit-sum response in every arm. Do not deploy a method based only on the aggregate rates.']
    with (args.root/'comparison.md').open('a',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['download','encode','train','evaluate','report','analyse'])
    parser.add_argument('--method',choices=['baseline','lora','qlora','full'],default='baseline')
    parser.add_argument('--root',type=Path,default=ROOT/'reports/finetuning_v2')
    parser.add_argument('--base',type=Path,default=ROOT/'.dist/finetuning/base')
    parser.add_argument('--checkpoints',type=Path,default=ROOT/'.dist/finetuning/v2/checkpoints')
    parser.add_argument('--max-seq',type=int,default=768)
    args=parser.parse_args();args.root.mkdir(parents=True,exist_ok=True)
    {'download':download,'encode':encode,'train':train,'evaluate':evaluate,'report':report,'analyse':analyse}[args.phase](args)
