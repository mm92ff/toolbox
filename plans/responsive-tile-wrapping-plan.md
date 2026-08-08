# Umsetzungsplan: Responsives Umbrechen der Toolbox-Kacheln

## 1. Ziel

Kacheln sollen sich an die tatsächlich verfügbare Breite des Toolbox-Fensters anpassen. Wird ein Fenster schmaler, werden Kacheln automatisch in zusätzliche Zeilen umgebrochen, bis bei sehr kleiner Breite nur noch eine Kachel pro Zeile angezeigt wird. Beim Vergrößern fließen sie wieder in weniger Zeilen zurück.

Die Funktion darf keine gespeicherten Positionen allein durch eine Fenstergrößenänderung verändern. Verschieden breite Fenster müssen daher unterschiedliche visuelle Anordnungen desselben gemeinsamen Toolbox-Zustands darstellen können.

## 2. Festgelegtes Produktverhalten

### 2.1 Geöffnete Ordner

Für die schreibgeschützte Ordneransicht wird responsives Umbrechen standardmäßig aktiviert:

- Die Ordneransicht verhält sich wie ein Dateimanager.
- Die Kacheln werden in stabiler Reihenfolge von links nach rechts und anschließend von oben nach unten angezeigt.
- Ordnerspezifische Symbolgrößen beeinflussen automatisch die Anzahl möglicher Spalten.
- Die temporären Browse-Einträge werden nicht in `tools.json` gespeichert.
- Es gibt keine horizontale Scrollleiste für Kacheln, solange mindestens eine Kachel in die Ansicht passt.

### 2.2 Normale Toolbox-Tabs

Für frei positionierbare Toolbox-Tabs wird eine globale optionale Einstellung ergänzt:

> Kacheln automatisch an Fensterbreite anpassen

Regeln:

- Standardwert für bestehende und neue Profile: aktiviert.
- Deaktiviert: Das bisherige manuelle Layout bleibt unverändert.
- Aktiviert: Kacheln und Abschnittstrenner werden responsiv dargestellt.
- Eine reine Fenstergrößenänderung verändert keine kanonischen `x`-/`y`-Werte.
- Die Einstellung wird mit den übrigen UI-Einstellungen gespeichert, synchronisiert sowie im Profil exportiert und importiert.
- Die Breite und der daraus entstehende visuelle Umbruch bleiben fensterlokal.

### 2.3 Manuelles Verschieben im responsiven Modus

Für die erste sichere Umsetzung wird manuelles Verschieben im responsiven Modus deaktiviert. Beim Versuch zeigt die Statusleiste einen verständlichen Hinweis:

> Manuelles Verschieben ist im responsiven Layout deaktiviert. Deaktivieren Sie „An Fensterbreite anpassen“, um Kacheln frei zu positionieren.

Begründung:

- Visuelle Koordinaten stimmen im responsiven Modus bewusst nicht mit den gespeicherten Koordinaten überein.
- Ein Drag-and-drop-Reordering zwischen Abschnittsgruppen wäre eine eigenständige Funktion mit zusätzlicher Persistenz- und Undo-Semantik.
- Hinzufügen, Entfernen, Starten, Auswählen, Datei-Drops und Kontextmenüs bleiben verfügbar.

Ein späteres sortierbares responsives Raster kann auf der neuen Layoutarchitektur aufbauen, gehört aber nicht zum Umfang dieses Plans.

## 3. Abgrenzung

### Im Umfang

- responsiver Umbruch von Kacheln
- Rückfluss beim Vergrößern
- Minimum von einer Kachel pro Zeile
- Abschnittstrenner über die verfügbare Breite
- stabile Gruppenbildung vor, zwischen und nach Abschnitten
- globale Option für normale Toolbox-Tabs
- standardmäßig responsives Verhalten in Ordneransichten
- fensterlokale visuelle Positionen
- Resize-Throttling
- Persistenz der Option, nicht der Resize-Ergebnisse
- Unterstützung der individuellen Ordner-Symbolgröße
- Linux-Mint-22.3-AppImage- und X11-Prüfung

### Nicht im Umfang

