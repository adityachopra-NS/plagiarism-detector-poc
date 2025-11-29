import os
import sys

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


# NEW: Extensions that we consider as "code files"
CODE_EXTENSIONS = {
    ".py", ".java", ".c", ".cpp", ".js", ".ts",
    ".cs", ".go", ".rb", ".php"
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


# NEW: Function to collect only "code files" from a repo
def collect_code_files(root_path):
    """
    Walks through the directory and returns a sorted list of
    relative paths to files that have code extensions.
    """
    root_path = os.path.abspath(root_path)
    code_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Ignore unwanted folders like .git, node_modules, etc.
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

    # Sort paths for nice output
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


def main():
    if len(sys.argv) != 3:
        print("Usage: python repo_tree.py <path_to_repo1> <path_to_repo2>")
        sys.exit(1)

    repo1_path = sys.argv[1]
    repo2_path = sys.argv[2]

    if not os.path.isdir(repo1_path):
        print(f"Error: {repo1_path} is not a directory")
        sys.exit(1)
    if not os.path.isdir(repo2_path):
        print(f"Error: {repo2_path} is not a directory")
        sys.exit(1)

    # Build trees (already working)
    tree1 = build_tree(repo1_path)
    tree2 = build_tree(repo2_path)

    print("\n=== Repository 1 Structure ===")
    print_tree(tree1, os.path.basename(os.path.abspath(repo1_path)))

    print("\n=== Repository 2 Structure ===")
    print_tree(tree2, os.path.basename(os.path.abspath(repo2_path)))

    # NEW: Collect only code files
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


if __name__ == "__main__":
    main()
