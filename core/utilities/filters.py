def roman(number):
    number = int(number)
    if number == 0:
        return '0'
    if number > 4000:
        raise ValueError("Argument must be between 1 and 3999")

    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = ""
    for i in range(len(ints)):
        count = int(number / ints[i])
        result += nums[i] * count
        number -= ints[i] * count
    return result


def isotex(date):
    return date.strftime('%Y--%m--%d')


def format_list(list):
    return render_list(list, bold=True)


def render_list(items, *, bold=False):
    if not isinstance(items, list):
        items = [items]

    if bold:
        items = [f"\\textbf{{{x}}}" for x in items]

    for i, item in enumerate(items[:-2]):
        items[i] = f"{item},"

    if len(items) > 1:
        items[-2] = f"{items[-2]} a"

    return ' '.join(items)