- Drag-Reordering im responsiven Modus
- individuelle Responsive-Einstellung je Tab
- individuelle Mindestspaltenzahl je Tab oder Ordner
- Masonry-/Pinterest-Layout
- automatische Veränderung der Kachel- oder Schriftgröße aufgrund der Fensterbreite
- Persistieren responsiv berechneter Koordinaten

## 4. Technische Leitentscheidungen

### 4.1 Kanonische und visuelle Positionen trennen

`ToolboxEntry.x` und `ToolboxEntry.y` bleiben die kanonischen, persistenten Positionen. Das responsive Layout erzeugt stattdessen eine fensterlokale Zuordnung:

```text
entry_id -> visuelles QRect
```

Diese Zuordnung wird vom jeweiligen `CanvasSurface` gehalten und niemals an das Repository oder `tools.json` zurückgeschrieben.

Folgen:

- Fenster A kann bei 1200 px vier Kacheln pro Zeile zeigen.
- Fenster B kann bei 500 px nur eine oder zwei Kacheln pro Zeile zeigen.
- Beide Fenster teilen weiterhin dieselben Einträge und manuellen Positionen.
- Beim Ausschalten des responsiven Modus erscheinen sofort wieder die kanonischen Positionen.

### 4.2 Reiner Layoutalgorithmus

Ein widget-unabhängiger Algorithmus erhält:

- geordnete sichtbare Einträge
- verfügbare Viewport-Breite
- Kachelbreite und Kachelhöhe
- horizontale und vertikale Rasterabstände
- Canvas-Padding
- Abschnittshöhe
- Abstand oberhalb und unterhalb von Abschnitten

Er liefert:

- visuelle Rechtecke je Eintrag
- resultierende Inhaltshöhe
- Anzahl verwendeter Spalten
- optional Gruppen-/Zeilenmetadaten für Tests und spätere Drag-Reordering-Unterstützung

Der Algorithmus hat keine Qt-Widget-Abhängigkeit. `QRect` kann durch eine kleine unveränderliche Dataklasse oder einfache Tupel ersetzt werden, damit Unit-Tests ohne sichtbare GUI möglich bleiben.

### 4.3 Spaltenberechnung

Die verfügbare Breite wird aus dem echten Viewport bestimmt:

```text
verfügbar = max(1, viewport_breite - 2 * canvas_padding)
zellbreite = kachelbreite + horizontaler_abstand
spalten = max(1, floor((verfügbar + horizontaler_abstand) / zellbreite))
```

Damit zählt nach der letzten Kachel kein unnötiger äußerer Rasterabstand. Die Spaltenzahl darf niemals null werden.

### 4.4 Stabile Reihenfolge

Für normale Toolbox-Tabs wird die bestehende logische Reihenfolge aus den kanonischen Positionen abgeleitet:

1. Abschnittssegment
2. `y`
3. `x`
4. stabiler ursprünglicher Listenindex
5. Titel nur als letzter deterministischer Fallback

Für Ordneransichten wird die bereits erzeugte Browse-Reihenfolge verwendet: Ordner zuerst, danach Dateien, jeweils alphabetisch.

Versteckte oder gefilterte Einträge belegen keinen visuellen Rasterplatz.

### 4.5 Abschnittstrenner

Abschnitte werden als Blockgrenzen behandelt:

- Werkzeuge vor dem ersten Abschnitt bilden Gruppe 0.
- Jeder Abschnitt beendet die vorherige Gruppe.
- Nach dem Abschnitt beginnt eine neue responsive Gruppe.
- Der Abschnitt verwendet die aktuelle Inhaltsbreite.
- Schutzabstände oberhalb und unterhalb werden in der visuellen Höhe berücksichtigt.
- Ein Umbruch darf keine Kachel in den Schutzbereich eines Abschnitts legen.

Die kanonischen Abschnittskoordinaten bleiben unverändert.

### 4.6 Resize-Steuerung

Resize-Ereignisse können sehr häufig auftreten. Deshalb wird die teure Neuberechnung gedrosselt:

