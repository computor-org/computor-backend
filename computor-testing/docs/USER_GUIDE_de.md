# Computor Testing Framework – Anleitung

Diese Anleitung richtet sich an **Aufgabenautor:innen**, die test.yaml-Dateien schreiben und mit dem Framework die Abgaben von Studierenden testen.

---

## Schnellstart

### 1. Installieren

Installiere die Pakete im Hauptverzeichnis einer lokalen Kopie des Repositorys `computor-backend`, weil `computor-types` nicht auf PyPI liegt:

```bash
pip install -e ./computor-types -e ./computor-testing
```

### 2. Umgebung prüfen

```bash
computor-test check --all
```

### 3. test.yaml anlegen

```bash
# Mit der Blocks-CLI eine Ausgangsdatei erzeugen
blocks init -l python -n "My Exercise Tests"

# Oder von Hand anlegen (siehe die Beispiele unten)
```

### 4. Tests ausführen

```bash
computor-test python run -t ./student -T test.yaml
```

---

## Verzeichnisstruktur

Dein Aufgabenverzeichnis sollte so aussehen:

```
my-exercise/
├── test.yaml                  # Testdefinitionen (erforderlich)
├── meta.yaml                  # Metadaten (zum Hochladen auf die Plattform erforderlich)
├── content/
│   └── index_en.md            # Aufgabenstellung, eine Datei pro Sprache
├── reference/                 # Musterlösung
│   └── solution.py
├── localTests/
│   ├── correctSolution/       # Soll alle Tests bestehen
│   │   └── solution.py
│   └── wrongSolution/         # Soll einige Tests nicht bestehen
│       └── solution.py
└── output/
    └── testSummary.json       # Erzeugte Testergebnisse
```

---

## test.yaml schreiben

### Grundstruktur

```yaml
name: Exercise Name
description: What this exercise tests
type: python           # python, octave, r, julia, c, fortran, document
version: "1.0"

properties:
  relativeTolerance: 1e-12    # Standardwert für numerische Vergleiche
  absoluteTolerance: 0.0001
  timeout: 180                # Sekunden

  tests:
    - type: exist             # Testsammlung
      name: File Check
      tests:
        - name: solution.py   # Einzelner Test

    - type: variable
      name: Variable Tests
      entryPoint: solution.py
      tests:
        - name: result
          value: 42
```

### Vererbung von Eigenschaften

Eigenschaften, die auf der Ebene `properties:` gesetzt sind, dienen als Standardwerte. Eine Testsammlung kann sie überschreiben, und ihre Werte kann wiederum ein einzelner Test überschreiben.

Diese Vererbung gilt in allen Testern für `qualification`, `relativeTolerance`,
`absoluteTolerance`, `typeCheck`, `shapeCheck`, `ignoreClass` und `verbosity`,
während von `properties:` an die Sammlungen außerdem `timeout`,
`storeGraphicsArtifacts` und `competency` weitergegeben werden.
`allowedOccuranceRange` und `occuranceType` werden nicht vererbt, weshalb du sie
bei jedem Test setzen musst, der sie braucht.

---

## Testtypen

### exist – Vorhandensein von Dateien

Dieser Testtyp steht für alle Sprachen zur Verfügung und prüft, ob die geforderten Dateien vorhanden sind.

```yaml
- type: exist
  name: Required Files
  tests:
    - name: solution.py          # Exakter Dateiname
    - name: data/*.csv           # Glob-Muster
    - name: config.json
      allowEmpty: true           # Dateien mit 0 Byte zulassen (Standardwert: false)
```

### variable – Vergleich von Variablen

Verfügbar für: Python, Octave, R, Julia

Dieser Testtyp führt ein Skript aus und vergleicht die Variablen, die nach dem Lauf des Skripts vorliegen, mit den erwarteten Werten.

```yaml
- type: variable
  name: Computation Tests
  entryPoint: solution.py          # Auszuführendes Skript
  tests:
    - name: result                 # Name der Variable
      value: 42                    # Erwarteter Wert

    - name: matrix
      value: [[1, 2], [3, 4]]     # Arrays und Matrizen

    - name: pi_approx
      value: 3.14159
      relativeTolerance: 1e-4     # Überschreibt die Standardtoleranz

    - name: greeting
      value: "Hello, World!"
```

