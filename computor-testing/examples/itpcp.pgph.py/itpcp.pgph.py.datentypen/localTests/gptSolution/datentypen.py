# ChatGPT solution

import numpy as np

# 1. Declare variables with specific NumPy data types
a = np.int8(80)                # int8
b = np.uint8(121)              # uint8
c = np.uint16(116)             # uint16
d = np.float64(np.exp(4.645)) # double (float64)
e = np.float64(111.111)        # double (float64)
f = np.float32(141/4 * np.pi)  # single (float32)

# 2. Save data types of the variables
typ_a = type(a).__name__
typ_b = type(b).__name__
typ_c = type(c).__name__
typ_d = type(d).__name__
typ_e = type(e).__name__
typ_f = type(f).__name__

print(f'typ_a: {typ_a}')
print(f'typ_b: {typ_b}')
print(f'typ_c: {typ_c}')
print(f'typ_d: {typ_d}')
print(f'typ_e: {typ_e}')
print(f'typ_f: {typ_f}')

# 3. Cast variables to integer
a = int(a)
b = int(b)
c = int(c)
d = int(d)
e = int(e)
f = int(f)

# Cast to string using chr and create combined string
char_a = chr(a)
char_b = chr(b)
char_c = chr(c)
char_d = chr(d)
char_e = chr(e)
char_f = chr(f)

# Combine characters into a string
wort = ''.join(sorted([char_a, char_b, char_c, char_d, char_e, char_f]))

print(f'Combined string: {wort}')

# 4. Test casting with double to single and various integers
test1 = np.float64(1.8e-60)
test2 = np.float64(1.4)
test3 = np.float64(1.5)
test4 = np.float64(128)

cast_test1 = np.float32(test1)
cast_test2 = np.uint8(test2)
cast_test3 = np.uint8(test3)
cast_test4 = np.uint8(test4)
cast_test5 = np.int8(test4)

print(f'cast_test1: {cast_test1}')
print(f'cast_test2: {cast_test2}')
print(f'cast_test3: {cast_test3}')
print(f'cast_test4: {cast_test4}')
print(f'cast_test5: {cast_test5}')

# 5. Combining variables of different types
pos_var_1 = np.uint8(255)
pos_var_2 = np.int8(1)
pos_var_3 = np.float64(1)
pos_var_4 = np.uint8(1)

p1_plus_p2 = pos_var_1 + pos_var_2
p1_plus_p3 = pos_var_1 + pos_var_3
p1_plus_p4 = pos_var_1 + pos_var_4

print(f'p1_plus_p2: {p1_plus_p2}')
print(f'p1_plus_p3: {p1_plus_p3}')
print(f'p1_plus_p4: {p1_plus_p4}')