- Viewport-Breite sofort erfassen.
- Responsive Neuberechnung höchstens etwa alle 50–80 ms durchführen.
- Den letzten Wert nach Ende einer Resize-Serie sicher anwenden.
- Fenstergröße nicht über globale Settings-Broadcasts verteilen.
- Keine Speicherung bei Resize auslösen.

### 4.7 Mindestbreiten

Die feste Canvas-Mindestbreite von derzeit 900 px und die Layout-Untergrenze von derzeit 480 px müssen getrennt bewertet und angepasst werden:

- Im responsiven Modus muss die Layoutberechnung bis auf eine Kachelbreite plus Padding reagieren.
- Im manuellen Modus darf das bisherige Scrollverhalten erhalten bleiben.
- Die minimale Fensterbreite wird aus Tab-Leiste, Breadcrumb-Leiste und einer vollständigen Kachel abgeleitet.
- Bei extrem schmaler Breite darf die Kachel nicht kleiner skaliert werden; sie bleibt vollständig und die Fenster-Mindestbreite verhindert unbrauchbares Abschneiden.

## 5. Voraussichtlich betroffene Dateien

- `app/canvas/layout_engine.py`
  - Spaltenberechnung und responsive Metriken
- neue Datei, beispielsweise `app/canvas/responsive_layout.py`
  - reiner responsiver Layoutalgorithmus
- `app/canvas/surface_state.py`
  - Layoutmodus und fensterlokale visuelle Rechtecke
- `app/canvas/surface_geometry.py`
  - responsive Rechtecke anwenden, ohne Modelle zu mutieren
- `app/canvas/surface_render.py`
  - Layoutmodus an `set_entries()` und `apply_layout_settings()` übergeben
- `app/canvas/surface_drag.py`
  - manuelles Verschieben im responsiven Modus kontrolliert blockieren
- `app/canvas/toolbox_canvas.py`
  - Resize-Throttle und responsive API
- `app/features/entries/controller_canvas.py`
  - normalen und Browse-Modus korrekt konfigurieren
- `app/features/entries/folder_browse.py`
  - Responsive-Modus für Ordner erzwingen
- `app/features/settings/schema.py`
  - neue persistente boolesche Einstellung
- `app/features/settings/state.py`
  - angewendeten Wert bereitstellen
- `app/features/settings/io_snapshot.py` und Import-/Loader-Module
  - JSON- und Profil-Roundtrip
- `app/ui/tabs/settings_tab_sections.py`
  - Checkbox und Hilfetext
- `README.md`, `CHANGELOG.md`, `app/ui/tabs/help_tab.py`
  - Bedienung und Einschränkungen dokumentieren
- Canvas-, Settings-, Ordner-, Mehrfenster- und AppImage-Tests

Die endgültige Dateiliste wird während Sprint 0 gegen die aktuelle Modularchitektur verifiziert.

## 6. Sprintplan

## Sprint 0 – Bestandsaufnahme und Charakterisierung

### Ziel

Das aktuelle Verhalten bei Resize, Auto-Compact, Abschnitten, versteckten Einträgen und mehreren Fenstern wird durch Tests festgehalten.

### Aufgaben

1. Aufrufkette von `ToolboxCanvas.resizeEvent()` bis `CanvasSurface.set_viewport_width()` dokumentieren.
2. Prüfen, welche Methoden bei Resize momentan Modelle oder Widget-Geometrien verändern.
3. Feste Mindestbreiten von Canvas, Layoutengine und Hauptfenster erfassen.
4. Aktuelles horizontales Scrollverhalten charakterisieren.
5. Sortier- und Segmentlogik für Werkzeuge und Abschnitte dokumentieren.
6. Drag-, Multi-Select-, Drop- und Persistenzpfade prüfen.
7. Vorhandene Layouttests als Ausgangsbasis ausführen.

### Tests

- Resize verändert derzeit keine Modellkoordinaten.
- Abschnitte passen ihre Breite an den Viewport an.
- Manuelles Layout bleibt bei unveränderter Einstellung stabil.
- Browse-Einträge bleiben transient.
- Zwei Fenster verwenden dasselbe Modell, aber eigene Viewport-Breiten.

### Abnahmekriterium

