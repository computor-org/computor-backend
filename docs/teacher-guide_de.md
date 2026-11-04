# Leitfaden für Lehrende: Kurs-Dashboard

Dieser Leitfaden richtet sich an Lehrende und Tutor:innen, die in der
Computor-Webanwendung die Arbeit ihrer Studierenden verfolgen. Er erklärt, was
jede Seite zeigt, woher die Zahlen stammen und was sie nicht aussagen. Technische
Vorkenntnisse brauchst du dafür nicht.

Alles auf diesen Seiten wird aus dem berechnet, was die Plattform ohnehin
aufzeichnet, wenn Studierende an Aufgaben arbeiten:

- **Testläufe**: Bei jedem Start der automatischen Tests durch Studierende werden
  der Zeitpunkt, die Punktzahl (0–100 %) und der Testbericht gespeichert.
- **Abgaben**: Wenn Studierende eine Aufgabe offiziell abgeben, wird der Zeitpunkt
  gespeichert.
- **Bewertungen und Feedback**: Wenn Tutor:innen oder Lehrende eine Abgabe
  bewerten, werden die Bewertung, der Status, das schriftliche Feedback, die
  bewertende Person und der Zeitpunkt gespeichert.

Tastenanschläge, Bildschirmzeit oder die im Editor verbrachte Zeit zeichnet die
Plattform nicht auf. Was nach „aufgewendeter Zeit“ aussieht, ist eine Schätzung
und als solche gekennzeichnet.

## Wo du die Seiten findest

Öffne einen Kurs und verwende die Seitenleiste:

| Eintrag in der Seitenleiste | Wer ihn sieht | Wozu er dient |
|---|---|---|
| Lehrende → Bewertung | Lehrende und Personen mit weitergehenden Rechten | Kursstatistik, die Liste der Studierenden mit ihren Auffälligkeiten und die Detailseite jeder einzelnen Person |
| Lehrende → Typische Fehler | Lehrende und Personen mit weitergehenden Rechten | Die fehlgeschlagenen Tests, die viele Studierende gemeinsam haben |
| Tutor | Tutor:innen und Personen mit weitergehenden Rechten | Wie viel Arbeit auf eine Prüfung wartet |
| Tutor → Abgaben | Tutor:innen und Personen mit weitergehenden Rechten | Die Warteschlange der zu prüfenden Abgaben |
| Tutor → Bewertung | Tutor:innen und Personen mit weitergehenden Rechten | Die Bewertung der Studierenden, eine Person nach der anderen |

Tutor:innen sehen nur die Tutor-Seiten. Die Seiten unter „Lehrende“, die Daten
über den gesamten Kurs zeigen, sind Lehrenden, Maintainer:innen und
Eigentümer:innen des Kurses sowie Administrator:innen vorbehalten.

## Kursstatistik (Lehrende → Bewertung)

Der obere Teil der Seite fasst den Kurs zusammen:

- **Studierende**, **Durchschnittlicher Fortschritt** und **Abgeschlossen**: Als
  Fortschritt gilt der Anteil der abgebbaren Aufgaben, die eine Person offiziell
  abgegeben hat.
- **Gefährdet**: Studierende mit weniger als 25 % Fortschritt.
- **Inaktiv**: Studierende ohne Abgabe in den letzten 14 Tagen.
- **Verteilung des Fortschritts** und das Diagramm zu den Inhaltstypen zeigen, wie
  sich der Kurs auf die Fortschrittsstufen und die Inhaltstypen verteilt.

### Auffälligkeiten

Unter den Diagrammen führt der Bereich **Auffälligkeiten** einfache, fest
vorgegebene Regeln auf, die dich auf Studierende hinweisen, die du dir vielleicht
ansehen möchtest. Eine Auffälligkeit ist ein Anlass zum Hinsehen, kein Urteil:
Jede nennt die Regel, die gegriffen hat, und die Zahlen, die dazu geführt haben.
Öffne auf der Seite **So werden Auffälligkeiten berechnet**, um jede Regel mit
ihrem Schwellenwert zu sehen.

