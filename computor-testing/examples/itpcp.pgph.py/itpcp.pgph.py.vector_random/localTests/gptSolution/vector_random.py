# ChatGPT solution

import numpy as np

# Erzeugung der Zufallsvektoren
rand1 = np.random.rand(10)                # 10 gleichverteilte Zufallszahlen im Intervall [0, 1)
rand2 = np.random.randn(20)               # 20 normalverteilte Zufallszahlen (Mittelwert 0, Standardabweichung 1)
rand_normal = np.random.normal(5, 0.2, 20)  # 20 normalverteilte Zufallszahlen (Mittelwert 5, Standardabweichung 0.2)

# Ganzzahlige Zufallszahlen
i_min = 5
i_max = 15
randint1 = np.random.randint(i_min, i_max + 1, 30)  # 30 gleichverteilte ganze Zufallszahlen im Intervall [i_min, i_max]


#print(np.random.rand(20))               #Auch möglich, keine Fehlermeldung
#print(np.random.rand(10))               