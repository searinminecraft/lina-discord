def flagconverter(code: str):
    if code is None:
        return ''
    res = f"{''.join(chr(127397 + ord(str.upper(k))) for k in code)}"
    return res
