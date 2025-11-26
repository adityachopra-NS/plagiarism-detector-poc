#!/usr/bin/env python3
"""
repo_plagiarism_detector_final.py

Complete plagiarism detection pipeline with:
- Tokenization & Normalization
- Fingerprinting (k-gram shingling)
- Jaccard similarity scoring
- Full JSON output with debugging info

Usage:
  python repo_plagiarism_detector_final.py <path_to_repo1> <path_to_repo2> [--k 5]
"""
import os
import sys
import re
import json
import hashlib
import argparse
from datetime import datetime

# ----------- Configuration -----------
IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', '.metadata', 
    '.idea', '.vscode', 'target', 'build', '.DS_Store'
}

CODE_EXTENSIONS = {
    ".py", ".java", ".c", ".cpp", ".js", ".ts", 
    ".cs", ".go", ".rb", ".php", ".jsx", ".tsx"
}

# Java/C-like keywords (kept as-is during normalization)
JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch",
    "char", "class", "const", "continue", "default", "do", "double",
    "else", "enum", "extends", "final", "finally", "float", "for",
    "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private",
    "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws",
    "transient", "try", "void", "volatile", "while", "true", "false", "null"
}
# -------------------------------------

def build_tree(root_path):
    """Build nested dict representing folder structure"""
    tree = {}
    root_path = os.path.abspath(root_path)
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORE_DIRS)
        filenames = sorted(filenames)
        
        rel_dir = os.path.relpath(dirpath, root_path)
        parts = [] if rel_dir == '.' else rel_dir.split(os.sep)
        
        subtree = tree
        for p in parts:
            subtree = subtree.setdefault(p, {})
        
        for f in filenames:
            subtree.setdefault(f, None)
    
    return tree

def collect_code_files(root_path):
    """Collect all code files (filtered by extension)"""
    root_path = os.path.abspath(root_path)
    code_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORE_DIRS)
        filenames = sorted(filenames)
        
        for f in filenames:
            _, ext = os.path.splitext(f)
            if ext.lower() in CODE_EXTENSIONS:
                rel_dir = os.path.relpath(dirpath, root_path)
                rel_path = f if rel_dir == '.' else os.path.join(rel_dir, f)
                code_files.append(rel_path)
    
    code_files.sort()
    return code_files

