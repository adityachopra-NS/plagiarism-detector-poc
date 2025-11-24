import os
import sys
import re
import json  # for writing tree.json


# Folders we usually don't care about
IGNORE_DIRS = {
    '.git',
    '__pycache__',
    'node_modules',
    '.metadata',      # Eclipse junk
    '.idea',          # IntelliJ
    '.vscode',        # VS Code
    'target',         # Maven build
    'build'           # Gradle build
}

# Extensions that we consider as "code files"
CODE_EXTENSIONS = {
    ".py", ".java", ".c", ".cpp", ".js", ".ts",
    ".cs", ".go", ".rb", ".php"
}

# Java keywords (for normalization; we will keep these as-is)
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


def build_tree(root_path):
    """
    Walks through a directory and builds a nested dict
    representing its folder/file structure.
    """
    tree = {}
    root_path = os.path.abspath(root_path)

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Sort for stable (predictable) output
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORE_DIRS
        )
        filenames = sorted(filenames)

        # Relative path of current folder from root
        rel_dir = os.path.relpath(dirpath, root_path)

        # Navigate to the correct subtree in our dict
        if rel_dir == '.':
            parts = []
        else:
            parts = rel_dir.split(os.sep)

        subtree = tree
        for p in parts:
            subtree = subtree.setdefault(p, {})

        # Add files (leaf nodes) with value None
        for f in filenames:
            subtree.setdefault(f, None)

    return tree


def collect_code_files(root_path):
    """
    Walks through the directory and returns a sorted list of
    relative paths to files that have code extensions.
    """
    root_path = os.path.abspath(root_path)
    code_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Ignore unwanted folders
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in IGNORE_DIRS
        )
        filenames = sorted(filenames)

        for f in filenames:
            _, ext = os.path.splitext(f)
            ext = ext.lower()

            if ext in CODE_EXTENSIONS:
                # relative path from root of repo
                rel_dir = os.path.relpath(dirpath, root_path)
                if rel_dir == '.':
                    rel_path = f
                else:
                    rel_path = os.path.join(rel_dir, f)

                code_files.append(rel_path)

    code_files.sort()
    return code_files


def print_tree(tree, root_name):
    """
    Nicely prints the nested dict as an ASCII tree.
    """
    print(root_name)
    _print_tree_inner(tree, prefix="")


def _print_tree_inner(tree, prefix=""):
    # Sort so that folders come before files, and names are alphabetic
    items = sorted(tree.items(), key=lambda x: (x[1] is None, x[0].lower()))

    for idx, (name, subtree) in enumerate(items):
        is_last = idx == len(items) - 1
        connector = "└── " if is_last else "├── "
        print(prefix + connector + name)

        if isinstance(subtree, dict):
            extension = "    " if is_last else "│   "
            _print_tree_inner(subtree, prefix + extension)


# ===== Step 2: Preprocessing & Normalization =====

def read_file_text(root_path, rel_path):
    """
    Given repo root and a relative file path, returns the file content as text.
    """
    full_path = os.path.join(root_path, rel_path)
    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def remove_comments_java(code):
    """
    Remove // line comments and /* ... */ block comments from Java-like code.
    This is a simple regex-based approach, good enough for our PoC.
    """
    # Remove /* ... */ (multiline) comments
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove // ... (single line) comments
    code = re.sub(r"//.*", "", code)
    return code


def tokenize_code_generic(code):
    """
    Very simple language-agnostic tokenizer.

    It will split code into:
    - identifiers / keywords (words like 'class', 'MovieSystemApplication')
    - numbers
    - multi-char operators (==, !=, <=, >=, &&, ||)
    - single-char symbols ({ } ( ) . , ; + - * / % < > = !)
    """
    token_pattern = r"""
        [A-Za-z_][A-Za-z0-9_]*   |   # identifiers / keywords
        \d+                      |   # numbers
        ==|!=|<=|>=|&&|\|\|      |   # multi-char operators
        [{}\[\]().,;:+\-*/%<>=!]     # single-char symbols
    """
    tokens = re.findall(token_pattern, code, flags=re.VERBOSE)
    return tokens