| Auffälligkeit | Wann sie erscheint |
|---|---|
| Viele fehlgeschlagene Versuche | 10 oder mehr Testläufe bei einer Aufgabe, ohne die volle Punktzahl zu erreichen. Solange die volle Punktzahl noch fehlt, erscheint dies als Warnung, sobald sie erreicht wurde, als Information. |
| Sprung auf volle Punktzahl | Ein Testlauf erreichte 100 % direkt nach einem Lauf mit höchstens 30 % bei derselben Aufgabe. Oft hat die Person einfach den Fehler gefunden; für sich genommen ist das kein Beleg für Abschreiben. |
| Inaktiv | Kein Testlauf und keine Abgabe in den letzten 14 Tagen oder noch überhaupt keine. |
| Geringer Fortschritt | Weniger als 25 % der abgebbaren Aufgaben abgegeben. |
| Abgabe auf den letzten Drücker | Die letzte Abgabe erfolgte weniger als 2 Stunden vor der Frist. |
| Abgabe nach der Frist | Mindestens eine Abgabe nach der Frist. |

Fristen je Aufgabe speichert die Plattform nicht. Die beiden Fristregeln verwenden
die **Abgabefrist**, die du im Bereich „Auffälligkeiten“ (oder auf der Seite einer
Person) einträgst. Sie wird in deinem Browser für diesen Kurs gespeichert und gilt
für alle Aufgaben, weshalb du dort die Frist einträgst, die dich gerade
interessiert. Ohne Abgabefrist entfallen die beiden Fristregeln.

Die Tabelle der Studierenden hat eine Spalte **Auffälligkeiten**. Fährst du mit der
Maus über eine Auffälligkeit, liest du ihre Begründung, und mit einem Häkchen bei
**Nur auffällige** listest du nur die betroffenen Studierenden auf. Ein Klick auf
eine Person öffnet ihre Detailseite.

## Einzelne Studierende (Lehrende → Bewertung → eine Person)

Die Detailseite zeigt von oben nach unten:

1. **Durchschnittliche Bewertung, Gesamtfortschritt und Abgabezahlen.**
2. **Abgabeverlauf**: die Abgaben der Person, über die Zeit aufsummiert, mit dem
   Startdatum und der Abgabefrist, die du oben auf der Seite festlegst.
3. **Auffälligkeiten**: dieselben Regeln wie oben für diese Person, jede mit ihrer
   Begründung.
4. **Bearbeitungsverlauf** (in der englischen Oberfläche: *Attempt timeline*): eine
   Zeile je Aufgabe, an der die Person gearbeitet hat.
   - *Versuche im Zeitverlauf*: Punkte sind Testläufe, nach Punktzahl eingefärbt
     (grün: volle Punktzahl, bernsteinfarben: mindestens 50 %, rot: unter 50 %);
     Balken sind Abgaben; eine gestrichelte Linie markiert die Abgabefrist. Alle
     Zeilen teilen sich eine Zeitachse, sodass du erkennst, wann an welcher Aufgabe
     gearbeitet wurde.
   - *Läufe* und *Abgaben*: jeweils deren Anzahl.
   - *Erste / letzte Aktivität*: das erste und das letzte Ereignis, sei es ein
     Testlauf oder eine Abgabe.
   - *Volle Punktzahl erreicht*: wann ein Testlauf erstmals 100 % erreichte, oder
     „noch nicht“.
   - *Beste / letzte*: die beste und die neueste Testpunktzahl.
   - *Tage*: an wie vielen verschiedenen Tagen die Person daran gearbeitet hat.
   - *Mediane Pause*: die typische Zeit zwischen zwei aufeinanderfolgenden
     Testläufen.
   - *Gesch. aktive Zeit*: eine **Schätzung**. Sie summiert die Pausen zwischen
     aufeinanderfolgenden Testläufen, die höchstens 30 Minuten auseinanderliegen.
     Arbeit ohne Testlauf bleibt für die Plattform unsichtbar, weshalb du diesen
     Wert als Untergrenze lesen solltest und niemals als gemessene Arbeitszeit.
   - *Letzte Abgabe* (nur mit Abgabefrist): wie lange vor oder nach der Frist die
     letzte Abgabe erfolgte.
5. **Verlauf der Läufe, Abgaben und Rückmeldungen**: alles in zeitlicher
   Reihenfolge, das Neueste zuerst. Ein *Abgabe-Lauf* ist ein Testlauf zu einer
   offiziellen Abgabe; eine Zeile *Bewertung* zeigt die Bewertung, ihren Status, das
   schriftliche Feedback und die Person, die es gegeben hat. Mit den beiden Filtern
   zeigst du nur eine Aufgabe oder nur eine Art von Einträgen.
6. **Fortschritt im Kursinhalt**: jede Aufgabe mit ihrem Status und der Anzahl der Versuche.

Mit **Drucken** erhältst du die Seite auf Papier oder als PDF, etwa für ein
Beratungsgespräch mit der Person.

