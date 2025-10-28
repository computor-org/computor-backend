import numpy as np
import matplotlib.pyplot as plt
from fun_exp import fun_exp

x = np.linspace(0, 10 * np.pi, 250)
d = 0.1

y, A = fun_exp(x, d)

plt.figure()
plt.plot(x, A * y, "k")
plt.plot(x, A, "b")
plt.plot(x, -A, "b")

plt.xlim([min(x), max(x)])
plt.ylim([min(-A), max(A)])

plt.xlabel("x")
plt.ylabel("y(x)")

plt.title("Abklingender Cosinus")
plt.show()