Alle aktuellen Invarianten sind dokumentiert oder durch Charakterisierungstests abgedeckt.

## Sprint 1 – Reiner responsiver Layoutalgorithmus

### Ziel

Ein deterministischer und unabhängig testbarer Algorithmus berechnet visuelle Positionen.

### Aufgaben

1. Eingabe- und Ergebnisdatentypen definieren.
2. Spaltenberechnung implementieren.
3. Row-Major-Platzierung für Werkzeuge implementieren.
4. Minimum von einer Spalte garantieren.
5. Versteckte Einträge aus der Platzbelegung entfernen.
6. Abschnittsgruppen und Schutzabstände berücksichtigen.
7. Resultierende Inhaltshöhe berechnen.
8. Stabile Reihenfolge und deterministische Fallbacks implementieren.
9. Keine Modellobjekte verändern.

### Unit-Tests

- Breite für vier Kacheln ergibt vier Spalten.
- Knapp unter dem Breakpoint ergibt drei Spalten.
- Weitere Verkleinerung ergibt zwei und schließlich eine Spalte.
- Vergrößerung ergibt wieder mehr Spalten.
- Exakter Breakpoint hat kein Off-by-one-Verhalten.
- Horizontale Abstände werden nur zwischen Kacheln berücksichtigt.
- Kleine und große Symbolgrößen verändern die Breakpoints korrekt.
- Automatische und feste Schriftgröße beeinflussen die gemessene Kachelgröße korrekt.
- Versteckte Einträge hinterlassen keine Lücken.
- Leere Liste ergibt eine gültige Mindesthöhe.
- 1, 2, 100 und 1000 Einträge werden korrekt platziert.
- Eingabeobjekte und kanonische Koordinaten bleiben unverändert.
- Derselbe Input liefert immer dasselbe Ergebnis.

### Abnahmekriterium

Der Algorithmus besteht alle Unit-Tests ohne Qt-Fenster und ohne Persistenzzugriff.

## Sprint 2 – Fensterlokale visuelle Geometrie

### Ziel

Canvas-Widgets verwenden responsive Rechtecke, ohne `ToolboxEntry.x/y` zu überschreiben.

### Aufgaben

1. Layoutmodus `manual`/`responsive` im Canvas-State ergänzen.
2. Visuelle Rechteckzuordnung je `entry_id` halten.
3. `_apply_geometry()` in manuelle und responsive Pfade aufteilen.
4. Widget-Geometrien aus der visuellen Zuordnung setzen.
5. Canvas-Gesamtgröße aus visuellen Rechtecken berechnen.
6. Abschnittsbreiten responsiv setzen.
7. Hit-Testing, Auswahlrahmen und Kontextmenüs gegen echte Widget-Geometrien prüfen.
8. Beim Wechsel zurück zu manuell die kanonischen Positionen sofort wiederherstellen.
9. Responsive Rechtecke beim Entfernen oder Ersetzen von Einträgen bereinigen.

### Integrationstests

- Responsive Darstellung verändert `entry.x/y` nicht.
- Ausschalten stellt manuelle Positionen exakt wieder her.
- Auswahl bleibt nach Reflow erhalten.
- Mehrfachauswahl bleibt visuell korrekt.
- Kontextmenü öffnet für die richtige Kachel.
- Abschnittsbreite folgt dem Viewport.
- Canvas-Höhe wächst mit zusätzlichen Zeilen.
- Horizontaler Scrollbereich verschwindet im responsiven Kachelbereich.
- Vertikales Scrollen bleibt möglich.

### Abnahmekriterium

Responsive und manuelle Darstellung können verlustfrei gewechselt werden.

## Sprint 3 – Resize-Throttling und Mindestbreiten

### Ziel

Das Layout reagiert flüssig auf Fenstergrößenänderungen bis hinunter zu einer Kachel pro Zeile.

### Aufgaben

