import numpy as np

a = np.int8(80)
b = np.uint8(121)
c = np.uint16(116)
d = np.double(np.exp(4.645))
e = np.double(111.111)
f = np.single(141 / 4 * np.pi)

typ_a = type(a).__name__
typ_b = type(b).__name__
typ_c = type(c).__name__
typ_d = type(d).__name__
typ_e = type(e).__name__
typ_f = type(f).__name__

a = int(a)
b = int(b)
c = int(c)
d = int(d)
e = int(e)
f = int(f)

char_a = chr(a)
char_b = chr(b)
char_c = chr(c)
char_d = chr(d)
char_e = chr(e)
char_f = chr(f)

wort = char_a + char_b + char_c + char_d + char_e + char_f

print(wort)

test1 = 1.8e-60
test2 = 1.4
test3 = 1.5
test4 = 128

cast_test1 = np.single(test1)
cast_test2 = np.uint8(test2)
cast_test3 = np.uint8(test3)
cast_test4 = np.uint8(test4)
cast_test5 = np.int8(cast_test4)


pos_var_1 = np.uint8(255)
pos_var_2 = np.int8(1)
pos_var_3 = np.double(1)
pos_var_4 = np.uint8(1)

p1_plus_p2 = pos_var_1 + pos_var_2
p1_plus_p3 = pos_var_1 + pos_var_3
p1_plus_p4 = pos_var_1 + pos_var_4
