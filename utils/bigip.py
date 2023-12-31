def bigip(x):
    return '.'.join([str(y) for y in int.to_bytes(int(x), 4, 'big')])