1. Resize-Throttle mit Single-Shot- oder wiederkehrendem Coalescing-Timer ergänzen.
2. Letzte Viewport-Breite nach einer Resize-Serie garantieren.
3. Unnötige Neuberechnung vermeiden, wenn sich die Spaltenzahl nicht ändert.
4. Feste Canvas-Mindestbreite im responsiven Modus entfernen oder dynamisch berechnen.
5. Layoutengine-Untergrenze von 480 px für responsive Berechnungen entkoppeln.
6. Fenster-Mindestbreite auf eine vollständig nutzbare Kachel plus UI-Chrome begrenzen.
7. Sichtbaren Anker oder Scrollposition beim Reflow möglichst stabil halten.
8. Timer beim Schließen sicher stoppen.

### Tests

- Resize von vier auf drei, zwei und eine Spalte.
- Resize zurück auf vier Spalten.
- 100 schnelle Resize-Ereignisse erzeugen nur wenige Layoutläufe.
- Der letzte Resize-Wert wird angewendet.
- Gleiche Spaltenzahl erzeugt keinen unnötigen vollständigen Reflow.
- Schließen während eines ausstehenden Timers verursacht keinen Callback auf zerstörte Widgets.
- Eine vollständige Kachel bleibt bei minimaler Fensterbreite benutzbar.
- Scroll-Anker springt nicht unkontrolliert an den Anfang.

### Abnahmekriterium

Kontinuierliches Resize bleibt responsiv und erzeugt keine Persistenz- oder Lebenszyklusfehler.

## Sprint 4 – Integration der Ordneransicht

### Ziel

Geöffnete Ordner verwenden automatisch das responsive Raster.

### Aufgaben

1. `_refresh_browse_view()` mit responsivem Layoutmodus aufrufen.
2. Ordnerspezifische Symbolgröße in die Breakpoint-Berechnung einbeziehen.
3. Wechsel zwischen Eltern- und Unterordner korrekt reflowen.
4. Änderung des Ordner-Symbolgrößenreglers sofort responsiv anwenden.
5. Browse-Auswahl und vertikale Scrollposition soweit möglich erhalten.
6. Rückkehr zur Toolbox stellt deren eigenen Layoutmodus wieder her.
7. Sicherstellen, dass kein Resize `tools.json` oder Browse-Einträge persistiert.

### Tests

- Ordneransicht ist unabhängig von der globalen Toolbox-Option responsiv.
- Kleine Ordner-Symbolgröße ermöglicht mehr Spalten.
- Große Ordner-Symbolgröße führt früher zum Umbruch.
- Regleränderung berechnet Spalten neu.
- Eltern- und Unterordner verwenden korrekte Reihenfolge und Größe.
- Bei einer Kachel pro Zeile bleiben alle Einträge erreichbar.
- Rückkehr zur Toolbox verändert keine gespeicherten Positionen.
- Ordner mit 500 Einträgen bleibt beim Resize bedienbar.
- `tools.json` bleibt bytegenau unverändert.

### Abnahmekriterium

Die Ordneransicht verhält sich wie ein responsiver Dateimanager und bleibt vollständig transient.

## Sprint 5 – Option für normale Toolbox-Tabs

### Ziel

Benutzer können responsives Verhalten für normale Toolbox-Tabs bewusst aktivieren.

### Aufgaben

1. Boolesche Einstellung mit rückwärtskompatiblem Standard `False` ergänzen.
2. Checkbox unter `Settings > Design & Layout` einbauen.
3. Erklärung ergänzen, dass manuelles Verschieben im responsiven Modus deaktiviert ist.
4. Preview beziehungsweise Apply-Verhalten an bestehende Settings-Semantik anbinden.
5. Aktivieren reflowt alle normalen Toolbox-Canvases fensterlokal.
6. Deaktivieren stellt die manuellen Positionen wieder her.
7. JSON-Snapshot, QSettings-Fallback und Profil-Import/-Export ergänzen.
8. Shared-Settings-Broadcast nutzen, ohne Fensterbreiten zu synchronisieren.
9. Alte Profile ohne Schlüssel unverändert manuell laden.

### Settings- und Persistenztests

