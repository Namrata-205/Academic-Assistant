"""Page-preserving semantic chunks of verified catalog pages, with local embeddings."""
import re
from functools import lru_cache
from diagnostic import semantic_mapper as sm

VERSION='semantic-page-v1'
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


def split_semantically(blocks,encode=sm.embed):
    sentences=units(blocks)
    if not sentences:return []
    vectors=encode(sentences);chunks=[];current=sentences[0]
    for i,sentence in enumerate(sentences[1:],1):
        similarity=float(vectors[i-1]@vectors[i])
        if similarity<BREAK_SIMILARITY or len(current)+len(sentence)+1>MAX_CHARS:
            chunks.append(current);current=sentence
        else:current+=' '+sentence
    chunks.append(current)
    return chunks


@lru_cache(maxsize=128)
def page_index(filename,page,mtime):
    from diagnostic.book_chat import page_content
    chunks=split_semantically(page_content(filename,page,mtime))
    return chunks,sm.embed(chunks) if chunks else None


def rank_pages(pages,query,limit=3):
    """Cosine retrieval over normalized vectors; page metadata stays attached."""
    query_vector=sm.embed([query])[0];ranked=[]
    for filename,page,mtime,metadata in pages:
        chunks,vectors=page_index(filename,page,mtime)
        if not chunks:continue
        for text,score in zip(chunks,vectors@query_vector):
            ranked.append(dict(metadata,excerpt=text,similarity=round(float(score),4)))
    return sorted(ranked,key=lambda item:(-item['similarity'],item['url'],item['excerpt']))[:limit]
