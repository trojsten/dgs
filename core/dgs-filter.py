#!/usr/bin/env python2

# Skript co sa spusta v prostriedku pandoc konverzie a robi veci specificke
# pre nas. Konkretne:
#
# - hlada code blocks oznacene ```vstup a ```vystup a vyrobi okolo nich tu
#   spravnu omacku (v latexu prida nase I/O makra a v html popisky a ramceky)
# - hlada code blocks oznacene ```rawhtml, v latexu ich vyhodi a v html ich
#   obsah pouzije ako raw vystup
# - v latexu prerobi nadpisy na nase makra (\nadpis a \velkynadpis)
# - v html vyhodi velky nadpis (nazov ulohy je v contestovych nastaveniach)

import json
import sys

def vyrob(t, c):
    return { 't':t, 'c':c }

def match(a, b):
    if a == any or b == any: return True
    if type(a) == unicode: a = str(a.encode('utf-8'))
    if type(b) == unicode: b = str(b.encode('utf-8'))
    if type(a) != type(b): return False
    if type(a) == dict:
        a = sorted(a.items())
        b = sorted(b.items())
    if type(a) == list or type(a) == tuple:
        return len(a) == len(b) and all(match(x, y) for x, y in zip(a, b))
    return a == b

def jetyp(obj, t):
    return match(obj, vyrob(t, any))

def jekod(obj, cls):
    return match(obj, vyrob('CodeBlock', [['', [cls], []], any]))

latexvstupvystup = r'''\vstup
\begin{verbatim}
$
\end{verbatim}
\vystup
\begin{verbatim}
$
\end{verbatim}
\koniec'''

def html_filter(obj, items):
    if jekod(obj, "vstup") or jekod(obj, "vystup"):
        label = "Input:" if jekod(obj, "vstup") else "Output:"
        items.append(vyrob("Para", [vyrob("Strong", [vyrob("Str", label)])]))
        obj['c'][0][1] = ["iobox"]
        items.append(obj)
        return True

    if jekod(obj, 'rawhtml'):
        items.append(vyrob("RawBlock", ["html", obj['c'][1]]))
        return True

    if jetyp(obj, 'Header'):
        level, attr, content = obj['c']

        # skip top level headers in HTML output
        if level == 1:
            return True

        # other HTML headers start from <h3>
        obj['c'][0] += 1

    # hladaj odstavec co obsahuje jediny texovy prikaz
    if match(obj, vyrob('Para', [vyrob('RawInline', ['tex', any])])):
        prikaz = obj['c'][0]['c'][1]
        # ked je to \listing{../nieco}, tak precitaj ten subor a vyrob CodeBlock
        if prikaz.startswith('\\listing{../') and prikaz.endswith('}'):
            meno = prikaz[len('\\listing{../'):-len('}')]
            koncovka = meno.rpartition('.')[2]
            jazyky = { 'cc': 'cpp', 'cpp': 'cpp', 'pas': 'pascal', 'py': 'python' }
            jazyk = jazyky[koncovka]
            with open(meno) as f: obsah = f.read()
            items.append(vyrob('CodeBlock', [['', [jazyk], []], obsah]))
            return True

def latex_filter(obj, items):
    # ak predosly bol vstup a my sme vystup, tak to nahradime nasimi makrami
    if jekod(obj, "vystup") and len(items) and jekod(items[-1], "vstup"):
        vstup = items[-1]['c'][1]
        vystup = obj['c'][1]
        # za prvy dolar v sablone nahradime vstup a za druhy vystup
        t1, t2, t3 = latexvstupvystup.split('$')
        tex = t1 + vstup + t2 + vystup + t3
        items.pop()   # vyrveme items[-1] cize ```vstup
        items.append(vyrob("Para", [vyrob("RawInline", ["latex", tex])]))
        return True

    # ignorujeme ```rawhtml
    if jekod(obj, 'rawhtml'):
        return True

    # chceme nase vlastne nadpisy, nie standardne LaTeXove
    if jetyp(obj, 'Header'):
        level, attr, content = obj['c']
        options = dict(attr[2])
        vystup = []
        def tex(s): return [vyrob("RawInline", ["latex", s])]

        if level != 1:
            vystup += tex(r'\nadpis{') + content + tex(r'}')
        else:
            vystup += tex(r'\pocetbodovpopis{' + options['bodypopis'] + r'}')
            vystup += tex(r'\pocetbodovprog{' + options['bodyprogram'] + r'}')
            if 'tcko' in options:
                vystup += tex(r'\vzoraktcko{' + options['tcko'] + r'}{') + content + tex(r'}{' + options['vzorak'] + r'}')
            elif 'vzorak' in options:
                vystup += tex(r'\vzorak{') + content + tex(r'}{' + options['vzorak'] + r'}')
            else:
                vystup += tex(r'\zadanie{') + content + tex(r'}')

        items.append(vyrob("Para", vystup))
        return True


formats = { 'latex': latex_filter, 'html': html_filter }


def walk(obj, callback):
    if isinstance(obj, list):
        new_list = []
        for item in obj:
            item = walk(item, callback)
            if not callback(item, new_list):
                new_list.append(item)
        return new_list
    if isinstance(obj, dict):
        return dict((key, walk(value, callback)) for key, value in obj.items())
    return obj


if __name__ == '__main__':
    json.dump(walk(json.load(sys.stdin), formats[sys.argv[1]]), sys.stdout)