- Standardwert ist aktiviert.
- Aktivieren und `Save & Apply` schaltet normale Canvases um.
- Deaktivieren stellt kanonische Positionen wieder her.
- Neustart stellt die Option wieder her.
- Altes `ui_settings.json` ohne Schlüssel bleibt kompatibel.
- Ungültiger Wert fällt sicher auf `False` zurück.
- Profil-Export enthält den Wert.
- Profil-Import stellt den Wert wieder her.
- Eine Änderung in Fenster A aktualisiert den Modus in Fenster B.
- Fensterbreite und Umbruchzahl bleiben dennoch fensterlokal.

### Abnahmekriterium

Die Option ist verständlich, persistent und beeinträchtigt bestehende manuelle Profile standardmäßig nicht.

## Sprint 6 – Interaktionen, Abschnitte und Mehrfensterbetrieb

### Ziel

Alle bestehenden Interaktionen funktionieren sicher oder werden bewusst eingeschränkt.

### Aufgaben

1. Manuelle Entry-Moves im responsiven Modus blockieren.
2. Statushinweis bei einem Verschiebeversuch anzeigen.
3. Datei-Drops auf Kacheln unverändert zulassen.
4. Drops auf leere Fläche weiterhin als Hinzufügen behandeln.
5. Abschnittsgruppen bei Hinzufügen und Entfernen neu berechnen.
6. Suchfilter und versteckte Einträge ohne Lücken reflowen.
7. Auswahl, Starten, Entfernen, Kontextmenüs und Tooltips prüfen.
8. Zwei Fenster mit unterschiedlichen Breiten gleichzeitig prüfen.
9. Sicherstellen, dass responsive Reflows keinen Repository-Commit und keinen Undo-Schritt erzeugen.

### Tests

- Drag-Versuch verändert im responsiven Modus keine Position.
- Verständlicher Statushinweis erscheint.
- Drag funktioniert nach Deaktivierung wieder wie bisher.
- Kachel-Drop und Empty-Canvas-Drop funktionieren.
- Hinzufügen und Entfernen reflowt korrekt.
- Suchfilter schließt Lücken.
- Abschnitte bleiben in stabiler Reihenfolge.
- Fenster A mit vier Spalten und Fenster B mit einer Spalte beeinflussen sich nicht.
- Kein `state_changed`-Signal bei reinem Resize.
- Kein neuer Undo-Schritt bei reinem Resize.
- Kein Schreibzugriff auf `tools.json` bei reinem Resize.

### Abnahmekriterium

Bestehende Bedienfunktionen bleiben erhalten; die einzige bewusste Einschränkung ist dokumentiertes manuelles Verschieben im responsiven Modus.

## Sprint 7 – Regression, Performance, Dokumentation und AppImage

### Ziel

Die Funktion wird für Linux Mint 22.3 und das AppImage produktionsreif abgesichert.

### Aufgaben

1. Vollständige Testsuite ausführen.
2. Ruff und `git diff --check` ausführen.
3. README, Changelog und Hilfe aktualisieren.
4. AppImage neu bauen.
5. AppImage-Inhalt und Prüfsumme validieren.
6. Offscreen-Smoke-Test um Responsive-Widget- und Layoutnachweise erweitern.
7. Echten X11-Resize-Test um Spaltenumbrüche ergänzen.
8. Sichtprüfung mit kleiner, mittlerer und großer Symbolgröße durchführen.
9. Manuelle Prüfung unter Linux Mint 22.3 Cinnamon dokumentieren.

### Performance- und End-to-End-Tests

- 1000 Kacheln und 100 Resize-Ereignisse innerhalb eines festgelegten Zeitbudgets.
- Keine lineare Widget-Neuerstellung bei jeder Breitenänderung.
- Speicherverbrauch wächst nicht nach wiederholtem Verkleinern und Vergrößern.
- AppImage startet und meldet vorhandene Responsive-Steuerung.
- AppImage-Ordneransicht bricht von mehreren Spalten bis auf eine um.
- AppImage stellt beim Vergrößern mehrere Spalten wieder her.
- Echte X11-Fenstergrößenänderung aktualisiert die visuelle Spaltenzahl.
- Zwei AppImage-Fenster mit verschiedenen Breiten bleiben unabhängig.
- Tray, neue Fenster, neue Tabs, AppImage-Icons, `.desktop`-Starts und Drops funktionieren weiterhin.
- AppImage-Prüfsumme stimmt.