def normalize_tokens_java(tokens):
    """
    Normalizes tokens for Java-like languages:

    - Keep Java keywords as-is (if, for, class, etc.)
    - Replace identifiers (variable, class, method names) with generic IDs
      like ID1, ID2, ID3 ...
    - Replace numbers with NUM
    - Keep operators and symbols as-is
    """
    normalized = []
    identifier_map = {}
    next_id = 1

    for tok in tokens:
        # Keyword
        if tok in JAVA_KEYWORDS:
            normalized.append(tok)
        # Number
        elif tok.isdigit():
            normalized.append("NUM")
        # Identifier: starts with letter or underscore
        elif tok[0].isalpha() or tok[0] == "_":
            if tok not in identifier_map:
                identifier_map[tok] = f"ID{next_id}"
                next_id += 1
            normalized.append(identifier_map[tok])
        else:
            # Operator or symbol
            normalized.append(tok)

    return normalized


def preprocess_file_java(root_path, rel_path):
    """
    Full preprocessing pipeline for a Java file:
    - Read text
    - Remove comments
    - Tokenize
    - Normalize tokens
    Returns the list of normalized tokens.
    """
    code = read_file_text(root_path, rel_path)
    code_no_comments = remove_comments_java(code)
    tokens = tokenize_code_generic(code_no_comments)
    normalized_tokens = normalize_tokens_java(tokens)
    return normalized_tokens


def main():
    if len(sys.argv) != 3:
        print("Usage: python repo_tree_tokenization.py <path_to_repo1> <path_to_repo2>")
        sys.exit(1)

    repo1_path = sys.argv[1]
    repo2_path = sys.argv[2]

    if not os.path.isdir(repo1_path):
        print(f"Error: {repo1_path} is not a directory")
        sys.exit(1)
    if not os.path.isdir(repo2_path):
        print(f"Error: {repo2_path} is not a directory")
        sys.exit(1)

    # ==== Step 1: Trees and code file lists ====
    tree1 = build_tree(repo1_path)
    tree2 = build_tree(repo2_path)

    print("\n=== Repository 1 Structure ===")
    print_tree(tree1, os.path.basename(os.path.abspath(repo1_path)))

    print("\n=== Repository 2 Structure ===")
    print_tree(tree2, os.path.basename(os.path.abspath(repo2_path)))

    code_files_repo1 = collect_code_files(repo1_path)
    code_files_repo2 = collect_code_files(repo2_path)

    print("\n=== Repository 1 Code Files ===")
    if not code_files_repo1:
        print("(No code files found)")
    else:
        for path in code_files_repo1:
            print(" -", path)

    print("\n=== Repository 2 Code Files ===")
    if not code_files_repo2:
        print("(No code files found)")
    else:
        for path in code_files_repo2:
            print(" -", path)

    # ==== Save tree + code files info to tree.json ====
    output = {
        "repo1_root": os.path.abspath(repo1_path),
        "repo2_root": os.path.abspath(repo2_path),
        "repo1_tree": tree1,
        "repo2_tree": tree2,
        "repo1_code_files": code_files_repo1,
        "repo2_code_files": code_files_repo2,
    }

    with open("tree.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print('\nSaved tree + code file info to "tree.json"')

    # ==== Step 2: Demo preprocessing on one sample Java file ====
    # We'll pick the first .java file from repo1 (if any)
    sample_java = None
    for rel_path in code_files_repo1:
        if rel_path.lower().endswith(".java"):
            sample_java = rel_path
            break

    if sample_java is not None:
        print("\n=== Step 2 Demo: Preprocessing & Normalization ===")
        print(f"Sample Java file from Repo 1: {sample_java}")

        norm_tokens = preprocess_file_java(repo1_path, sample_java)
        print(f"Total normalized tokens: {len(norm_tokens)}")
        print("First 80 normalized tokens:")
        print(" ".join(norm_tokens[:80]))
    else:
        print("\n(No .java file found in Repo 1 for Step 2 demo)")


if __name__ == "__main__":
    main()