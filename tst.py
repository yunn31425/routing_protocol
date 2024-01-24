import struct

def encode_8float(coord_float):
    '''
    encode vaild time from  to binary
    '''
    mantissa = 0
    exponent = 0
    C = 0.0625

    # Calculate the exponent first
    while coord_float > C:
        coord_float /= 2
        exponent += 1
    print(coord_float)

    # Calculate the mantissa
    mantissa = int(((coord_float / C) - 1) * 16)
    # Combine mantissa and exponent into Htime
    Htime = (mantissa << 8) | exponent
    print(mantissa, exponent)
    return Htime

print(encode_8float(37.234246))
print(float(37.234246).hex())
