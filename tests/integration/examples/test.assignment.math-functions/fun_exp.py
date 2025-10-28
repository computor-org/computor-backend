import numpy as np

def fun_exp(x, d):
  cos_exp = 0.5 * np.real(np.exp(1j*x) + np.exp(-1j*x))
  A = np.exp(-d * x)
  return cos_exp, A