#### Mit Setup- und Teardown-Code

```yaml
- type: variable
  name: Advanced Tests
  entryPoint: solution.py
  setUpCode:
    - "x = 10"                     # Python und Octave: läuft nach dem Einstiegspunkt
    - "y = compute(x)"
  tearDownCode:
    - "cleanup()"                  # Läuft nach setUpCode, bevor die Variablen gelesen werden
  tests:
    - name: y
      value: 100
```

#### Mit Eingabe (stdin)

```yaml
- type: variable
  name: Interactive Tests
  entryPoint: solution.py
  inputAnswers:
    - "5"                          # Der erste input()-Aufruf erhält "5"
    - "hello"                      # Der zweite input()-Aufruf erhält "hello"
  tests:
    - name: result
      value: 5
```

### stdout – Vergleich der Ausgabe

Verfügbar für: C, Fortran, Python, R, Julia

```yaml
- type: stdout
  name: Output Tests
  entryPoint: main.c
  tests:
    - name: greeting
      qualification: contains      # Prüft, ob die Ausgabe diesen Text enthält
      pattern: "Hello"

    - name: exact
      qualification: matches       # Exakte Übereinstimmung
      value: "Hello, World!\n"

    - name: pattern
      qualification: regexp        # Treffer eines regulären Ausdrucks
      pattern: "Result: \\d+"

    - name: prefix
      qualification: startsWith
      pattern: "Program"

    - name: suffix
      qualification: endsWith
      pattern: "Done."
```

Ohne `qualification` wird die Ausgabe mit `value` verglichen oder, falls kein
`value` angegeben ist, mit der Ausgabe der Musterlösung. C und Fortran entfernen
vor dem Vergleich den Leerraum am Anfang und Ende der Ausgabe und akzeptieren
`value` auch anstelle von `pattern`. Python vergleicht die unveränderte Ausgabe
und entnimmt den erwarteten Text bei jeder `qualification`, auch bei `matches`,
aus `pattern`. R und Julia unterstützen `contains` und `regexp` (und behandeln
`matches` als regulären Ausdruck).

### structural – Struktur des Codes

Dieser Testtyp steht für alle Sprachen zur Verfügung und sucht im Quellcode nach Schlüsselwörtern oder Mustern.

```yaml
- type: structural
  name: Code Structure
  file: solution.py                # Zu analysierende Datei
  tests:
    - name: no_eval                # Sprechender Name
      pattern: "\\beval\\b"        # Gesuchter regulärer Ausdruck
      allowedOccuranceRange: [0, 0]  # Darf nicht vorkommen (verboten)

    - name: uses_function
      pattern: "\\bdef\\b"
      allowedOccuranceRange: [1, 0]  # Mindestens einmal, ohne Obergrenze

    - name: for_loop
      pattern: "\\bfor\\b"
      allowedOccuranceRange: [2, 5]  # Muss 2- bis 5-mal vorkommen
```

**Hinweis zu `allowedOccuranceRange`:** Das Format lautet `[min, max]`:

| Wert | Bedeutung |
| --- | --- |
| `[0, 0]` | Das Element darf **überhaupt nicht** vorkommen |
| `[n, 0]` (n > 0) | Mindestens `n` Vorkommen, ohne Obergrenze |
| `[min, max]` | Zwischen `min` und `max` Vorkommen, einschließlich der Grenzen |

Alternativ verlangt `countRequirement: n` eine exakte Anzahl, was allerdings nur
gilt, wenn `allowedOccuranceRange` nicht gesetzt ist; ein Untertest ohne beide
Angaben wird übersprungen.

In Python wird `name` mit dem Token-Strom abgeglichen, sodass gepunktete Namen
wie `np.pi` als Einheit gezählt und Treffer in Kommentaren und Zeichenketten
ignoriert werden. Gibst du stattdessen ein `pattern` an, sucht der Test mit einem
regulären Ausdruck im unveränderten Dateitext, der Kommentare und Zeichenketten
einschließt.

R und Julia zählen `pattern` (oder `name`) auf dieselbe Weise. Octave ignoriert
`pattern` und zählt das Schlüsselwort oder die Funktion, die als `name` angegeben
ist. C und Fortran wenden den Bereich auf bekannte Schlüsselwörter an, die als
`name` angegeben sind (etwa `for` oder `malloc`); bei allen anderen Tests prüfen
sie nur, ob `pattern` (oder `name`) im Quellcode vorkommt.

