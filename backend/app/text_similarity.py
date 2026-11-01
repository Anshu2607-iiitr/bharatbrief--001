"""Small pure-Python TF-IDF + cosine similarity.

Matches scikit-learn's TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
max_features=N) defaults (lowercase, token pattern \\b\\w\\w+\\b, smooth idf,
L2 norm) without pulling in numpy/scipy/scikit-learn, which are too big for a
Vercel function.
"""

import math
import re
from collections import Counter

TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")

# scikit-learn's ENGLISH_STOP_WORDS (BSD-3-Clause)
ENGLISH_STOP_WORDS = frozenset([
    'a', 'about', 'above', 'across', 'after', 'afterwards', 'again', 'against', 'all',
    'almost', 'alone', 'along', 'already', 'also', 'although', 'always', 'am', 'among',
    'amongst', 'amoungst', 'amount', 'an', 'and', 'another', 'any', 'anyhow', 'anyone',
    'anything', 'anyway', 'anywhere', 'are', 'around', 'as', 'at', 'back', 'be',
    'became', 'because', 'become', 'becomes', 'becoming', 'been', 'before',
    'beforehand', 'behind', 'being', 'below', 'beside', 'besides', 'between', 'beyond',
    'bill', 'both', 'bottom', 'but', 'by', 'call', 'can', 'cannot', 'cant', 'co',
    'con', 'could', 'couldnt', 'cry', 'de', 'describe', 'detail', 'do', 'done', 'down',
    'due', 'during', 'each', 'eg', 'eight', 'either', 'eleven', 'else', 'elsewhere',
    'empty', 'enough', 'etc', 'even', 'ever', 'every', 'everyone', 'everything',
    'everywhere', 'except', 'few', 'fifteen', 'fifty', 'fill', 'find', 'fire', 'first',
    'five', 'for', 'former', 'formerly', 'forty', 'found', 'four', 'from', 'front',
    'full', 'further', 'get', 'give', 'go', 'had', 'has', 'hasnt', 'have', 'he',
    'hence', 'her', 'here', 'hereafter', 'hereby', 'herein', 'hereupon', 'hers',
    'herself', 'him', 'himself', 'his', 'how', 'however', 'hundred', 'i', 'ie', 'if',
    'in', 'inc', 'indeed', 'interest', 'into', 'is', 'it', 'its', 'itself', 'keep',
    'last', 'latter', 'latterly', 'least', 'less', 'ltd', 'made', 'many', 'may', 'me',
    'meanwhile', 'might', 'mill', 'mine', 'more', 'moreover', 'most', 'mostly', 'move',
    'much', 'must', 'my', 'myself', 'name', 'namely', 'neither', 'never',
    'nevertheless', 'next', 'nine', 'no', 'nobody', 'none', 'noone', 'nor', 'not',
    'nothing', 'now', 'nowhere', 'of', 'off', 'often', 'on', 'once', 'one', 'only',
    'onto', 'or', 'other', 'others', 'otherwise', 'our', 'ours', 'ourselves', 'out',
    'over', 'own', 'part', 'per', 'perhaps', 'please', 'put', 'rather', 're', 'same',
    'see', 'seem', 'seemed', 'seeming', 'seems', 'serious', 'several', 'she', 'should',
    'show', 'side', 'since', 'sincere', 'six', 'sixty', 'so', 'some', 'somehow',
    'someone', 'something', 'sometime', 'sometimes', 'somewhere', 'still', 'such',
    'system', 'take', 'ten', 'than', 'that', 'the', 'their', 'them', 'themselves',
    'then', 'thence', 'there', 'thereafter', 'thereby', 'therefore', 'therein',
    'thereupon', 'these', 'they', 'thick', 'thin', 'third', 'this', 'those', 'though',
    'three', 'through', 'throughout', 'thru', 'thus', 'to', 'together', 'too', 'top',
    'toward', 'towards', 'twelve', 'twenty', 'two', 'un', 'under', 'until', 'up',
    'upon', 'us', 'very', 'via', 'was', 'we', 'well', 'were', 'what', 'whatever',
    'when', 'whence', 'whenever', 'where', 'whereafter', 'whereas', 'whereby',
    'wherein', 'whereupon', 'wherever', 'whether', 'which', 'while', 'whither', 'who',
    'whoever', 'whole', 'whom', 'whose', 'why', 'will', 'with', 'within', 'without',
    'would', 'yet', 'you', 'your', 'yours', 'yourself', 'yourselves',
])


def _terms(text, ngram_range=(1, 2)):
    tokens = [
        token for token in TOKEN_PATTERN.findall(text.lower())
        if token not in ENGLISH_STOP_WORDS
    ]
    low, high = ngram_range
    terms = []
    for n in range(low, high + 1):
        for i in range(len(tokens) - n + 1):
            terms.append(" ".join(tokens[i:i + n]))
    return terms


def tfidf_vectors(documents, max_features=5000, ngram_range=(1, 2)):
    counts = [Counter(_terms(doc or "", ngram_range)) for doc in documents]

    total = Counter()
    doc_freq = Counter()
    for c in counts:
        total.update(c)
        doc_freq.update(c.keys())

    if max_features is not None and len(total) > max_features:
        # highest corpus frequency first, ties broken alphabetically (like sklearn)
        vocab = set(sorted(total, key=lambda t: (-total[t], t))[:max_features])
    else:
        vocab = set(total)

    n_docs = len(documents)
    idf = {t: math.log((1 + n_docs) / (1 + doc_freq[t])) + 1 for t in vocab}

    vectors = []
    for c in counts:
        vec = {t: tf * idf[t] for t, tf in c.items() if t in vocab}
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm:
            vec = {t: v / norm for t, v in vec.items()}
        vectors.append(vec)
    return vectors


def cosine(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(t, 0.0) for t, v in a.items())
