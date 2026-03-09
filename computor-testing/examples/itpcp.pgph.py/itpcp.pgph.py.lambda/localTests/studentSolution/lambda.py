"""
Week08/01_lambda
Tilman Gräbe
11917627
zum 15.05.24
"""


## import

import numpy as np
import matplotlib.pyplot as plt
import scipy.integrate as scint


## lamba

adder = lambda z1, z2: z1 + z2

data = [
    (2, 3), (12, 3), (-4, 5), (6, -7), (8, 9), (-3, 11)
]

sorted_r = sorted(data, key= lambda data: np.sqrt((data[:][0])**2 + (data[:][1])**2))
sorted_y = sorted(data, key= lambda data: data[:][1])

l = [7, 2, 3, 12, 6, 13, 4]
evens = list(filter(lambda x: x % 2 == 0, l))

def calc_multiple(n):
    return lambda x: x*n



## Periode

U_0 =230*np.sqrt(2)
f = 50

T = 1 / f

t = np.linspace(0, T, num=500)

f_sin = lambda t_sin: U_0 * np.sin(2*np.pi * f * t_sin)
f_abssin = lambda t_abssin: np.abs(f_sin(t_abssin))
f_square = lambda t_square: U_0 * np.sign(f_sin(t_square))
f_saw = lambda t_saw: np.mod(t_saw, (T/2)) * U_0*4*f - U_0


## Integral

array_f = np.array([f_sin(t), f_abssin(t), f_square(t), f_saw(t)])

U_mean = np.zeros(4)
U_eff = np.zeros(4)

fig, axs = plt.subplots(nrows=4)

for k_U in range(4):
    U_mean[k_U] = scint.simpson(array_f[k_U], x=t) * f
    U_eff[k_U] = np.sqrt(scint.simpson((array_f[k_U])**2, x=t) * f)

    axs[k_U].plot(t, array_f[k_U])
    axs[k_U].plot(t, U_mean[k_U] * np.ones(np.size(t)), label='$U_{mean}$')
    axs[k_U].plot(t, U_eff[k_U] * np.ones(np.size(t)), label='$U_{eff}$')


axs[0].set_title('$f_{sin}$')
axs[1].set_title('$f_{abssin}$')
axs[2].set_title('$f_{square}$')
axs[3].set_title('$f_{saw}$')

plt.tight_layout()
plt.legend()
plt.show()



## Probe

# print(
# U_mean, U_eff
# )

# plt.plot(t, f_saw(t))
# plt.plot(t, f_sin(t))
# plt.plot(t, f_abssin(t))
# plt.plot(t, f_square(t))
# plt.show()