### exitcode – Prüfung des Exit-Codes (C, Fortran)

```yaml
- type: exitcode
  name: Exit Code
  entryPoint: main.c
  tests:
    - name: success
      expectedExitCode: 0

    - name: error_case
      expectedExitCode: 1
```

### compile – Kompilierungstest (C, Fortran)

```yaml
- type: compile
  name: Compilation
  entryPoint: main.c
  compiler: gcc
  compilerFlags: ["-Wall", "-Wextra", "-Werror"]
  tests:
    - name: compiles_clean         # Soll ohne Fehler kompilieren
```

### graphics – Test von Plots (Python, Octave)

Jedes `name` ist ein Ausdruck, der ausgewertet wird, nachdem das Skript gelaufen
ist. In Python wird ihm `plt.` vorangestellt, in Octave wird er so ausgewertet,
wie er dasteht. Das Ergebnis wird mit `value` oder mit der Musterlösung verglichen.

```yaml
- type: graphics
  name: Plot Tests
  entryPoint: plot_script.py
  tests:
    - name: gcf().axes[0].get_xlabel()
      value: "Time"
    - name: gcf().axes[0].get_title()
      value: "Data Plot"
```

```yaml
- type: graphics
  name: Plot Tests
  entryPoint: plot_script.m
  tests:
    - name: get(gca, 'XLim')
      value: [0, 10]
```

### Testtypen für Dokumente

Verfügbar für: Document

```yaml
type: document

properties:
  tests:
    - type: wordcount
      name: Word Count
      file: essay.md
      tests:
        - name: minimum_words
          allowedOccuranceRange: [500, 0]   # Mindestens 500 Wörter

    - type: section
      name: Required Sections
      file: essay.md
      tests:
        - name: Introduction
        - name: Methodology
        - name: Conclusion

    - type: keyword
      name: Keywords
      file: essay.md
      tests:
        - name: algorithm
          allowedOccuranceRange: [3, 0]     # Mindestens 3 Vorkommen

    - type: linecount
      name: Line Count
      file: essay.md
      tests:
        - name: minimum_lines
          allowedOccuranceRange: [50, 0]
```

---

## Tests vom Erfolg früherer Tests abhängig machen

Du kannst Testsammlungen vom Erfolg vorhergehender Sammlungen abhängig machen:

```yaml
properties:
  tests:
    - type: exist
      name: File Check
      id: file_check              # Vergibt eine ID
      tests:
        - name: solution.py

    - type: variable
      name: Variable Tests
      entryPoint: solution.py
      successDependency: file_check   # Läuft nur, wenn File Check bestanden wurde
      tests:
        - name: result
          value: 42
```

---

## Token-Ersetzung

In Octave-Tests lassen sich Dateien, die frühere `exist`-Tests gefunden haben, im
`file` eines `structural`-Tests als `#file_N#` ansprechen (`N` zählt ab 1):

```yaml
- type: exist
  name: Script
  tests:
    - name: "*.m"                  # Beliebige abgegebene .m-Datei

- type: structural
  name: Loops
  file: "#file_1#"                 # Wird durch die oben gefundene Datei ersetzt
  tests:
    - name: for
      allowedOccuranceRange: [1, 0]
```

---

## meta.yaml

Die Metadaten der Aufgabe sind erforderlich, wenn sie auf die Plattform
hochgeladen wird, wo sie „Beispiel“ heißt. Der Tester selbst liest nur `properties.testDependencies`.

```yaml
slug: physics.python.hello_world  # Eindeutige, durch Punkte gegliederte Kennung
version: '1.0'
title: Hello World in Python
description: A simple Hello World program
language: en
license: CC BY-NC 4.0
keywords: [python, basics]         # Erscheinen in der Beispielbibliothek als Schlagwörter
category: Basics

authors:
  - name: Your Name
    email: your.email@example.org
    affiliation: Your Institute

properties:
  studentSubmissionFiles:
    - solution.py
  executionBackend:
    language: python
    version: "3.12"
```

