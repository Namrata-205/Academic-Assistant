"""Page-preserving graph chunks of verified catalog pages, with local embeddings."""
import re
import hashlib
import unicodedata
from functools import lru_cache
from diagnostic import semantic_mapper as sm

VERSION='graph-metadata-page-v2'
BREAK_SIMILARITY=.48
MAX_CHARS=650


def units(blocks):
    result=[]
    for block in blocks:
        for sentence in re.split(r'(?<=[.!?।])\s+',block):
            # Bound long OCR/layout runs; never silently truncate an evidence span.
            words=sentence.split();current=[];size=0
            for word in words:
                if current and size+len(word)+1>MAX_CHARS:
                    result.append(' '.join(current));current=[];size=0
                current.append(word);size+=len(word)+1
            if current:result.append(' '.join(current))
    return result


def split_graph(blocks,encode=None):
    """Merge contiguous communities using weighted sentence-similarity edges.

    Nodes are sentence spans. Every pair above BREAK_SIMILARITY has an
    undirected cosine-weighted edge. Adjacent communities merge by strongest
    mean cross-community edge weight, including non-adjacent sentence links.
    Missing edges count as zero, preventing a single bridge from joining
    unrelated topics. Contiguous communities preserve exact evidence order.
    MAX_CHARS is a safety ceiling, rather than the chunk boundary rule.
    """
    sentences=units(blocks)
    if not sentences:return []
    vectors=(encode or sm.embed)(sentences)
    # Normalize here as well so injected encoders need not return unit vectors.
    import numpy as np
    vectors=np.asarray(vectors,dtype=float)
    norms=np.linalg.norm(vectors,axis=1,keepdims=True)
    vectors=np.divide(vectors,norms,out=np.zeros_like(vectors),where=norms!=0)
    similarities=vectors@vectors.T
    weights=np.where(similarities>=BREAK_SIMILARITY,similarities,0.)
    communities=[(i,i+1,len(text)) for i,text in enumerate(sentences)]
    while len(communities)>1:
        best=None
        for index,(left,right) in enumerate(zip(communities,communities[1:])):
            a,b,left_size=left;c,d,right_size=right
            if left_size+right_size+1>MAX_CHARS:continue
            strength=float(weights[a:b,c:d].mean())
            if strength>=BREAK_SIMILARITY and (best is None or strength>best[0]):
                best=(strength,index)
        if best is None:break
        index=best[1]
        a,b,left_size=communities[index];c,d,right_size=communities[index+1]
        communities[index:index+2]=[(a,d,left_size+right_size+1)]
    return [' '.join(sentences[a:b]) for a,b,_ in communities]


def split_semantically(blocks,encode=None):
    """Compatibility entry point for callers of the previous chunker."""
    return split_graph(blocks,encode)


@lru_cache(maxsize=128)
def page_index(filename,page,mtime):
    from diagnostic.book_chat import page_content
    chunks=split_graph(page_content(filename,page,mtime))
    return chunks,sm.embed(chunks) if chunks else None


@lru_cache(maxsize=256)
def contextual_vectors(texts,context):
    """Cache embeddings of metadata plus evidence, without changing evidence."""
    return sm.embed([context+'\n'+text for text in texts])


def _terms(text):
    return set(re.findall(r'[^\W_]+',unicodedata.normalize('NFKC',text).casefold()))


def rank_pages(pages,query,limit=3):
    """Rank graph chunks using evidence, contextual metadata and concept coverage."""
    query_vector=sm.embed([query])[0];ranked=[]
    for filename,page,mtime,metadata in pages:
        chunks,vectors=page_index(filename,page,mtime)
        if not chunks:continue
        context=' | '.join(str(metadata[key]) for key in
                          ('chapter_title','section','concept_en','concept_hi','language')
                          if metadata.get(key))
        contextual=contextual_vectors(tuple(chunks),context) if context else vectors
        label=metadata.get('concept_hi' if metadata.get('language')=='hi' else 'concept_en','')
        label_terms=_terms(label)
        offset=0
        for index,(text,score,context_score) in enumerate(zip(chunks,vectors@query_vector,contextual@query_vector)):
            coverage=len(label_terms & _terms(text))/len(label_terms) if label_terms else 0.
            # Fixed weights: do not fit them to the development evaluation cases.
            combined=.75*float(score)+.15*float(context_score)+.10*coverage if context else float(score)
            identity=f"{metadata.get('sha256',filename)}:{page}:{index}:{VERSION}:{text}"
            ranked.append(dict(metadata,excerpt=text,similarity=round(float(score),4),
                               retrieval_score=round(combined,4),metadata_similarity=round(float(context_score),4),
                               concept_coverage=round(coverage,4),chunking=VERSION,
                               chunk_id=hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24],
                               chunk_index=index,chunk_count=len(chunks),
                               char_start=offset,char_end=offset+len(text)))
            offset+=len(text)+1
    return sorted(ranked,key=lambda item:(-item['retrieval_score'],item['url'],item['excerpt']))[:limit]