### Abnahmekriterium

Alle automatisierten Prüfungen und der vollständige AppImage-Release-Workflow bestehen.

## 7. Testmatrix

| Bereich | Fall | Erwartung |
|---|---|---|
| Breite | breite Ansicht | mehrere Kacheln pro Zeile |
| Breite | schmalere Ansicht | automatischer Umbruch |
| Breite | minimale Ansicht | genau eine Kachel pro Zeile |
| Breite | erneutes Vergrößern | Kacheln fließen zurück |
| Symbolgröße | klein | mehr mögliche Spalten |
| Symbolgröße | groß | weniger mögliche Spalten |
| Schriftgröße | automatisch | bestehende Kachelmetrik wird verwendet |
| Schriftgröße | fest | Breakpoint berücksichtigt feste Textmetrik |
| Abschnitte | mehrere Gruppen | kein Überlappen der Schutzbereiche |
| Filter | versteckte Einträge | keine leeren Rasterplätze |
| Ordneransicht | globale Option aus | Ordner bleibt responsiv |
| Normale Toolbox | Option aus | manuelles Layout bleibt unverändert |
| Normale Toolbox | Option an | responsive Darstellung |
| Moduswechsel | responsive zu manuell | gespeicherte Positionen kehren zurück |
| Mehrfenster | verschiedene Breiten | unabhängige visuelle Layouts |
| Persistenz | Resize | keine Änderung an `tools.json` |
| Undo | Resize | kein neuer Undo-Schritt |
| Lebenszyklus | Schließen während Timer | kein Absturz |
| AppImage | Offscreen und X11 | Umbruch und Rückfluss funktionieren |

## 8. Fehlerbehandlung

- Viewport-Breite kleiner oder gleich null: vorübergehend letzte gültige Breite verwenden oder auf eine Spalte fallen.
- Ungültige gespeicherte Option: sicheren Standard `False` verwenden.
- Eintrag ohne Widget: Geometrie überspringen und nächsten Refresh zulassen.
- Eintrag ohne visuelles Rechteck: auf kanonische Geometrie zurückfallen und diagnostisch protokollieren.
- Entferntes Tab oder Fenster: Resize-Timer stoppen und Callback nicht mehr ausführen.
- Sehr große Kachel: eine Spalte verwenden und Fenster-Mindestbreite respektieren.
- Abschnitt ohne nachfolgende Werkzeuge: Abschnitt weiterhin korrekt darstellen.

## 9. Risiken und Gegenmaßnahmen

### Versehentliche Persistenz visueller Positionen

Gegenmaßnahme: strikte Trennung von kanonischen Modellkoordinaten und fensterlokalen visuellen Rechtecken; Bytevergleich von `tools.json` in Tests.

### Zwei Fenster überschreiben sich aufgrund verschiedener Breiten

Gegenmaßnahme: Responsive-Reflow ist reine View-Operation und verwendet weder Repository-Commit noch Shared-State-Broadcast.

### Ruckeln während Resize

Gegenmaßnahme: Spaltenzahl vor vollständigem Reflow vergleichen, Ereignisse drosseln und bestehende Widgets nur verschieben statt neu erstellen.

### Abschnittsüberlappungen

Gegenmaßnahme: Abschnitte als explizite Gruppenblöcke im Algorithmus behandeln und Schutzabstände in die vertikale Platzierung einrechnen.

### Verwirrung beim manuellen Verschieben

Gegenmaßnahme: Drag im responsiven Modus blockieren, deutlichen Hilfetext und Statushinweis anzeigen und manuelle Positionen vollständig erhalten.

### Unbeabsichtigte Verhaltensänderung für bestehende Nutzer

Gegenmaßnahme: Die Option kann jederzeit deaktiviert werden; eine einmalige Migration stellt bestehende Profile auf den neuen aktivierten Standard um, danach bleiben bewusste Benutzerentscheidungen erhalten.

## 10. Definition of Done

