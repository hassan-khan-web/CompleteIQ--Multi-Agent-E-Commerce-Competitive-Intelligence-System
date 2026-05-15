import tokenize
import io
import os
import ast

def clean_file(filepath):
    with open(filepath, 'r') as f:
        source = f.read()
    
        result = []
    g = tokenize.generate_tokens(io.StringIO(source).readline)
    for toktype, tokval, _, _, _ in g:
        if toktype != tokenize.COMMENT:
            result.append((toktype, tokval))
    
    source_no_comments = tokenize.untokenize(result)
    
    tree = ast.parse(source_no_comments)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                node.body.pop(0)
    
    clean_source = ast.unparse(tree)
    
    lines = clean_source.splitlines()
    final_lines = []
    for line in lines:
        if line.strip():
            final_lines.append(line)
        elif final_lines and final_lines[-1].strip():
            final_lines.append("")
    
    with open(filepath, 'w') as f:
        f.write("\n".join(final_lines))

if __name__ == "__main__":
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and file != "clean_code.py":
                print(f"Cleaning {file}...")
                try:
                    clean_file(os.path.join(root, file))
                except Exception as e:
                    print(f"Error cleaning {file}: {e}")
