import os, sys, re, json, hashlib

# --------------------------------------------
# CONFIG
# --------------------------------------------

JAVA_KEYWORDS = {
    "abstract","assert","boolean","break","byte","case","catch","char","class","const","continue",
    "default","do","double","else","enum","extends","final","finally","float","for","goto","if",
    "implements","import","instanceof","int","interface","long","native","new","package","private",
    "protected","public","return","short","static","strictfp","super","switch","synchronized",
    "this","throw","throws","transient","try","void","volatile","while","true","false","null"
}

IGNORE_DIRS = {
    ".git",".idea",".vscode","node_modules","__pycache__","target","build",".metadata"
}

CODE_EXT = {".java",".py",".c",".cpp",".js",".ts",".cs",".go",".rb",".php"}

# --------------------------------------------
# FILE READ / SANITIZE
# --------------------------------------------

def read_text(root, rel):
    path = os.path.join(root, rel)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def remove_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    code = re.sub(r"//.*", "", code)
    code = re.sub(r"(?m)^\s*#(?!\!).*$", "", code)
    return code

# --------------------------------------------
# TOKENIZER (fixed)
# --------------------------------------------

token_pattern = re.compile(r"""
    "[^"\\\n]*(?:\\.[^"\\\n]*)*"    |   # string (double quotes)
    '[^'\\\n]*(?:\\.[^'\\\n]*)*'    |   # string (single quotes)
    [A-Za-z_][A-Za-z0-9_]*         |   # identifiers / keywords
    \d+\.\d+|\d+                   |   # numbers
    ==|!=|<=|>=|\+\+|--|&&|\|\||->|=>|:= |   # multi-char ops
    [~!%^&*()+={}\[\]|\\:;\"'<>,.?/-]      # single char symbols
""", re.VERBOSE)

def tokenize(code):
    tokens = token_pattern.findall(code)
    return [t for t in tokens if t.strip()]

# --------------------------------------------
# NORMALIZATION
# --------------------------------------------

def normalize(tokens, keywords=JAVA_KEYWORDS):
    id_map = {}
    next_id = 1
    norm = []

    for tok in tokens:
        # string literal → STR
        if (tok.startswith('"') and tok.endswith('"')) or (tok.startswith("'") and tok.endswith("'")):
            norm.append("STR")

        # Java keyword
        elif tok in keywords:
            norm.append(tok)

        # number
        elif re.fullmatch(r"\d+\.\d+|\d+", tok):
            norm.append("NUM")

        # identifier
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
            if tok not in id_map:
                id_map[tok] = f"ID{next_id}"
                next_id += 1
            norm.append(id_map[tok])

        # operator / symbol
        else:
            norm.append(tok)

    return norm, id_map

# --------------------------------------------
# FINGERPRINTING (k-shingles)
# --------------------------------------------

def fingerprints_from_norm(norm_tokens, k=5):
    fps = set()
    n = len(norm_tokens)
    for i in range(max(0, n - k + 1)):
        shingle = "\u241F".join(norm_tokens[i:i+k])
        h = hashlib.sha1(shingle.encode("utf-8")).hexdigest()
        fps.add(h)
    return fps

# --------------------------------------------
# COLLECT CODE FILES
# --------------------------------------------

def collect_code_files(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in IGNORE_DIRS]
        for f in sorted(fns):
            if os.path.splitext(f)[1].lower() in CODE_EXT:
                rel = os.path.relpath(os.path.join(dp, f), root)
                out.append(rel.replace("\\","/"))
    return sorted(out)

# --------------------------------------------
# JACCARD SIMILARITY
# --------------------------------------------

def jaccard(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union) if union else 0.0

# --------------------------------------------
# AGGREGATE REPO SIMILARITY
# --------------------------------------------

