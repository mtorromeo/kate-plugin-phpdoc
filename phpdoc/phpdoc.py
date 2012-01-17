import kate
import subprocess
import os
import json
import re

from textwrap import dedent

def phpdoc_class(tokens):
    class_name = None
    for token in tokens:
        if token['name'] == 'T_STRING':
            class_name = token['source']
            break

    return ['/**', ' * %s' % class_name, ' */']

def phpdoc_function(tokens):
    function_name = None
    for token in tokens:
        if token['name'] == 'T_STRING':
            function_name = token['source']
            break

    # Build doc_block
    doc_block = ['/**', ' * %s' % function_name]

    arguments = []
    arg = {}
    for i, token in enumerate(tokens):
        if token['source'] in ('(', ','):
            if arg and arg['name']:
                arguments.append(arg)
            arg = {'name': None, 'type': 'mixed', 'optional': None}

        elif token['name'] == 'T_VARIABLE':
            prev_token = tokens[i-1]
            if prev_token['source'] not in ('(', ','):
                arg['type'] = prev_token['source']
            arg['name'] = token['source']

        elif token['source'] == '=':
            arg['optional'] = ' OPTIONAL'

        elif token['source'] == ')':
            if arg['name']:
                arguments.append(arg)
            break

    if arguments:
        doc_block.append(' *')
        for arg in arguments:
            doc_block.append(' * @param {type} {name}{optional}'.format(**arg))

    doc_block.append(' */')

    return doc_block

def phpdoc_variable(tokens):
    var_name = None
    for token in tokens:
        if token['name'] == 'T_VARIABLE':
            var_name = token['source']
            break

    return ['/**', ' * %s' % var_name, ' *', ' * @var mixed', ' */']

@kate.action('Insert phpDoc', shortcut='Meta+D', menu='Tools')
def add_phpdoc():
    document = kate.activeDocument()
    view = kate.activeView()
    pos = view.cursorPosition()

    if pos.line() == 0:
        return

    parser = subprocess.Popen( [ os.path.join( os.path.dirname(__file__), 'php-parse' ), "-" ], stdin = subprocess.PIPE, stdout = subprocess.PIPE )
    parser.stdin.write( document.text() )
    output = parser.communicate()[0]
    tokens = json.loads( output )

    if not tokens:
        return

    line = pos.line()+1

    # strip all tokens on lines after the cursor position
    for x, line_tokens in enumerate(tokens):
        if line_tokens['line'] > line:
            break

    if not x:
        return

    x -= 1
    tokens = tokens[:x]
    x -= 1

    print tokens

    # Find function/class definition start
    source_line = None
    while x:
        if tokens[x]['name'] in ('T_FUNCTION', 'T_CLASS'):
            source_line = tokens[x]['line']
            break
        if x and tokens[x]['name'] == 'T_VARIABLE' and tokens[x-1]['name'] in ('T_STATIC', 'T_PROTECTED', 'T_PUBLIC', 'T_PRIVATE', 'T_VAR'):
            source_line = tokens[x]['line']
            break
        x -= 1

    doc_block = None

    if not source_line:
        return

    tokens = tokens[x:]
    if tokens[0]['name'] == 'T_FUNCTION':
        doc_block = phpdoc_function(tokens)
    elif tokens[0]['name'] == 'T_CLASS':
        doc_block = phpdoc_class(tokens)
    elif tokens[0]['name'] == 'T_VARIABLE':
        doc_block = phpdoc_variable(tokens)

    if not doc_block:
        return

    # Indent docblock at the same level of the corresponding definition
    source_line -= 1

    sourcecode = document.line(source_line)
    m = re.search(r'^\s*', sourcecode)

    for i, line in enumerate(doc_block):
        doc_block[i] = "%s%s" % (m.group(0), line)
    doc_block = "\n".join(doc_block)+"\n"

    document.startEditing()
    pos.setPosition(source_line, 0)
    document.insertText(pos, doc_block)
    document.endEditing()
