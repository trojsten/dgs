#!/usr/bin/env python3

def roman(what):
    what = int(what)
    if what == 0:
        return '0'
    if what > 4000:
        raise ValueError("Argument must be between 1 and 3999")

    ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
    nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
    result = ""
    for i in range(len(ints)):
        count = int(what / ints[i])
        result += nums[i] * count
        what -= ints[i] * count
    return result

def formatList(list):
    return renderList(list, bold = True)

def renderList(what, **kwargs):
    if (type(what) == str):
        what = [what]

    if kwargs.get('bold', False):
        what = ['\\textbf{{{}}}'.format(x) for x in what if x != '']

    for i, item in enumerate(what[:-2]):
        what[i] = '{},'.format(item)

    if len(what) > 1:
        what[-2] = '{} a'.format(what[-2])
    
    return ' '.join(what)

