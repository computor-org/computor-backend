# ChatGPT solution

import numpy as np

# Erzeugen der Matrix M mit float64 Typ
M = np.arange(1, 73, dtype=np.float64).reshape(9, 8)

# 1. Logische Felder
L1 = M > 8
L2 = (M >= 14) & (M <= 30)
L3 = M % 3 == 0
L4 = (M % 4 == 0) & (M % 5 == 0)
L5 = (M % 4 == 0) | (M % 5 == 0)
L6 = M % 3 != 0
L7 = M > np.mean(M)
L8 = M >= 0.75 * np.max(M)

# 2. Anzahl der Werte
anz_L1 = np.sum(L1)
anz_L2 = np.sum(L2)
anz_L3 = np.sum(L3)

# 3. Anzahl der Werte, die L2 und L4 erfüllen
anz_L2_L4 = np.sum(L2 & L4)

# 4. Vektoren der Werte
w_L6 = M[L6]
w_L5 = M[~L5]
w_L2_L5 = M[L2 & L5]

# 5. Zeilen- und Spaltenindex der Werte, die L6 erfüllen
iz6, is6 = np.where(L6)

# 6. Lineare Indizes der Werte, die L6 erfüllen
i6 = np.ravel_multi_index((iz6, is6), M.shape)

# 7. Matrix M3, bei der Werte, die L3 erfüllen, durch 14 ersetzt werden
M3 = M.copy()
M3[L3] = 14

# 8. Matrix M7 mit modifizierten Werten basierend auf L7
M7 = M.copy()
avg_M = np.mean(M)
M7[L7] = avg_M + 1
M7[~L7] = avg_M - 1

# 9. Mindestens ein Element, das L3 erfüllt
eines_L3 = np.any(L3)

# 10. Kein Element erfüllt L3
keines_L3 = not np.any(L3)

# 11. Alle Elemente erfüllen L4
alle_L4 = np.all(L4)

# 12. Nicht alle Elemente erfüllen L4
nicht_alle_L4 = not np.all(L4)

# 13. Zusätzliche Berechnungen
s1 = np.sum(M, axis=0)
sm1 = np.mean(s1)
Lsm1 = (s1 >= 0.8 * sm1) & (s1 <= sm1)
Ssm1 = M[:, Lsm1]

s2 = np.sum(M, axis=1)
sm2 = np.mean(s2)
Lsm2 = (s2 >= 0.8 * sm2) & (s2 <= sm2)
Ssm2 = M[Lsm2, :]

S3 = M[np.ix_(Lsm2, Lsm1)]

# Ausgaben zur Überprüfung
print(f"L1: {L1}\nL2: {L2}\nL3: {L3}\nL4: {L4}\nL5: {L5}\nL6: {L6}")
print(f"anz_L1: {anz_L1}, anz_L2: {anz_L2}, anz_L3: {anz_L3}, anz_L2_L4: {anz_L2_L4}")
print(f"w_L6: {w_L6}\nw_L5: {w_L5}\nw_L2_L5: {w_L2_L5}")
print(f"iz6: {iz6}, is6: {is6}, i6: {i6}")
print(f"M3: \n{M3}\nM7: \n{M7}")
print(f"eines_L3: {eines_L3}, keines_L3: {keines_L3}")
print(f"alle_L4: {alle_L4}, nicht_alle_L4: {nicht_alle_L4}")
print(f"s1: {s1}, sm1: {sm1}, Lsm1: {Lsm1}, Ssm1: \n{Ssm1}")
print(f"s2: {s2}, sm2: {sm2}, Lsm2: {Lsm2}, Ssm2: \n{Ssm2}")
print(f"S3: \n{S3}")
