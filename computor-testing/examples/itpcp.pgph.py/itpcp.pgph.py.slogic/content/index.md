[np.all]: <https://numpy.org/doc/stable/reference/generated/numpy.all.html> "np.all"
[np.any]: <https://numpy.org/doc/stable/reference/generated/numpy.any.html> "np.any"
[np.where]: <https://numpy.org/doc/stable/reference/generated/numpy.where.html> "np.where"
[np.max]: <https://numpy.org/doc/stable/reference/generated/numpy.ndarray.max.html> "np.max"
[np.mean]: <https://numpy.org/doc/stable/reference/generated/numpy.mean.html> "np.mean"
[np.ravel]: <https://numpy.org/doc/stable/reference/generated/numpy.ravel.html> "np.ravel"
[np.sum]: <https://numpy.org/doc/stable/reference/generated/numpy.sum.html> "np.sum"

# Einfache logische Indizierung

## Einleitung

Erzeugen Sie eine Matrix `M` mit Einträgen von `1` bis `72`, die `9` Zeilen und `8` Spalten aufweist. Da wir diese kopieren und mit ihr rechnen werden, achten Sie darauf, dass es sich um `np.float64` Einträge handelt und keine `numpy.int32`. Verwenden Sie die Matrix für die folgenden Operationen.

## Aufgabe

Erzeugen Sie ein Python-Skript `slogic`, das folgende Aufgaben erfüllt:

1. Speichern Sie in den Variablen `L1` bis `L8` die **logischen Felder** für folgende
    Aufgabenstellungen bezüglich der Werte in `M`.

    Variable     | Aufgabe
    :------------|:------
    `L1` | Werte größer als 8
    `L2` | Werte größer gleich 14 und kleiner gleich 30
    `L3` | Werte durch drei teilbar (siehe modulo-Operator)
    `L4` | Werte durch vier und fünf teilbar
    `L5` | Werte durch vier oder fünf teilbar
    `L6` | Werte nicht durch drei teilbar
    `L7` | Werte größer als der Durchschnitt der Werte ([np.mean])
    `L8` | Werte größer gleich 75 Prozent des Maximalwertes ([np.max])

2. Berechnen Sie für `L1` bis `L3` die Anzahl der Werte, für die die entsprechende
     Bedingung gilt, und speichern Sie diese in den Variablen
    `anz_L1` bis `anz_L3`. (Siehe Hinweise)

3. Berechnen Sie in `anz_L2_L4` die Anzahl der Werte, für die die Bedingungen `L2` und `L4` gelten.

4. Erzeugen Sie je einen Vektor bestehend aus den Werten der Matrix `M`, die folgende Bedingung erfüllen:

    * `L6` (Variable: `w_L6`)
    * nicht `L5` (Variable: `w_L5`)
    * `L2` und `L5` (Variable: `w_L2_L5`).

5. Berechnen Sie den **Zeilen- und Spaltenindex** der Werte, für die die Bedingung `L6` gilt,
  in den Variablen `iz6` und `is6`  ([np.where]).

6. Berechnen Sie den **linearen** (einfachen) **Index** der Werte, für die die Bedingung `L6` gilt,
  in der Variablen `i6` ([np.ravel]).

7. Erzeugen Sie eine Matrix `M3`, die gleich der Matrix
  `M` ist. Ersetzen Sie in `M3` alle Werte, für die die Bedingung `L3`
  gilt, durch die Zahl 14.

8. Erzeugen Sie eine Matrix `M7`, die gleich der Matrix `M` ist.
    * Ersetzen Sie in `M7` alle Werte, für die die Bedingung `L7` gilt, durch einen Wert, der um eins *größer* ist
     als der Durchschittswert von `M`.
    * Ersetzen Sie dann in `M7` alle Werte für die die Bedingung `L7` **nicht** gilt durch einen Wert, der um eins
     *kleiner* ist als der Durchschittswert von `M`.
  
9. Speichern Sie in der Variable `eines_L3` die logische Antwort auf die Frage, ob
  **zumindest** für **ein** Element (Hinweis: [np.any]) in `M` die Bedingung `L3` gilt.
  
10. Speichern Sie in der Variable `keines_L3` die logische Antwort auf die Frage, ob
  für **kein** Element in `M` die Bedingung `L3` gilt (Überlegen Sie, wie das mit der vorherigen
  Aufgabe zusammenhängen könnte).
  
11. Speichern Sie in der Variable `alle_L4` die logische Antwort auf die
  Frage, ob für **alle** Elemente (Hinweis: [np.all]) in `M` die Bedingung `L4` gilt.
  
12. Speichern Sie in der Variable `nicht_alle_L4` die logische Antwort auf die Frage, ob
    **nicht** für **alle** Elemente in `M` die Bedingung `L4` gilt.

13. Erzeugen Sie die folgenden Variablen:

Variable     | Aufgabe
:------------|:------
`s1`   | Summe über alle Zeilen entlang der Spalten von `M`
`sm1`  | Mittelwert der Werte in `s1`
`Lsm1` | Logischer Vektor; `true` dort, wo `s1` zwischen 80% und 100% von `sm1` liegt (einschließlich).
`Ssm1` | Jene Teile (Spalten) von `M`, für die `Lsm1` gilt
`s2`   | Summe über alle Spalten entlang der Zeilen von `M`.
`sm2`  | Mittelwert der Werte in `s2`
`Lsm2` | Logischer Vektor; `true` dort, wo `s2` zwischen 80% und 100% von `sm2` liegt (einschließlich).
`Ssm2` | Jene Teile (Zeilen) von `M`, für die `Lsm2` gilt
`S3`   | Jene Teile von `M`, für die `Lsm1` und `Lsm2` gilt

## Hinweise

* Logisch wahr (``True``) wird in arithmetischen Operationen wie Addition und Multiplikation als 1 behandelt, logisch falsch (``False``) als 0. Die Anzahl wahrer Werte ist damit gleich ihrer Summe.

* Mit sogenannten *masks* kann man in Python Bool'sche Indizierung durchführen.

* Wie oben angemerkt, sind die Befehle [np.all] und [np.any] recht praktisch. Denken sie bei deren Verwendung, wie Befehle dieser Art angewandt werden müssen (siehe z.B. auch [np.sum]).