def aggregate(repoA, repoB):
    # repoA: {file: {fingerprints, norm_len}}
    # repoB: same structure
    # A -> B
    totw = sum(max(1, info["norm_len"]) for info in repoA.values())
    sumw = 0

    for relA, infoA in repoA.items():
        best = max(jaccard(infoA["fingerprints"], infoB["fingerprints"]) for infoB in repoB.values())
        w = max(1, infoA["norm_len"])
        sumw += best * w

    scoreA = sumw / totw

    # B -> A
    totw = sum(max(1, info["norm_len"]) for info in repoB.values())
    sumw = 0

    for relB, infoB in repoB.items():
        best = max(jaccard(infoB["fingerprints"], infoA["fingerprints"]) for infoA in repoA.values())
        w = max(1, infoB["norm_len"])
        sumw += best * w

    scoreB = sumw / totw

    return (scoreA + scoreB) / 2.0

# --------------------------------------------
# MAIN DRIVER
# --------------------------------------------

def main():
    if len(sys.argv) != 3:
        print("Usage: python repo_tree_tokenization.py <repo1_path> <repo2_path>")
        sys.exit(1)

    repo1 = sys.argv[1]
    repo2 = sys.argv[2]

    if not os.path.isdir(repo1) or not os.path.isdir(repo2):
        print("One or both paths are not valid directories.")
        sys.exit(1)

    filesA = collect_code_files(repo1)
    filesB = collect_code_files(repo2)

    print("\nCode files in Repo A:")
    for f in filesA:
        print(" -", f)

    print("\nCode files in Repo B:")
    for f in filesB:
        print(" -", f)

    perA = {}
    perB = {}

    results = {
        "repoA": repo1,
        "repoB": repo2,
        "filesA": filesA,
        "filesB": filesB,
        "per_file": {},
        "pairs": []
    }

    # process repo A
    for rel in filesA:
        txt = read_text(repo1, rel)
        txt = remove_comments(txt)
        toks = tokenize(txt)
        norm, idmap = normalize(toks)
        fps = fingerprints_from_norm(norm, k=5)

        results["per_file"][f"A:{rel}"] = {
            "raw_len": len(toks),
            "norm_len": len(norm),
            "fingerprints_count": len(fps),
            "id_map": idmap,
            "first_norm_tokens": norm[:80]
        }

        perA[rel] = {"fingerprints": fps, "norm_len": len(norm)}

    # process repo B
    for rel in filesB:
        txt = read_text(repo2, rel)
        txt = remove_comments(txt)
        toks = tokenize(txt)
        norm, idmap = normalize(toks)
        fps = fingerprints_from_norm(norm, k=5)

        results["per_file"][f"B:{rel}"] = {
            "raw_len": len(toks),
            "norm_len": len(norm),
            "fingerprints_count": len(fps),
            "id_map": idmap,
            "first_norm_tokens": norm[:80]
        }

        perB[rel] = {"fingerprints": fps, "norm_len": len(norm)}

    # Pairwise similarities
    for a, infoA in perA.items():
        for b, infoB in perB.items():
            score = jaccard(infoA["fingerprints"], infoB["fingerprints"])
            results["pairs"].append({
                "fileA": a,
                "fileB": b,
                "jaccard": score,
                "a_fp": len(infoA["fingerprints"]),
                "b_fp": len(infoB["fingerprints"])
            })

    # overall similarity
    results["overall_repo_similarity"] = aggregate(perA, perB)

    # Write JSON
    outfile = "detailed_output_fixed.json"
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nSaved:", outfile)
    print("\nTop matches (sorted):")

    pairs_sorted = sorted(results["pairs"], key=lambda x: x["jaccard"], reverse=True)
    for p in pairs_sorted[:10]:
        print(f"{p['fileA']} <-> {p['fileB']} = {p['jaccard']:.4f} (fpA={p['a_fp']}, fpB={p['b_fp']})")

    print("\nOverall repo similarity =", results["overall_repo_similarity"])

if __name__ == "__main__":
    main()