## Typische Fehler (Lehrende → Typische Fehler)

Diese Seite sammelt die fehlgeschlagenen Tests aus den Testläufen der Studierenden
und fasst jene zusammen, die aus demselben Grund fehlschlagen. So erkennst du
Probleme, die viele Studierende gemeinsam haben, etwa eine missverstandene
Aufgabenstellung oder einen fehlenden Hinweis.

Zu jeder Gruppe siehst du die Aufgabe, den fehlgeschlagenen Test und die
Fehlermeldung sowie, wie viele **Studierende** betroffen sind und wie viele
fehlgeschlagene **Läufe** es gab. Gruppen mit den meisten betroffenen Studierenden
stehen oben. Ein Klick auf eine Zeile zeigt bis zu drei Beispiele von verschiedenen
Studierenden mit der ursprünglichen Meldung und einem Link zur Seite der jeweiligen
Person.

So werden Meldungen gruppiert: Erhalten bleibt nur die erste Zeile, die den Fehler
benennt, und Einzelheiten, die sich von Person zu Person unterscheiden, werden durch
Platzhalter ersetzt, nämlich Zahlen durch `<n>`, Werte in Anführungszeichen durch
`<str>`, Dateipfade durch `<path>` und Speicheradressen durch `<addr>`. Einfache
Namen in Anführungszeichen, etwa `'np'` in „name 'np' is not defined“, bleiben
erhalten, weil sie meist das eigentliche Problem benennen. Aus „assert 3 == 4“ und
„assert 7 == 2“ wird also die eine Gruppe `assert <n> == <n>`.

Gut zu wissen:

- Es zählen nur Testläufe von Studierenden; die eigenen Testläufe von Lehrenden und
  Tutor:innen bleiben außen vor.
- Die Seite wertet die neuesten fehlgeschlagenen Testläufe aus, standardmäßig 300. Gibt
  es mehr, weist ein Hinweis darauf hin; wähle dann eine größere Anzahl oder eine
  einzelne Aufgabe, um weiter zurückzuschauen.
- *Läufe ohne Bericht* zählt die Läufe, zu denen kein ausführlicher Testbericht
  gespeichert wurde. Sie können zu keiner Gruppe beitragen.

## Tutor-Seiten

### Tutor (Übersicht)

Zeigt, wie viele Studierende du hast und wie viele davon unbewertete Abgaben haben,
außerdem die Zahl der unbewerteten Abgaben und der ungelesenen Nachrichten, und
verlinkt auf die beiden unten beschriebenen Seiten.

### Abgaben

Die Warteschlange der zu prüfenden Abgaben umfasst alle Studierenden oder Teams mit
Abgaben, standardmäßig nur jene mit unbewerteter Arbeit, wobei die am längsten
Wartenden zuerst stehen. Du kannst nach Aufgabe filtern oder das Häkchen bei **Nur
unbewertete** entfernen, um alles zu sehen. Ein Klick auf eine Zeile öffnet die
Bewertungsseite dieser Person bei der richtigen Aufgabe.

### Bewertung

Wähle eine Person aus der Liste aus (mit einem Häkchen bei **Nur mit unbewerteten
Abgaben** grenzt du sie ein). Die Seite der Person führt links ihre Aufgaben auf;
wählst du eine davon aus, siehst du:

- das letzte Testergebnis und die Zahl der Abgaben und Testläufe,
- ein Formular unter **Letzte Abgabe bewerten**: eine Bewertung in Prozent, einen
  Status (*Korrigiert*, *Korrektur nötig*, *Verbesserung möglich* oder *Nicht
  geprüft*) und schriftliches Feedback für die Person,
- die früheren Bewertungen und das Feedback zu dieser Aufgabe,
- die Details des letzten Testlaufs.

Das Feld für die Bewertung ist mit der letzten automatischen Testpunktzahl
vorausgefüllt; ändere sie bei Bedarf. Bezieht sich eine Bewertung auf eine ältere
Abgabe als die letzte, weist die Seite darauf hin.

## Was das Dashboard nicht leistet

- Es beurteilt Studierende nicht automatisch. Auffälligkeiten sind fest vorgegebene,
  sichtbare Regeln mit genannten Schwellenwerten; eine verborgene Punktzahl gibt es
  nicht.
- Es misst nicht die Arbeitszeit. Die einzige Zeitangabe ist die als solche
  gekennzeichnete Schätzung im Bearbeitungsverlauf.
- Fristen für Aufgaben kennt es nur, wenn du eine Abgabefrist einträgst.
