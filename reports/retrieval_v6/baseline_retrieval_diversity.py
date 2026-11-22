"""Reduce redundant evidence without removing candidates or altering passages."""
OVERLAP_PENALTY=.25
VERSION='source-span-diversity-v1'


def budgeted_prefix(rows,max_items=3,max_chars=1300):
    """Allow a third passage only when it fits the old two-by-650 ceiling.

    Keep the ranking prefix: do not replace a long relevant passage with a
    shorter weaker one simply to fill the budget.
    """
    if max_items<1 or max_chars<1:raise ValueError('Evidence limits must be positive.')
    result=[];used=0
    for row in rows[:max_items]:
        size=len(row['excerpt'])
        if used+size>max_chars:break
        result.append(row);used+=size
    return result


def merged(intervals):
    result=[]
    for start,end in sorted(intervals):
        if end<=start:continue
        if result and start<=result[-1][1]:result[-1]=(result[-1][0],max(end,result[-1][1]))
        else:result.append((start,end))
    return result


def length(intervals):
    return sum(end-start for start,end in merged(intervals))


def intersection(left,right):
    return length([(max(a,c),min(b,d)) for a,b in merged(left) for c,d in merged(right)
                   if max(a,c)<min(b,d)])


def span(row):
    start=row.get('context_char_start');end=row.get('context_char_end')
    if not isinstance(start,int) or not isinstance(end,int) or end<=start:return None
    # Offsets are local to a reconstructed page, never comparable across pages.
    return row['url'],(start,end)


def rerank(rows):
    """Keep the best result, then softly penalize already covered source text.

    No result is filtered: limit=None still exposes the complete candidate pool
    and its original recall denominator. Every prefix belongs to one fixed order.
    """
    remaining=[(i,row) for i,row in enumerate(rows)];result=[];covered={}
    while remaining:
        options=[]
        seed_rank,seed=remaining[0]
        for original_rank,row in remaining:
            # Novelty cannot compensate for weaker relevance. Require Pareto
            # dominance on the existing semantic and query-coverage signals.
            if original_rank!=seed_rank and not (
                row.get('semantic_score',float('-inf'))>=seed.get('semantic_score',float('inf'))
                and row.get('query_coverage',float('-inf'))>=seed.get('query_coverage',float('inf'))
            ):continue
            location=span(row);overlap=0.
            if location:
                key,(start,end)=location
                overlap=intersection([(start,end)],covered.get(key,[]))/(end-start)
            base=row['retrieval_score']
            score=base*(1-OVERLAP_PENALTY*overlap)
            options.append((score,-original_rank,original_rank,row,overlap))
        score,_,original_rank,row,overlap=max(options,key=lambda entry:entry[:2])
        result.append(dict(row,pre_diversity_score=row['retrieval_score'],retrieval_score=score,
                           source_overlap=overlap,diversification=VERSION,pre_diversity_rank=original_rank+1))
        location=span(row)
        if location:
            key,interval=location;covered[key]=merged(covered.get(key,[])+[interval])
        remaining=[entry for entry in remaining if entry[0]!=original_rank]
    return result
