"""Local BM25 and reciprocal-rank fusion over the same evidence candidates.

No downloaded models, external services, or benchmark-specific rules.
"""
import math
import unicodedata
from collections import Counter

VERSION='bm25-rrf-v1'
K1=1.2
B=0.75
RRF_K=60
# Function words only. Keep negation, mathematical terms, and numbers.
STOP_WORDS=set(('a an the is are was were be been being of to in on at for '
                'and or with by as it this that these those what how why '
                'which who does do did can could would should please explain '
                'है हैं था थी थे का की के को से में पर और या यह वह इस उस '
                'एक क्या कैसे क्यों कौन कितने कितनी होता होती होते बताइए समझाइए').split())


def words(text):
    """Unicode words including vowel signs; normalize decimal digit scripts."""
    result=[];current=[]
    for char in unicodedata.normalize('NFKC',text).casefold():
        if unicodedata.category(char)=='Nd':char=str(unicodedata.decimal(char))
        if unicodedata.category(char)[0] in 'LNM':current.append(char)
        elif current:result.append(''.join(current));current=[]
    if current:result.append(''.join(current))
    return result


def bm25_scores(documents,query):
    """BM25 document frequencies and lengths are computed on anchor text only."""
    tokens=[[w for w in words(text) if w not in STOP_WORDS] for text in documents]
    query_terms=set(words(query))-STOP_WORDS
    if not tokens or not query_terms:return [0.]*len(tokens)
    frequencies=[Counter(doc) for doc in tokens]
    df=Counter(word for counts in frequencies for word in counts)
    average=sum(len(doc) for doc in tokens)/len(tokens)
    if not average:return [0.]*len(tokens)
    result=[]
    for doc,counts in zip(tokens,frequencies):
        score=0.
        for word in query_terms:
            count=counts.get(word,0)
            if not count:continue
            idf=math.log1p((len(tokens)-df[word]+.5)/(df[word]+.5))
            score+=idf*count*(K1+1)/(count+K1*(1-B+B*len(doc)/average))
        result.append(score)
    return result


def fuse(candidates,query):
    """Fuse independent semantic and positive BM25 ranks, before deduplication.

    Missing lexical evidence supplies no rank contribution. Ties retain the
    semantic order, and no lexical matches reproduce that order exactly.
    """
    if not candidates:return []
    semantic=sorted(candidates,key=lambda row:(-row['retrieval_score'],row['url'],row['excerpt']))
    scores=bm25_scores([row.get('matched_excerpt',row['excerpt']) for row in semantic],query)
    lexical=sorted((i for i,score in enumerate(scores) if score>0),key=lambda i:(-scores[i],i))
    lexical_ranks={index:rank for rank,index in enumerate(lexical,1)}
    result=[]
    for index,row in enumerate(semantic):
        semantic_rank=index+1;lexical_rank=lexical_ranks.get(index)
        fused=1/(RRF_K+semantic_rank)+(1/(RRF_K+lexical_rank) if lexical_rank else 0.)
        result.append(dict(row,semantic_score=row['retrieval_score'],semantic_rank=semantic_rank,
                           bm25_score=round(scores[index],6),bm25_rank=lexical_rank,
                           retrieval_score=fused,ranking=VERSION))
    return sorted(result,key=lambda row:(-row['retrieval_score'],row['semantic_rank']))
