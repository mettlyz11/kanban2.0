import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

# Import core functions directly
from collections import defaultdict
from math import sqrt
import re

# Copy the functions here for testing
def strip_t_prefix(text):
    if not text:
        return ""
    text = re.sub(r'^T\d+[：:]\s*', '', text)
    text = re.sub(r'^[\u4e00-\u9fff]+\s*[-—]\s*', '', text)
    text = re.sub(r'^.+?[-—]\s*.+?[-—]\s*', '', text, count=1)
    return text.strip()

def tokenize(text):
    if not text:
        return set()
    text = text.lower().strip()
    words = set()
    words.update(re.findall(r'[a-z0-9]+', text))
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(chinese_chars) - 1):
        words.add(chinese_chars[i] + chinese_chars[i+1])
    words.update(chinese_chars)
    return words

def jaccard_similarity(text_a, text_b, strip_prefix=True):
    if strip_prefix:
        text_a = strip_t_prefix(text_a)
        text_b = strip_t_prefix(text_b)
    set_a = tokenize(text_a)
    set_b = tokenize(text_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0

def levenshtein_similarity(text_a, text_b, strip_prefix=True):
    if strip_prefix:
        a = strip_t_prefix(text_a)
        b = strip_t_prefix(text_b)
    else:
        a, b = text_a, text_b
    a = a.lower().strip()[:50]
    b = b.lower().strip()[:50]
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    distance = dp[m][n]
    max_len = max(m, n)
    return 1.0 - (distance / max_len) if max_len > 0 else 0.0

def tfidf_similarity(text_a, text_b, strip_prefix=True, global_corpus=None):
    if strip_prefix:
        text_a = strip_t_prefix(text_a)
        text_b = strip_t_prefix(text_b)
    
    corpus = global_corpus or [text_a, text_b]
    docs = [list(tokenize(t)) for t in [text_a, text_b]]
    all_tokens = set()
    for d in docs:
        all_tokens.update(d)
    
    N = len(corpus)
    idf = {}
    for token in all_tokens:
        doc_count = sum(1 for t in [text_a, text_b] if token in tokenize(t))
        idf[token] = sqrt(N / (doc_count + 1)) if doc_count > 0 else 0
    
    vectors = []
    for d in docs:
        tf = defaultdict(int)
        for token in d:
            tf[token] += 1
        max_tf = max(tf.values()) if tf else 1
        vec = {}
        for token in all_tokens:
            tf_val = tf.get(token, 0) / max_tf
            vec[token] = tf_val * idf.get(token, 0)
        vectors.append(vec)
    
    vec_a, vec_b = vectors
    dot = sum(vec_a.get(t, 0) * vec_b.get(t, 0) for t in all_tokens)
    norm_a = sqrt(sum(v*v for v in vec_a.values()))
    norm_b = sqrt(sum(v*v for v in vec_b.values()))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def prefix_similarity(text_a, text_b, prefix_len=20, strip_prefix=True):
    if strip_prefix:
        a = strip_t_prefix(text_a)
        b = strip_t_prefix(text_b)
    else:
        a, b = text_a, text_b
    a = a.strip()[:prefix_len]
    b = b.strip()[:prefix_len]
    if not a or not b:
        return 0.0
    match = sum(1 for i in range(min(len(a), len(b))) if a[i] == b[i])
    return match / max(len(a), len(b))

THRESHOLDS = {'jaccard': 0.60, 'tfidf': 0.50, 'levenshtein': 0.70, 'prefix': 0.80}

print("=" * 60)
print("Dedup Algorithm Tests")
print("=" * 60)

tests = [
    (
        "T4: \u8d22\u5bcc\u589e\u503c - AI\u50ac\u5316\u8d5b\u9053\u4e00\u7ea7\u5e02\u573a\u6295\u8d44\u6807\u7684\u7cfb\u7edf\u6027\u626b\u63cf\u4e0e\u7b5b\u9009",
        "T4: \u8d22\u5bcc\u589e\u503c - AI\u50ac\u5316\u8d5b\u9053\u4e00\u7ea7\u5e02\u573a\u6295\u8d44\u673a\u4f1a\u7cfb\u7edf\u6027\u626b\u63cf\u4e0e\u7b5b\u9009",
        True, "Nearly identical titles"
    ),
    (
        "T4: \u8d22\u5bcc\u589e\u503c - AI\u50ac\u5316\u8d5b\u9053\u4e00\u7ea7\u5e02\u573a\u6295\u8d44\u6807\u7684\u7cfb\u7edf\u6027\u626b\u63cf\u4e0e\u7b5b\u9009",
        "T4: \u8d22\u5bcc\u589e\u503c - AI\u50ac\u5316\u8d5b\u9053\u4e00\u7ea7\u5e02\u573a\u6295\u8d44\u6807\u7684\u7cfb\u7edf\u6027\u626b\u63cf\u4e0e\u7b5b\u9009",
        True, "Exact same title"
    ),
    (
        "T4: \u8d22\u5bcc\u589e\u503c\u4e0e\u8d44\u4ea7\u7ba1\u7406 - \u9ec4\u91d1ETF\u5efa\u4ed3\u65f6\u673a\u5206\u6790\u4e0e\u6267\u884c\u8ba1\u5212",
        "T4: \u8d44\u4ea7\u914d\u7f6e\u4e0e\u4ea7\u4e1a\u6295\u8d44 - \u9ec4\u91d1ETF Q2\u5efa\u4ed3\u65f6\u673a\u91cf\u5316\u5206\u6790",
        True, "Same topic (gold ETF) with different T-labels"
    ),
    (
        "T1: AI\u52a9\u624b\u4f18\u5316 - \u4efb\u52a1\u81ea\u52a8\u751f\u6210\u5f15\u64ceV4.4\u7248\u672c\u8fed\u4ee3\u4e0e\u4f18\u5316",
        "T3: \u5b66\u672f\u5f71\u54cd\u529b - NSFC 2026\u9762\u4e0a\u9879\u76eeAI\u50ac\u5316\u9886\u57df\u7cbe\u51c6\u9009\u9898\u4e0e\u7533\u62a5\u65f6\u95f4\u8868",
        False, "Completely different topics"
    ),
    (
        "T6: \u884c\u4e1a\u5f71\u54cd\u529b - 2026\u5e74AI\u50ac\u5316\u9886\u57df\u9876\u7ea7\u4f1a\u8bae\u6295\u7a3f\u4e0espeaker\u7533\u8bf7",
        "T6: \u884c\u4e1a\u5f71\u54cd\u529b\u4e0e\u793e\u4f1a\u53c2\u4e0e - AI\u50ac\u5316\u4ea7\u4e1a\u8054\u76df\u53d1\u8d77\u4e0e2026\u884c\u4e1a\u5cf0\u4f1a\u7b56\u5212",
        False, "Different topics (conf submission vs industry alliance)"
    ),
    (
        "T7: \u5065\u5eb7\u7ba1\u7406 - 2026\u5e74\u5ea6\u5168\u9762\u4f53\u68c0\u65b9\u6848\u4e0e\u5065\u5eb7\u6307\u6807\u8ddf\u8e2a\u4f53\u7cfb",
        "T7: \u5065\u5eb7\u7ba1\u7406 - 2026\u5e74\u5ea6\u5168\u9762\u4f53\u68c0\u65b9\u6848\u4e0e\u5065\u5eb7\u6307\u6807\u8ddf\u8e2a\u4f53\u7cfb",
        True, "Exact same title"
    ),
    (
        "T6: \u884c\u4e1a\u5f71\u54cd\u529b\u4e0e\u793e\u4f1a\u53c2\u4e0e - AI\u50ac\u5316\u4ea7\u4e1a\u8054\u76df\u53d1\u8d77\u4e0e2026\u884c\u4e1a\u5cf0\u4f1a\u7b56\u5212",
        "T6: \u884c\u4e1a\u5f71\u54cd\u529b\u4e0e\u793e\u4f1a\u53c2\u4e0e - AI\u50ac\u5316\u4ea7\u4e1a\u8054\u76df\u53d1\u8d77\u4e0e2026\u884c\u4e1a\u5cf0\u4f1a\u7b56\u5212",
        True, "Exact same (pending dup)"
    ),
    (
        "T7: \u5065\u5eb7\u7ba1\u7406 - 2026\u5e74\u5ea6\u5168\u9762\u4f53\u68c0\u65b9\u6848\u4e0e\u5065\u5eb7\u6307\u6807\u8ddf\u8e2a\u4f53\u7cfb",
        "T6: \u8eab\u5fc3\u5065\u5eb7\u4e0e\u751f\u6d3b\u8d28\u91cf - 2026\u5e74\u6625\u5b63\u5065\u5eb7\u7ba1\u7406\u8ba1\u5212\u5236\u5b9a",
        False, "Both health-related but different topics"
    ),
]

passed, failed = 0, 0
for title_a, title_b, expected, desc in tests:
    jac = jaccard_similarity(title_a, title_b)
    tfidf = tfidf_similarity(title_a, title_b)
    lev = levenshtein_similarity(title_a, title_b)
    pre = prefix_similarity(title_a, title_b)
    
    th = THRESHOLDS
    above = sum([jac >= th['jaccard'], tfidf >= th['tfidf'], lev >= th['levenshtein'], pre >= th['prefix']])
    is_dup = above >= 2
    
    status = "OK" if is_dup == expected else "FAIL"
    if is_dup == expected:
        passed += 1
    else:
        failed += 1
    
    clean_a = strip_t_prefix(title_a)[:35]
    clean_b = strip_t_prefix(title_b)[:35]
    print(f"[{status}] {desc}")
    print(f"  '{clean_a}' vs '{clean_b}'")
    print(f"  J={jac:.3f} TF={tfidf:.3f} L={lev:.3f} P={pre:.3f} | above={above}/4 -> {'DUP' if is_dup else 'OK'} (expect {'DUP' if expected else 'OK'})")

print(f"\n{'='*60}")
print(f"Result: {passed}/{passed+failed} passed", end="")
print(" - ALL PASS!" if failed == 0 else f" - {failed} FAILED")
print(f"{'='*60}")
