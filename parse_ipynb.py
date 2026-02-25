import json

with open('Untitled30.ipynb', 'r', encoding='utf-8') as f:
    notebook = json.load(f)

code_content = []
for cell in notebook.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        code_content.append(''.join(source))

with open('Untitled30_code.py', 'w', encoding='utf-8') as f:
    f.write('\n\n# --- NEW CELL ---\n\n'.join(code_content))
