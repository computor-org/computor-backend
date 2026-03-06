# Datentypen (Klassen) in Python

## Einleitung

In dieser Aufgabe werden Variablen verschiedener (numerischer) Datentypen (File:
`datentypen.py`) erzeugt, der Datenyp der Variablen wird überprüft und die Variablen
werden umdeklariert (in einen anderen Typ verwandeln).

### Klassen in Python und NumPy

Grundsätzlich wird unterschieden zwischen den Klassen Boolean (logical), Numeric, Text
(string), Funktions- und Objekt-Referenzen und Strukturen wie Listen, Tupel,
Dictionaries, etc. Verschiedene Module können ihrerseits Klassen definieren (wir können
auch eigene Klassen definieren), wie zum Beispiel das viel verwendetete NumPy-Array, das
Zahlen von bestimmten Grundtypen enthalten kann. In dieser Übung beschränken wir uns auf
die numerischen Typen.

In Python selbst gibt es die numerischen Datentypen `bool` (*Boolean*, `True` oder
`False`), `int` (*integer*, Ganzzahl), `float` (*floating point with double precision*,
Gleitkommazahl), `complex` (komplexe Gleitkommazahl). Diese werden von Python
automatisch erkannt und müssen nicht angegeben werden.

```python
var_int = 3                 # integer
var_float = 3.              # float, double precision
var_float2 = 3.1            # float, double precision
var_string = 'hello world'  # string
var_compl = 4 + 1j          # complex double
```

Diese werden für numerische Programme mit den [NumPy-Datentypen] erweitert, welche
NumPy-Arrays zu Grunde liegen können. Zum Beispiel entspricht der Python `float` einem
`np.float64` (`numpy` wird oft mit `np` abgekürzt). Es gibt jedoch auch `np.float32`,
`np.float16`, etc. mit entsprechend vielen Bits für die Darstellung der Zahlen.

Einfach vorzustellen sind die Einschränkungen der Größe der Datentypen für Integer. Die
Ganzzahlen (Integer) beinhalten die *signed* (vorzeichenbehafteten, z.B. `int8`,
`int16`, …) und *unsigned* (nicht vorzeichenbehafteten, z.B. `uint8`, `uint16`, ...)
Integer. Hier hat `np.int8` zum Beispiel 8 Bit zur Verfügung. Die größte mögliche Zahl?
$127$, da natürlich auch negative Zahlen $\\ge -128$ möglich sind.

Und bei `uint8` (u steht für unsigned)? Hier ist die größte Zahl $2^8-1 = 255$.

Detailliertere Informationen kann man der Dokumentation über [NumPy-Datentypen]
entnehmen.

Der Datentyp `str` (sogenannte Zeichenketten oder auch *strings* genannt) tritt u.a. bei
der Beschriftung von Plots auf (z.B. mit `xlabel`).

List, Tuple, Dict, Set, ... funktionieren wie ein Sammelbehälter und können mehrere
Datentypen umfassen. Mehr Details dazu gibt es in der Zusatzübung zum Thema Strukturen.

In objektorientierten Programmiersprachen wie Python lassen sich eigene Klassen
(Datentypen) erzeugen (z.B. eine Klasse Polynome). In dieser Klasse kann man
beispielsweise eine Methode zur Addition von Polynomen definieren. Dadurch kann man auch
Operatoren wie `+`, `-`, `*`, `/` usw. *überladen*. Ein `+`-Operator, angewendet auf ein
Objekt der Klasse Polynome, würde dann die Polynomaddition durchführen.

Mit dem Befehl `type(var_name)` können Sie sich in der Konsole die Klasse der Variable
`var_name` anzeigen lassen. Um den Klassennamen als String zu speichern, greifen Sie auf
das Attribut `__name__` zu, also

```python
type(var_name).__name__
```

Handelt es sich bei der Variable um ein NumPy-Array, so kann man mit dem Attribut
`dtype` den Typ der gespeicherten numerischen Werte anzeigen.

Mit dem Befehl `help(var_name)` können Sie von einer Variable deren Klasse und alle für
sie definierten Befehle (`+` zum Beispiel als Funktion `__add__()`) anzeigen lassen.

## Aufgabe

1. Deklarieren Sie folgende 6 Variablen mit unterschiedlichen [NumPy-Datentypen] mit
   folgenden Werten. Für das automatische Testen ist es unbedingt notwendig, dass Sie
   <span style="color: red;">genau diese Namen</span> für Ihre Variablen verwenden!
   Benutzen Sie die Konsole zum Testen Ihres Programms!

   | Variable | Wert                | Datentyp |
   | -------- | ------------------- | -------- |
   | `a`      | $80$                | int8     |
   | `b`      | $121$               | uint8    |
   | `c`      | $116$               | uint16   |
   | `d`      | $e^{4.645}$         | double   |
   | `e`      | $111.111$           | double   |
   | `f`      | $\frac{141}{4} \pi$ | single   |