Die Umsetzung ist abgeschlossen, wenn alle folgenden Punkte erfüllt sind:

- Ordneransichten brechen Kacheln automatisch bis auf eine Spalte um.
- Beim Vergrößern fließen Kacheln wieder zurück.
- Normale Toolbox-Tabs besitzen eine standardmäßig aktivierte Responsive-Option.
- Responsive Reflows verändern keine `ToolboxEntry.x/y`-Werte.
- Reflows schreiben nicht in `tools.json` und erzeugen keinen Undo-Schritt.
- Zwei Fenster können dasselbe Tab mit unterschiedlicher Spaltenzahl anzeigen.
- Abschnitte und Schutzabstände bleiben korrekt.
- Versteckte Einträge erzeugen keine Lücken.
- Individuelle Ordner-Symbolgrößen verändern Breakpoints korrekt.
- Manuelles Verschieben ist im responsiven Modus kontrolliert deaktiviert.
- Resize-Ereignisse sind gedrosselt und der letzte Wert wird angewendet.
- Einstellungen, Neustart sowie Profilimport und -export funktionieren.
- Alte Profile behalten das bisherige manuelle Toolbox-Layout.
- Unit-, Integrations-, Performance-, Mehrfenster- und AppImage-Tests bestehen.
- README, Changelog und Hilfe sind aktualisiert.
- AppImage-Build, Prüfsumme, Offscreen-Smoke-Test und echter X11-Test bestehen.

## 11. Empfohlene Umsetzungsreihenfolge

Die Sprints werden in der angegebenen Reihenfolge umgesetzt. Der reine Algorithmus und die Trennung visueller von kanonischen Positionen müssen vor UI und Persistenz abgeschlossen sein. Erst danach darf die Funktion für normale Toolbox-Tabs aktivierbar werden. Dadurch bleibt das Risiko gering, dass ein Resize versehentlich Benutzerdaten oder den gemeinsamen Mehrfensterzustand verändert.

## 12. Umsetzungsstand vom 8. August 2026

Die Sprints 0 bis 7 sind umgesetzt. Der reine Algorithmus liegt in
`app/canvas/responsive_layout.py`; Canvas-Geometrie, Ordneransicht, globale Option,
Persistenz, Drag-Schutz, Dokumentation und AppImage-Smoke-Nachweise sind integriert.

Verifikation:

- 378 automatisierte Tests bestanden
- Ruff und `git diff --check` ohne Befund
- AppDir- und AppImage-Smoke-Tests bestanden
- AppImage-Inhalts-, Relokations- und Prüfsummenprüfung bestanden
- erzeugtes Artefakt: `dist-appimage/Toolbox-0.42-beta-x86_64.AppImage`
- SHA-256: `88fddaa2d60da690a93efad8596703650efa23bfe6fb04df00152c455fe1661c`

Der echte X11-Test wurde in der verfügbaren X11-Sitzung ausgeführt. Er bestätigte
Fenstererzeugung, WM-Metadaten, Taskleisten-Icon, zweite Instanz sowie am realen
Fenster den Übergang „mehrere Spalten → eine Spalte → mehrere Spalten“. Dabei blieben
die kanonischen Positionen unverändert. Der AppImage-Smoke-Test bestätigte denselben
Umbruch zusätzlich im eingefrorenen Programm. Die abschließende subjektive
Sichtprüfung unter Linux Mint Cinnamon bleibt ein manueller Release-Schritt.

Ein abschließender Soll-Ist-Audit ergänzte außerdem das Überspringen vollständiger
Reflows bei unveränderter Spaltenzahl, die Erhaltung des vertikalen Scroll-Ankers,
eine kachelabhängige Mindestfensterbreite, das explizite Stoppen ausstehender
Resize-Timer und die sichere Normalisierung beschädigter lokaler Einstellungswerte.

Auf Benutzerwunsch ist das responsive Layout nun standardmäßig aktiviert. Eine
einmalige Migration aktiviert es auch für Profile, die den früheren
Entwicklungsstandard bereits als `false` gespeichert hatten. Nach dieser Migration
werden bewusste spätere Deaktivierungen dauerhaft respektiert.
