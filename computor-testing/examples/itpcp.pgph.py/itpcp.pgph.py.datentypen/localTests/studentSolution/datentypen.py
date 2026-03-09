#######################################
#
# author: eudaemon
#
# project: Programmieren in der Physik
#
#######################################

#--imports--#
import numpy as np
import matplotlib.pyplot as plt

#--main--#
a = np.int8(80)
b = np.uint8(121)
c = np.uint16(116)
d = np.exp(4.645) # double ist standart
e = np.float64(111.111) # double ist standart
f = np.float32(141*np.pi/4)


# get type
typ_a = type(a).__name__
typ_b = type(b).__name__
typ_c = type(c).__name__
typ_d = type(d).__name__
typ_e = type(e).__name__
typ_f = type(f).__name__

# cast to int32
a = int(a)
b = int(b)
c = np.int32(c)
d = np.int32(d)
e = np.int32(e)
f = np.int32(f)

# convert to char
char_a = chr(a)
char_b = chr(b)
char_c = chr(c)
char_d = chr(d)
char_e = chr(e)
char_f = chr(f)

# concatenate chars
wort = char_a+char_b+char_c+char_d+char_e+char_f
print(wort)

# dangers of casting
test1 = np.double(1.8e-60)
test2 = np.double(1.4)
test3 = np.double(1.5)
test4 = np.double(128)

cast_test1 = np.float32(test1)
cast_test2 = np.uint8(test2)
cast_test3 = np.uint8(test3)
cast_test4 = np.uint8(test4)
cast_test5 = np.int8(cast_test4) #int overflow

# Kominationen von datentypen
pos_var_1 = np.uint8(255)
pos_var_2 = np.int8(1)
pos_var_3 = np.float64(1)
pos_var_4 = np.uint8(1)

# if 2 different dtypes python will 
# automatically cast to a correct type
p1_plus_p2 = pos_var_1 + pos_var_2
p1_plus_p3 = pos_var_1 + pos_var_3

# no recast happens so variable overflows
p1_plus_p4 = pos_var_1 + pos_var_4 
