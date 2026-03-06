import numpy as np

M = np.reshape(np.arange(1, 8 * 9 + 1, dtype=np.float64), (9, 8))

L1 = M > 8
L2 = (M >= 14) & (M <= 30)
L3 = M % 3 == 0
L4 = (M % 4 == 0) & (M % 5 == 0)
L5 = (M % 4 == 0) | (M % 5 == 0)
L6 = M % 3 != 0
# Anmerkung: Alternativ kann man auch np.mod() statt dem
# modulo operator `%` verwenden
L7 = M > np.mean(M)
L8 = M >= np.max(M) * 0.75

anz_L1 = np.sum(L1)
anz_L2 = np.sum(L2)
anz_L3 = np.sum(L3)

anz_L2_L4 = np.sum(L2 & L4)

w_L6 = M[L6]
w_L5 = M[~L5]
w_L2_L5 = M[L2 & L5]

[iz6, is6] = np.where(L6)
i6 = np.where(L6.ravel())

M3 = np.copy(M)
M3[L3] = 14

M7 = np.copy(M)
mm7 = np.mean(M)
M7[L7] = mm7 + 1
M7[~L7] = mm7 - 1

eines_L3 = L3.any()
keines_L3 = not L3.any()

alle_L4 = np.all(L4)

nicht_alle_L4 = not np.all(L4)
# nicht_alle_L4 = np.any(~L4)

s1 = np.sum(M, axis=0)
sm1 = np.mean(s1)

Lsm1 = np.logical_and(s1 >= 0.8 * sm1, s1 <= sm1)
Ssm1 = M[:, Lsm1]

s2 = np.sum(M, axis=1)
sm2 = np.mean(s2)
Lsm2 = np.logical_and((s2 >= 0.8 * sm2), (s2 <= sm2))
Ssm2 = M[Lsm2, :]

S3 = M[Lsm2, Lsm1]
