import numpy as np
import matplotlib.pyplot as plt
import scipy.integrate as integrate


adder = lambda x, y: x + y
val1 = adder(5, 10)
val2 = adder(100, 20)


data = [(2, 3), (12, 3), (-4, 5), (6, -7), (8, 9), (-3, 11)]

sorted_y = sorted(data, key = lambda x: x[1])
sorted_r = sorted(data, key = lambda x: np.sqrt(x[0]**2 + x[1]**2))

print(sorted_y)
print(sorted_r)


l = [7, 2, 3, 12, 6, 13, 4]
evens = list(filter(lambda x: x % 2 == 0, l))

print(evens)




def calc_multiple(n):
    return lambda x: x * n

make_double = calc_multiple(2)
print(make_double(6))

tripler = calc_multiple(3)
print(tripler(6))





U_0 = 230*np.sqrt(2)
f = 50

T = 1/f


f_sin = lambda t: U_0*np.sin(2*np.pi*f*t)

f_abssin = lambda t: U_0*np.abs(np.sin(2*np.pi*f*t))

f_square = lambda t: U_0*np.sign(np.sin(2*np.pi*f*t))

f_saw = lambda t: -U_0 + np.mod(4*f*U_0*t, 2*U_0)



f_funcs = [f_sin, f_abssin, f_square, f_saw]

U_eff = np.zeros(4)
U_mean = np.zeros(4)
t = np.linspace(0, T, 500)



fig, axes = plt.subplots(4, 1, figsize = (10, 8), sharex = True)
for i, fun in enumerate(f_funcs):
    U_eff[i] = np.sqrt(1/T*integrate.simpson(fun(t)**2, x = t))
    U_mean[i] = 1/T*integrate.simpson(fun(t), x = t)
    axes[i].plot(t, fun(t),'-k', label = 'U(t)')
    axes[i].hlines(U_eff[i], 0, T, color = 'red', ls = 'dashed', label = r'$U_\mathrm{eff}$')
    axes[i].hlines(U_mean[i], 0, T, color = 'green', ls = 'dotted', label = r'$U_\mathrm{mean}$')
    axes[i].set_ylabel('U [V]', fontsize = 14) 
    axes[i].legend(loc = 'upper right')
    axes[i].set_xlim(0, 1.2*T)
    
axes[3].set_xlabel('t [s]', fontsize = 14)
plt.tight_layout()
plt.show()




#$META type "mandatory"
#$META title "Lambda Funktionen"

#$VARIABLETEST vars
#$TESTVAR data
#$TESTVAR sorted_y
#$TESTVAR sorted_r
#$TESTVAR l
#$TESTVAR evens
#$TESTVAR U_0
#$TESTVAR f
#$TESTVAR T
#$TESTVAR t



#$VARIABLETEST func1
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["val1 = adder(5, 10)"]
#$TESTVAR val1

#$VARIABLETEST func2
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["make_double = calc_multiple(2)\nval2=make_double(6)"]
#$TESTVAR val2

#$VARIABLETEST func3
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["val3=f_sin(np.pi/2)"]
#$TESTVAR val3

#$VARIABLETEST func4
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["val4=f_abssin(np.pi/2)"]
#$TESTVAR val4

#$VARIABLETEST func5
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["val5=f_square(np.pi/2)"]
#$TESTVAR val5

#$VARIABLETEST func6
#$PROPERTY entryPoint "lambda.py"
#$PROPERTY setUpCode ["val6=f_saw(np.pi/2)"]
#$TESTVAR val6