1. Speichern Sie nun die Datentypen der eben deklarierten Variablen `a` bis `f` unter
   den Namen `typ_a` bis `typ_f` ab.

1. Analog zur Deklaration von Variablen kann man sie auch umdeklarieren (einen neuen
   Datentyp zuweisen). Dies nennt man auch *cast* und wird z.B. folgendermaßen
   durchgeführt:

   ```python
   var = np.int8(1.34)
   var2 = np.float(var)
   ```

   Es ist sofort einsichtig, dass das nicht immer gefahrlos ist.

   Casten Sie nun alle eben definierten Dezimalzahlen als integer um (ersetzen Sie die
   alten Variablen durch die neuen Werte).

   Als nächstes deklarieren Sie die Variablen `a` bis `f` mit der Funktion [chr] auf den
   Datentyp `str` um. Speichern Sie das Ergebnis unter den Variablen `char_a` bis
   `char_f` ab.

   Die Klasse `str` in Python hat als Beispiel den Operator `+` so implementiert, dass
   dieser Zeichenketten einfach aneinanderreiht.

   Erstellen Sie nun die Variable `wort` wo Sie `char_a` bis `char_f` in alphabetischer
   Reihenfolge zusammenfügen und geben Sie den resultierenden String mit `print` aus.
   Überrascht?

1. Nun gehen wir auf die Gefahren dieser casts ein.

   Mit kleineren Datentypen kann einerseits Speicherplatz gespart werden, es kann daher
   aber auch beim Umdeklarieren (casten) Information verloren gehen. Definieren Sie
   folgende Variablen als `double`:

   | Variable | Wert                  |
   | -------- | --------------------- |
   | `test1`  | $1.8 \\cdot 10^{-60}$ |
   | `test2`  | $1.4$                 |
   | `test3`  | $1.5$                 |
   | `test4`  | $128$                 |

   Casten Sie die Variable `test1` auf den Typ `single` und speichern Sie das Ergebnis
   als `cast_test1` ab. Was passiert mit `test1`?

   Versuchen Sie die Variablen `test2` bis `test4` auf den Typ `uint8` zu casten
   (`cast_test2` bis `cast_test4`). Was fällt Ihnen auf? Was passiert, wenn Sie
   `cast_test4` auf den Typ `int8` casten (`cast_test5`)? Probiere nun für dich aus, ob
   das casten auch für `test_4` funktioniert. Beantworte dir selbst folgende Frage: Hat
   das etwas mit der Größe von dem Datentyp zu tun? (Um dies zu beantworten kann die
   `view` member Funktion von numpy's Datenypen (`np.uint16(22).view(np.int16)`)
   verwendet werden)

   Die Unterschiede, die man sieht, hängen zum Teil mit den größten, bzw., kleinsten
   darstellbaren Zahlen für einen bestimmten Datentyp zusammen. Der
   Python-Standarddatentyp `int` (`long`) hat keine Grenze in der Darstellbarkeit,
   allerdings sind die [NumPy-Datentypen] auf ihre Bitzahl beschränkt und meist
   systemabhängig. Um mehr herauszufinden, gibt es Befehle wie z.B.
   `np.finfo(np.float64)`, siehe Dokumentation zu [floatinfo] und [numpy.finfo].

1. Bei der Kombinationen verschiedener Datentypen ist zu beachten, dass Python (bzw.
   Numpy) automatisch auf den umfassenderen Datentyp castet.

   Erstellen Sie folgende Variablen

   | Variable    | Wert | Datentyp |
   | ----------- | ---- | -------- |
   | `pos_var_1` | 255  | uint8    |
   | `pos_var_2` | 1    | int8     |
   | `pos_var_3` | 1    | double   |
   | `pos_var_4` | 1    | uint8    |

   Speichern Sie nun in den Variablen `p1_plus_p2`, `p1_plus_p3` und `p1_plus_p4` die
   Summe der ersten und der zweiten, der ersten und der dritten bzw. der ersten und der
   vierten Variable.

   Stimmen die beiden Ergebnisse überein? Können Sie die Ergebnisse erklären?

## Hinweise

- Die Deklaration erfolgt in Python einfach in Form von `var = datentyp(wert)`, also
  z.B. `var = np.float32(1.13)`. Der Datentyp `double` bzw. `int` muss nicht
  spezifiziert werden, da dieser der Standardfall ist (Je nach Definition des Werts: 1.0
  oder 1).

[chr]: https://docs.python.org/3/library/functions.html#chr
[floatinfo]: https://docs.python.org/3/library/sys.html#sys.float_info
[numpy-datentypen]: https://numpy.org/doc/stable/user/basics.types.html
[numpy.finfo]: https://numpy.org/doc/stable/reference/generated/numpy.finfo.html
