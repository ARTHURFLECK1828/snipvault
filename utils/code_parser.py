"""Code parsing utilities for extracting functions, classes, and metadata."""

import ast
import re
from typing import List, Dict, Tuple


def extract_python_elements(code: str) -> List[Dict]:
    """
    Extract functions and classes from Python code using AST.

    Args:
        code: Python source code

    Returns:
        List of dictionaries with extracted elements
    """
    elements = []

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            # Extract functions
            if isinstance(node, ast.FunctionDef):
                element = {
                    'type': 'function',
                    'name': node.name,
                    'code': ast.get_source_segment(code, node),
                    'docstring': ast.get_docstring(node),
                    'line': node.lineno,
                    'decorators': [d.id if isinstance(d, ast.Name) else '' for d in node.decorator_list],
                    'args': [arg.arg for arg in node.args.args],
                }
                elements.append(element)

            # Extract classes
            elif isinstance(node, ast.ClassDef):
                element = {
                    'type': 'class',
                    'name': node.name,
                    'code': ast.get_source_segment(code, node),
                    'docstring': ast.get_docstring(node),
                    'line': node.lineno,
                    'bases': [base.id if isinstance(base, ast.Name) else '' for base in node.bases],
                    'decorators': [d.id if isinstance(d, ast.Name) else '' for d in node.decorator_list],
                }
                elements.append(element)

    except SyntaxError:
        # If code has syntax errors, return empty list
        pass

    return elements


def extract_javascript_functions(code: str) -> List[Dict]:
    """
    Extract functions from JavaScript/TypeScript code using regex.

    Args:
        code: JavaScript source code

    Returns:
        List of dictionaries with extracted functions
    """
    elements = []

    # Pattern for function declarations
    func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{'

    # Pattern for arrow functions assigned to const/let/var
    arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'

    # Pattern for class methods
    method_pattern = r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{'

    for match in re.finditer(func_pattern, code):
        elements.append({
            'type': 'function',
            'name': match.group(1),
            'line': code[:match.start()].count('\n') + 1,
        })

    for match in re.finditer(arrow_pattern, code):
        elements.append({
            'type': 'function',
            'name': match.group(1),
            'line': code[:match.start()].count('\n') + 1,
        })

    return elements


def extract_docstring_from_code(code: str, language: str) -> str:
    """
    Extract docstring or comments from code.

    Args:
        code: Source code
        language: Programming language

    Returns:
        Extracted docstring or empty string
    """
    if language == 'python':
        try:
            tree = ast.parse(code)
            docstring = ast.get_docstring(tree)
            return docstring or ''
        except:
            return ''

    # For other languages, try to extract first comment block
    lines = code.split('\n')
    docstring_lines = []

    for line in lines:
        stripped = line.strip()
        # Check for comment patterns
        if stripped.startswith('//') or stripped.startswith('#'):
            docstring_lines.append(stripped.lstrip('/#').strip())
        elif stripped.startswith('/*') or stripped.startswith('*'):
            docstring_lines.append(stripped.lstrip('/*').rstrip('*/').strip())
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            # Python-style docstrings in other files
            docstring_lines.append(stripped.strip('"\'').strip())
        elif docstring_lines:
            # Stop when we hit non-comment line after comments started
            break

    return ' '.join(docstring_lines)


def extract_imports(code: str, language: str) -> List[str]:
    """
    Extract import statements from code.

    Args:
        code: Source code
        language: Programming language

    Returns:
        List of imported modules/packages
    """
    imports = []

    if language == 'python':
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except:
            pass

    elif language in ['javascript', 'typescript']:
        # Match import statements
        import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        require_pattern = r"require\(['\"]([^'\"]+)['\"]\)"

        for match in re.finditer(import_pattern, code):
            imports.append(match.group(1))

        for match in re.finditer(require_pattern, code):
            imports.append(match.group(1))

    return imports


def generate_auto_tags(code: str, language: str, filename: str = '') -> List[str]:
    """
    Generate automatic tags based on code analysis.

    Args:
        code: Source code
        language: Programming language
        filename: Optional filename

    Returns:
        List of suggested tags
    """
    tags = set()

    # Add language as a tag
    tags.add(language)

    # Extract imports and use them as tags
    imports = extract_imports(code, language)
    for imp in imports[:5]:  # Limit to 5 imports
        # Extract package name (first part)
        package = imp.split('.')[0].split('/')[0]
        if package and len(package) > 2:
            tags.add(package)

    # Check for common patterns
    code_lower = code.lower()

    # API/HTTP patterns
    if any(keyword in code_lower for keyword in ['fetch', 'axios', 'requests', 'http', 'api']):
        tags.add('api')

    # Database patterns
    if any(keyword in code_lower for keyword in ['database', 'sql', 'query', 'select', 'insert']):
        tags.add('database')

    # Testing patterns
    if any(keyword in code_lower for keyword in ['test', 'assert', 'expect', 'describe', 'it(']):
        tags.add('testing')

    # Async patterns
    if any(keyword in code_lower for keyword in ['async', 'await', 'promise', 'then']):
        tags.add('async')

    # File I/O patterns
    if any(keyword in code_lower for keyword in ['file', 'read', 'write', 'open']):
        tags.add('file-io')

    # Authentication patterns
    if any(keyword in code_lower for keyword in ['auth', 'login', 'password', 'token', 'jwt']):
        tags.add('authentication')

    # Class/OOP patterns
    if language == 'python' and 'class ' in code:
        tags.add('class')
    elif language in ['javascript', 'typescript'] and 'class ' in code:
        tags.add('class')

    # Filename-based tags
    if filename:
        if 'test' in filename.lower():
            tags.add('testing')
        if 'util' in filename.lower() or 'helper' in filename.lower():
            tags.add('utility')

    return sorted(list(tags))


def should_extract_as_snippet(code: str, language: str) -> bool:
    """
    Determine if code is substantial enough to be a snippet.

    Args:
        code: Source code
        language: Programming language

    Returns:
        True if code should be extracted as snippet
    """
    lines = [line.strip() for line in code.split('\n') if line.strip()]

    # Filter out comment-only lines
    code_lines = [
        line for line in lines
        if not line.startswith('#') and
           not line.startswith('//') and
           not line.startswith('/*') and
           not line.startswith('*')
    ]

    # Must have at least 3 lines of actual code
    if len(code_lines) < 3:
        return False

    # Must be less than 500 lines (too large)
    if len(code_lines) > 500:
        return False

    return True
