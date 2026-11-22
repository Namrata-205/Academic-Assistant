"""Optional, pinned ONNX cross-encoder. No network access during inference."""
import hashlib
import json
import math
import os
import sys
import threading
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'assets/models/multilingual-reranker'
VERSION='mmarco-cross-encoder-v1'
SHORTLIST=20
LOCK=threading.RLock()


@lru_cache(maxsize=1)
def runtime():
    manifest_path=MODEL/'manifest.json'
    if not manifest_path.exists():raise RuntimeError('Local reranker is not installed.')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    for entry in manifest['files']:
        path=MODEL/entry['filename']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('Reranker artifact hash mismatch: '+entry['filename'])
    dependencies=ROOT/'.dist/semantic-runtime'
    if dependencies.exists() and str(dependencies) not in sys.path:sys.path.append(str(dependencies))
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    config=json.loads((MODEL/'config.json').read_text())
    tokenizer=Tokenizer.from_file(str(MODEL/'tokenizer.json'))
    tokenizer.enable_truncation(max_length=512)
    tokenizer.enable_padding(pad_id=config.get('pad_token_id',1),pad_token='<pad>')
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(MODEL/'model_quint8_avx2.onnx'),sess_options=options,
                                 providers=['CPUExecutionProvider'])
    return np,session,tokenizer


@lru_cache(maxsize=256)
def score_passages(query,passages):
    np,session,tokenizer=runtime();result=[]
    with LOCK:
        for offset in range(0,len(passages),4):
            encoded=tokenizer.encode_batch([(query,text) for text in passages[offset:offset+4]])
            inputs={'input_ids':np.array([e.ids for e in encoded],dtype=np.int64),
                    'attention_mask':np.array([e.attention_mask for e in encoded],dtype=np.int64),
                    'token_type_ids':np.array([e.type_ids for e in encoded],dtype=np.int64)}
            logits=session.run(None,{i.name:inputs[i.name] for i in session.get_inputs()})[0]
            scores=np.asarray(logits).reshape(len(encoded),-1)
            if scores.shape[1]!=1:raise RuntimeError('Expected a single relevance logit per passage.')
            result.extend(float(value) for value in scores[:,0])
    if not all(math.isfinite(value) for value in result):raise RuntimeError('Non-finite reranker scores.')
    return tuple(result)


def rerank(rows,query):
    if not rows:return []
    head=rows[:SHORTLIST];tail=rows[SHORTLIST:]
    scores=score_passages(query,tuple(row['excerpt'] for row in head))
    if len(scores)!=len(head):raise RuntimeError('Reranker score count mismatch.')
    ordered=sorted(enumerate(zip(head,scores)),key=lambda entry:(-entry[1][1],entry[0]))
    result=[dict(row,pre_cross_encoder_rank=index+1,cross_encoder_score=score,
                 reranker=VERSION,reranker_status='scored',reranker_input='query + expanded source passage')
            for index,(row,score) in ordered]
    # Preserve the full pool for recall evaluation; unscored candidates remain
    # in their original order, never masquerading as cross-encoder-scored rows.
    result.extend(dict(row,reranker=VERSION,reranker_status='outside_shortlist') for row in tail)
    return result


def apply_if_available(rows,query,enabled=None):
    """Auto-use installed artifacts; never download or silently change evidence."""
    if enabled is None:
        mode=os.environ.get('ATLAS_RERANKER','auto').strip().lower()
        if mode not in ('auto','on','off'):raise ValueError('ATLAS_RERANKER must be auto, on, or off.')
        enabled=mode!='off' and (mode=='on' or (MODEL/'manifest.json').exists())
    if not enabled:return rows
    try:return rerank(rows,query)
    except Exception as error:
        # ONNX Runtime exposes backend-specific exception classes. This optional
        # stage must fail back to the complete previous ranking, with a status.
        return [dict(row,reranker=VERSION,reranker_status='unavailable',
                     reranker_error=type(error).__name__) for row in rows]
