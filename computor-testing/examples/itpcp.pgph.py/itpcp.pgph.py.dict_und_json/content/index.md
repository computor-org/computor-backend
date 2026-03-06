# Dictionaries und JSON files

## Einleitung

Wenn z.B. bei Computersimulationen Daten erzeugt werden, welche anschließend auszuwerten
sind, ist es empfehlenswert, diese zwischenzuspeichern und die Auswertung vom Generieren
der Daten zu trennen. Eine Möglichkeit, das in einer übersichtlichen Art und Weise zu
tun, ist Python dictionaries in JSON files zu speichern, welche als Textdateien für
Menschen lesbar und syntaktisch gleich wie dictionaries aufgebaut sind.

Dabei muss man beachten, dass nicht alle Datentypen als Text darstellbar sind.
NumPy-Arrays zum Beispiel müssen in Listen umgewandelt werden.

## Aufgabe

In dieser Übungseinheit schreiben Sie ein Skript, welches beispielhaft ein JSON file mit
Konfigurationsparametern einliest, und mit von Ihnen berechneten Werten befüllt.

Das Skript `generate_data.py` soll die Datei `data_file.json` mit dem [json] module als
dictionary `data` einlesen. Jeder Eintrag im dict `'sim_config'` besteht aus einem Satz
von Parametern für eine bestimmte Berechnung. In diesem Beispiel handelt es sich um die
Mittelwerte `mu`, Standardabweichungen `sig` und die Größen `size` von Arrays von
normalverteilten Zufallszahlen.

1. Generieren Sie die Arrays und fügen Sie diese als dictionary `results` auf gleicher
   Ebene wie `'sim_config'` und unter dem jeweiligen Namen der Simulation ('sim1',
   'sim2', ...) hinzu.

1. Fügen Sie zusätzlich das dictionary `'metadata'` mit dem aktuellen Datum und der
   Uhrzeit (Keys `'date'` bzw. `'time'`) hinzu ([datetime]). Nutzen Sie dazu das
   `"%Y-%m-%d"` bzw. das `"%H:%M"` Format. Das erhaltene dict sollte also folgenden
   Aufbau haben:

   ```python
   {'sim_config': {...},
   'results': {'sim1': [...], 'sim2': [], ...},
   'metadata': {'date' : '...', 'time': '...'}
   }
   ```

1. Speichern Sie nun das nested dictionary in einer Datei `results.json`. Das Schreiben
   funktioniert ähnlich wie das Einlesen, wobei Sie beim Aufruf von `open()` das
   Argument `"w"` anstelle von `"r"` verwenden müssen (write statt read). Danach
   verwenden Sie `json.dump(data, fp, indent=4)`.

[datetime]: https://docs.python.org/3/library/datetime.html
[json]: https://docs.python.org/3/library/json.html#basic-usage