def read_file_text(root_path, rel_path):
    """Read file content as text"""
    full_path = os.path.join(root_path, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception as e:
        print(f"Warning: Failed to read {rel_path}: {e}")
        return ""

def remove_comments(code):
    """Remove Java/C-style and Python comments"""
    # Remove /* ... */ block comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove // line comments
    code = re.sub(r"//.*", "", code)
    # Remove Python # comments (but keep shebang)
    code = re.sub(r"(?m)^\s*#(?!\!).*$", "", code)
    return code

def tokenize_code_generic(code):
    """
    Generic tokenizer for code
    Returns list of tokens: identifiers, numbers, operators, symbols
    """
    token_pattern = r"""
        [A-Za-z_][A-Za-z0-9_]*   |   # identifiers / keywords
        \d+(\.\d+)?               |   # integers or floats
        ==|!=|<=|>=|&&|\|\|      |   # multi-char operators
        [{}\[\]().,;:+\-*/%<>=!&|^~]   # single-char symbols
    """
    tokens = re.findall(token_pattern, code, flags=re.VERBOSE)
    
    # Flatten tuples from regex groups
    flat = []
    for t in tokens:
        if isinstance(t, tuple):
            flat.append(t[0])  # Take full match
        else:
            flat.append(t)
    
    return flat

def normalize_tokens(tokens, language_keywords=None):
    """
    Normalize tokens:
    - Keep keywords as-is
    - Replace identifiers with ID1, ID2, ...
    - Replace numbers with NUM
    - Keep operators/symbols
    
    Returns: (normalized_tokens, identifier_map)
    """
    if language_keywords is None:
        language_keywords = set()
    
    normalized = []
    id_map = {}
    next_id = 1
    
    for tok in tokens:
        # Keep keywords
        if tok in language_keywords:
            normalized.append(tok)
        # Numbers → NUM
        elif re.fullmatch(r'\d+(\.\d+)?', tok):
            normalized.append("NUM")
        # Identifiers (start with letter or _)
        elif tok and (tok[0].isalpha() or tok[0] == "_"):
            if tok not in id_map:
                id_map[tok] = f"ID{next_id}"
                next_id += 1
            normalized.append(id_map[tok])
        else:
            # Operators/symbols
            normalized.append(tok)
    
    return normalized, id_map

def fingerprint_tokens(normalized_tokens, k=5):
    """
    Create k-shingles from normalized tokens and hash them
    
    Returns: set of SHA1 hex fingerprints
    """
    if k <= 0:
        raise ValueError("k must be >= 1")
    
    # Handle edge case: fewer tokens than k
    if len(normalized_tokens) < k:
        # Create one fingerprint from all available tokens
        if len(normalized_tokens) == 0:
            return set()  # Empty file
        
        joined = "\u241F".join(normalized_tokens)
        h = hashlib.sha1(joined.encode("utf-8")).hexdigest()
        return {h}
    
    # Normal case: create k-shingles
    fingerprints = set()
    for i in range(len(normalized_tokens) - k + 1):
        shingle = normalized_tokens[i:i+k]
        joined = "\u241F".join(shingle)
        h = hashlib.sha1(joined.encode("utf-8")).hexdigest()
        fingerprints.add(h)
    
    return fingerprints

def jaccard_similarity(set_a, set_b):
    """Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|"""
    if not set_a and not set_b:
        return 0.0  # Both empty → 0% similarity (changed from 1.0)
    if not set_a or not set_b:
        return 0.0  # One empty → 0% similarity
    
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    
    return intersection / union if union > 0 else 0.0

def aggregate_repo_similarity(per_file_info_A, per_file_info_B):
    """
    Compute overall repo similarity by:
    - Finding best match for each file
    - Weighting by token length
    - Averaging symmetrically (A→B and B→A)
    """
    if not per_file_info_A or not per_file_info_B:
        return 0.0
    
    # A → B direction
    total_weight_A = 0
    weighted_sum_A = 0.0
    
    for path, info in per_file_info_A.items():
        best_score = 0.0
        for other_path, other_info in per_file_info_B.items():
            sim = jaccard_similarity(info["fingerprints"], other_info["fingerprints"])
            if sim > best_score:
                best_score = sim
        
        weight = max(1, info["norm_len"])
        weighted_sum_A += best_score * weight
        total_weight_A += weight
    
    score_A = weighted_sum_A / total_weight_A if total_weight_A > 0 else 0.0
    
    # B → A direction (symmetric)
    total_weight_B = 0
    weighted_sum_B = 0.0
    
    for path, info in per_file_info_B.items():
        best_score = 0.0
        for other_path, other_info in per_file_info_A.items():
            sim = jaccard_similarity(info["fingerprints"], other_info["fingerprints"])
            if sim > best_score:
                best_score = sim
        
        weight = max(1, info["norm_len"])
        weighted_sum_B += best_score * weight
        total_weight_B += weight
    
    score_B = weighted_sum_B / total_weight_B if total_weight_B > 0 else 0.0
    
    # Final symmetric average
    return (score_A + score_B) / 2.0

def run_pipeline(repo1_path, repo2_path, k=5, out_file="detailed_output_claude.json"):
    """
    Main pipeline:
    1. Build trees & collect code files
    2. Process each file (tokenize, normalize, fingerprint)
    3. Compute pairwise similarities
    4. Aggregate repo similarity
    5. Save comprehensive JSON output
    """
    print(f"\n{'='*60}")
    print(f"🔍 PLAGIARISM DETECTION PIPELINE")
    print(f"{'='*60}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Shingle size (k): {k}")
    print(f"{'='*60}\n")
    
    repo1_path = os.path.abspath(repo1_path)
    repo2_path = os.path.abspath(repo2_path)
    
    # Step 1: Trees & code file lists
    print("📂 Step 1: Scanning repository structures...")
    tree1 = build_tree(repo1_path)
    tree2 = build_tree(repo2_path)
    code_files_repo1 = collect_code_files(repo1_path)
    code_files_repo2 = collect_code_files(repo2_path)
    
    print(f"   Repo A: {len(code_files_repo1)} code files")
    print(f"   Repo B: {len(code_files_repo2)} code files")
    
    tree_output = {
        "repo1_root": repo1_path,
        "repo2_root": repo2_path,
        "repo1_tree": tree1,
        "repo2_tree": tree2,
        "repo1_code_files": code_files_repo1,
        "repo2_code_files": code_files_repo2
    }
    
    with open("tree.json", "w", encoding="utf-8") as fh:
        json.dump(tree_output, fh, indent=2)
    print("   ✅ Saved: tree.json\n")
    
    # Step 2: Process each file
    print("🔄 Step 2: Processing files (tokenization & normalization)...")
    per_file_details = {}
    per_file_info_A = {}
    per_file_info_B = {}
    
    def process_repo(root_path, rel_paths, repo_label):
        for idx, rel in enumerate(rel_paths, 1):
            print(f"   [{repo_label}] {idx}/{len(rel_paths)}: {rel}")
            
            try:
                raw = read_file_text(root_path, rel)
                if not raw:
                    print(f"      ⚠️  Empty file, skipping")
                    continue
                
                # Remove comments
                raw_no_comments = remove_comments(raw)
                
                # Tokenize
                raw_tokens = tokenize_code_generic(raw_no_comments)
                print(f"      Raw tokens: {len(raw_tokens)}")
                
                # Normalize
                normalized_tokens, id_map = normalize_tokens(
                    raw_tokens, 
                    language_keywords=JAVA_KEYWORDS
                )
                print(f"      Normalized tokens: {len(normalized_tokens)}")
                print(f"      Unique identifiers: {len(id_map)}")
                
                # Fingerprint
                fingerprints = fingerprint_tokens(normalized_tokens, k=k)
                print(f"      Fingerprints: {len(fingerprints)}")
                
                # Store detailed info
                key = f"{repo_label}:{rel.replace(os.sep, '/')}"
                per_file_details[key] = {
                    "repo": repo_label,
                    "file": rel.replace(os.sep, '/'),
                    "raw_token_count": len(raw_tokens),
                    "normalized_token_count": len(normalized_tokens),
                    "unique_identifiers": len(id_map),
                    "raw_tokens": raw_tokens[:100],  # First 100 for debugging
                    "normalized_tokens": normalized_tokens[:100],
                    "identifier_map": id_map,
                    "fingerprints": sorted(list(fingerprints))[:20],  # First 20 hashes
                    "fingerprint_count": len(fingerprints),
                    "k": k
                }
                
                # Store minimal info for comparison
                info_min = {
                    "fingerprints": fingerprints,
                    "norm_len": len(normalized_tokens)
                }
                
                if repo_label == "A":
                    per_file_info_A[rel.replace(os.sep, '/')] = info_min
                else:
                    per_file_info_B[rel.replace(os.sep, '/')] = info_min
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
                continue
    
    process_repo(repo1_path, code_files_repo1, "A")
    print()
    process_repo(repo2_path, code_files_repo2, "B")
    print()
    
    # Step 3: Pairwise similarities
    print("🔗 Step 3: Computing pairwise file similarities...")
    similarity_scores = []
    
    for a_rel, a_info in per_file_info_A.items():
        for b_rel, b_info in per_file_info_B.items():
            sim = jaccard_similarity(a_info["fingerprints"], b_info["fingerprints"])
            similarity_scores.append({
                "fileA": a_rel,
                "fileB": b_rel,
                "jaccard_similarity": round(sim, 4),
                "similarity_percent": round(sim * 100, 2),
                "fileA_fingerprints": len(a_info["fingerprints"]),
                "fileB_fingerprints": len(b_info["fingerprints"]),
                "fileA_tokens": a_info["norm_len"],
                "fileB_tokens": b_info["norm_len"]
            })
    
    # Sort by similarity (high to low)
    similarity_scores.sort(key=lambda x: x["jaccard_similarity"], reverse=True)
    print(f"   Total comparisons: {len(similarity_scores)}")
    print()
    
    # Step 4: Repo-level aggregation
    print("📊 Step 4: Computing overall repository similarity...")
    overall_sim = aggregate_repo_similarity(per_file_info_A, per_file_info_B)
    print(f"   Overall similarity: {overall_sim:.4f} ({overall_sim*100:.2f}%)")
    print()
    
    # Save comprehensive output
    output = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "repo1_root": repo1_path,
            "repo2_root": repo2_path,
            "shingle_size_k": k,
            "repo1_files": len(per_file_info_A),
            "repo2_files": len(per_file_info_B),
            "total_comparisons": len(similarity_scores)
        },
        "tree": tree_output,
        "per_file_details": per_file_details,
        "pairwise_similarities": similarity_scores,
        "overall_repo_similarity": round(overall_sim, 4),
        "overall_repo_similarity_percent": round(overall_sim * 100, 2)
    }
    
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
    
    print(f"✅ Saved detailed output: {out_file}")
    print()
    
    # Print summary
    print(f"{'='*60}")
    print(f"📈 SUMMARY")
    print(f"{'='*60}")
    print(f"Repo A: {repo1_path}")
    print(f"  Files: {len(per_file_info_A)}")
    print(f"\nRepo B: {repo2_path}")
    print(f"  Files: {len(per_file_info_B)}")
    print(f"\nTop 5 Most Similar File Pairs:")
    print(f"{'-'*60}")
    
    for idx, r in enumerate(similarity_scores[:5], 1):
        print(f"{idx}. {r['fileA']}")
        print(f"   <--> {r['fileB']}")
        print(f"   Similarity: {r['similarity_percent']}% (Jaccard: {r['jaccard_similarity']})")
        print(f"   Fingerprints: A={r['fileA_fingerprints']}, B={r['fileB_fingerprints']}")
        print()
    
    print(f"{'='*60}")
    print(f"🎯 OVERALL REPOSITORY SIMILARITY: {overall_sim*100:.2f}%")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Complete plagiarism detection pipeline for GitHub repositories"
    )
    parser.add_argument("repo1", help="Path to repository 1")
    parser.add_argument("repo2", help="Path to repository 2")
    parser.add_argument("--k", type=int, default=5, help="Shingle size (default: 5)")
    parser.add_argument("--out", default="detailed_output_claude.json", 
                       help="Output JSON filename (default: detailed_output_claude.json)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.repo1):
        print(f"❌ Error: {args.repo1} is not a directory")
        sys.exit(1)
    if not os.path.isdir(args.repo2):
        print(f"❌ Error: {args.repo2} is not a directory")
        sys.exit(1)
    
    run_pipeline(args.repo1, args.repo2, k=args.k, out_file=args.out)