`executionBackend` nimmt entweder eine `language` entgegen (python, octave, r,
julia, c, cpp, fortran, document, matlab), die mit den Test-Runnern der
Installation, also den Diensten, die die Tests ausführen, abgeglichen wird und sich durch eine optionale `version` ergänzen
lässt, oder einen `slug`, der genau einen bestimmten Runner festlegt. Die
zugehörigen `settings` werden zwar gespeichert, von den Testern aber nicht
angewendet; `timeout` und Compileroptionen setzt du in `test.yaml`.

---

## CLI-Referenz

### Einheitliche CLI

```bash
# Tests ausführen
computor-test <language> run -t <student_dir> -T <test.yaml> [-v 0-3]

# Lokal testen (test.yaml im übergeordneten Verzeichnis oder in <solution_dir>)
computor-test <language> local -d <solution_dir>

# Laufzeitumgebung prüfen
computor-test check --all
computor-test check python

# Verfügbare Tester auflisten
computor-test list
```

### Blocks-CLI (Erzeugung von test.yaml)

```bash
# Verfügbare Testtypen auflisten
blocks list -l python

# Neue test.yaml anlegen
blocks init -l python -n "My Tests"

# Testschnipsel erzeugen
blocks generate -l python -t variable -n result

# Vorlagen durchsehen
blocks templates list
blocks templates show "Variable Check" -l python

# Für die VS-Code-Erweiterung exportieren
blocks export ./generated
```

### Sandbox-CLI

```bash
# Backends prüfen
sandbox check -v

# Befehl in der Sandbox ausführen
sandbox run python3 -c "print('hello')"

# Konfiguration anzeigen
sandbox config --show

# Funktion der Sandbox testen
sandbox test
```

### Installation von Abhängigkeiten

```bash
# Alle Abhängigkeiten installieren
deps-installer install -f dependencies.yaml

# Dockerfile erzeugen
deps-installer dockerfile -f dependencies.yaml -o Dockerfile

# Abhängigkeitsdatei validieren
deps-installer validate -f dependencies.yaml
```

---

## Fehlerbehebung

### „Runtime not found“

```bash
# Prüfen, welche Laufzeitumgebungen verfügbar sind
computor-test check --all

# Für R muss jsonlite installiert sein:
Rscript -e "install.packages('jsonlite', repos='https://cloud.r-project.org/')"

# Für Julia muss JSON installiert sein:
julia -e 'import Pkg; Pkg.add("JSON")'
```

### Tests bestehen lokal, schlagen auf dem Server aber fehl

- Prüfe die Timeout-Werte, denn der Server kann langsamer sein
- Stelle sicher, dass test.yaml keine fest eingetragenen absoluten Pfade enthält
- Prüfe, ob die Pakete, die dein Code importiert, auf dem Test-Runner der Plattform installiert sind; die Plattform liest `dependencies.yaml` nicht
- Vergewissere dich, dass `executionBackend` in meta.yaml eine Sprache oder einen Runner nennt, die oder den die Installation bereitstellt

### „Execution failed“ ohne weitere Meldung

Jeder Prozess, der Code von Studierenden ausführt, läuft unter
Ressourcenbegrenzungen. `COMPUTOR_JOB_MAX_PROCESSES` (Standardwert 512) begrenzt
die Zahl aller Prozesse und Threads deines Benutzerkontos, sodass lokale Läufe auf einem
ausgelasteten Arbeitsrechner den Interpreter womöglich gar nicht erst starten
können. Setze für lokale Läufe `COMPUTOR_JOB_MAX_PROCESSES=0`.

### „Path validation failed“

Das Framework verhindert, dass Pfade aus dem erlaubten Verzeichnis herausführen (Directory Traversal). Achte deshalb auf Folgendes:
- Dateipfade enthalten kein `..`
- Alle Pfade sind relativ zum Wurzelverzeichnis der Tests
- Einstiegspunkte verweisen auf Dateien innerhalb des Verzeichnisses der Abgabe oder der Musterlösung

### Ausgabe wird nicht erfasst

Bei interpretierten Sprachen musst du sicherstellen, dass das Einstiegsskript tatsächlich eine Ausgabe erzeugt. Bei kompilierten Sprachen musst du darauf achten, dass `printf`/`cout` die Ausgabe auch wirklich schreibt (verwende `\n` oder `fflush(stdout)`).
