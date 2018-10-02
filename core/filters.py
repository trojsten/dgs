def roman(number):
    number = int(number)
    if number == 0:
        return '0'
    if number > 4000:
        raise ValueError("Argument must be between 1 and 3999")

    ints = (1000,  900, 500,  400, 100,   90,  50,   40,  10,    9,   5,    4,   1)
    nums = ( 'M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = ""
    for i in range(len(ints)):
        count = int(number / ints[i])
        result += nums[i] * count
        number -= ints[i] * count
    return result

def formatList(list):
    return renderList(list, bold = True)

def renderList(items, **kwargs):
    if isinstance(items, str):
        items = [items]

    if not isinstance(items, list):
        raise TypeError("{} is not a list".format(items))

    if kwargs.get('bold', False):
        items = ['\\textbf{{{}}}'.format(x) for x in items]

    for i, item in enumerate(items[:-2]):
        items[i] = '{},'.format(item)

    if len(items) > 1:
        items[-2] = '{} a'.format(items[-2])
    
    return ' '.join(items)
