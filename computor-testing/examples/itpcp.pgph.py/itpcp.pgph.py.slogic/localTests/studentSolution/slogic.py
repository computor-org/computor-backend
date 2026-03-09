import numpy as np

# Array erstellen
M = np.arange(1, 73).reshape(9, 8)

# Logische Felder
L1 = M > 8
L2 = np.logical_and(M >= 14, M <= 30)
L3 = M % 3 == 0
L4 = np.logical_and(M % 4 == 0, M % 5 == 0)
L5 = np.logical_or(M % 4 == 0, M % 5 == 0)
L6 = M % 3 != 0
L7 = M >= np.mean(M)
L8 = M >= 0.75 * np.max(M)

# Auswertung
anz_L1 = np.sum(L1)
anz_L2 = np.sum(L2)
anz_L3 = np.sum(L3)

anz_L2_L4 = np.sum(np.logical_and(L2, L4))

# Erzeugung von Spaltenvektoren
w_L6 = M[L6]
w_L5 = M[np.logical_not(L5)]
w_L2_L5 = M[np.logical_and(L2, L5)]

# Indizes für Bedingungen
iz6, is6 = np.where(L6)
i6 = np.where(np.ravel(L6))

# neue Matrizen (deepcopy)
M3 = np.copy(M)
M3[L3] = 14

M7 = np.copy(M)
M7[L7] = np.mean(M) + 1
M7[np.logical_not(L7)] = np.mean(M) - 1

# weitere Abfragen
eines_L3 = np.any(L3)
keines_L3 = not eines_L3

alle_L4 = np.all(L4)
nicht_alle_L4 = not alle_L4

# 13 Berechnungen
s1 = np.sum(M, 0) # Summe über Zeilen
sm1 = np.mean(s1)
Lsm1 = np.logical_and(s1 >= 0.8 * sm1, s1 <= sm1)
Ssm1 = M[:, Lsm1]

s2 = np.sum(M, 1)
sm2 = np.mean(s2)
Lsm2 = np.logical_and(s2 >= 0.8 * sm2, s2 <= sm2)
Ssm2 = M[Lsm2]

S3 = M[Lsm2, Lsm1]
