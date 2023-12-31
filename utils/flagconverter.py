def flagconverter(code: str):
    if code == 'None':
        return ''
    res = f"{''.join(chr(127397 + ord(str.upper(k))) for k in code)}"
    return res
