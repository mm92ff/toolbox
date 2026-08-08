# Umsetzungsplan: Individuelle Symbolgröße je geöffnetem Ordner

## 1. Ziel

In der Ordneransicht der Toolbox soll die Symbol- beziehungsweise Kachelgröße für jeden geöffneten Ordner individuell eingestellt werden können. Die Einstellung erfolgt direkt in der Breadcrumb-Leiste der Ordneransicht und wird dauerhaft gespeichert.

Beispiel:

- `/home/jemi/Bilder` verwendet 112 px.
- `/home/jemi/Downloads` verwendet 72 px.
- Ein Ordner ohne eigene Einstellung verwendet weiterhin die globale Symbolgröße.

Die Änderung darf weder die Einträge in `tools.json` verändern noch die globale Symbolgröße überschreiben. Die bestehende Drag-and-drop-, AppImage-, Desktop-Datei- und Mehrfensterfunktionalität muss erhalten bleiben.

## 2. Festgelegtes Bedienkonzept

### 2.1 Platzierung

Die Steuerung wird in die bereits vorhandene Breadcrumb-Leiste eingebaut, die nur während einer geöffneten Ordneransicht sichtbar ist:

1. Zurück-Schaltfläche
2. aktueller Ordnerpfad
3. Beschriftung `Symbolgröße`
4. horizontaler Schieberegler
5. aktuelle Größe, zum Beispiel `96 px`
6. Zurücksetzen-Schaltfläche

Außerhalb der Ordneransicht bleibt die gesamte Leiste verborgen. Die normale Toolbox-Ansicht erhält dadurch keine zusätzlichen Bedienelemente.

### 2.2 Verhalten

- Der Regler verwendet dieselben Grenzen wie die globale Symbolgröße: `MIN_ICON_SIZE` bis `MAX_ICON_SIZE`.
- Beim Verschieben wird die numerische Anzeige sofort aktualisiert.
- Die Kacheln werden während des Verschiebens flüssig aktualisiert, jedoch durch ein kurzes Debouncing vor unnötig vielen vollständigen Layoutdurchläufen geschützt.
- Die Zurücksetzen-Schaltfläche entfernt die ordnerspezifische Einstellung.
- Nach dem Zurücksetzen gilt sofort wieder die aktuelle globale Symbolgröße.
- Beim Wechsel in einen Unter- oder Elternordner lädt die Oberfläche dessen eigene Einstellung oder den globalen Fallback.
- Ein Ordner ohne Überschreibung folgt auch späteren Änderungen der globalen Symbolgröße.
- Eine explizite Ordnerüberschreibung bleibt von späteren globalen Änderungen unberührt.

### 2.3 Schriftgröße

Die bestehende Schriftgrößenlogik bleibt erhalten:

- Bei automatischer Schriftgröße wird die Beschriftung passend zur gewählten Ordner-Symbolgröße berechnet.
- Bei einer vom Benutzer fest eingestellten Schriftgröße bleibt diese unverändert.

Es wird keine zweite, ordnerspezifische Schriftgrößeneinstellung eingeführt.

## 3. Datenmodell und technische Entscheidungen

### 3.1 Effektive Symbolgröße

Die effektive Größe wird nach folgender Priorität bestimmt:

1. gültige ordnerspezifische Überschreibung
2. aktuelle globale Symbolgröße
3. `DEFAULT_ICON_SIZE`, falls auch die globale Einstellung ungültig oder nicht verfügbar ist

Beim Zurücksetzen wird der Ordner aus der Überschreibungsliste entfernt. Es wird ausdrücklich nicht der momentan globale Wert als neue Überschreibung gespeichert.

### 3.2 Ordneridentität

Ordner werden über einen normalisierten absoluten Pfad identifiziert:

- `expanduser()` auf Benutzerpfade anwenden
- in einen absoluten Pfad umwandeln
- `resolve(strict=False)` verwenden, damit vorübergehend nicht erreichbare Ordner die Einstellungen nicht beschädigen
- abschließende Pfadtrenner vereinheitlichen
- die Normalisierung zentral implementieren und nicht in mehreren UI-Klassen duplizieren

Damit verwenden alternative Schreibweisen desselben Pfades dieselbe Einstellung. Das Verhalten bei symbolischen Links wird durch die kanonische Auflösung eindeutig festgelegt und getestet.

### 3.3 Speicherformat

Die Daten werden als optionaler, rückwärtskompatibler Abschnitt in `ui_settings.json` gespeichert, beispielsweise:

```json
{
  "folder_browse": {
    "icon_size_overrides": {
      "/home/jemi/Bilder": {
        "size": 112,
        "last_used_utc": "2026-08-08T12:00:00Z"
      }
    }
  }
}
```

Regeln:

- `tools.json` bleibt unverändert.
- Fehlende `folder_browse`-Daten bedeuten eine leere Überschreibungsliste.
- Unbekannte zusätzliche Felder werden tolerant behandelt.
- Ungültige Pfade oder Werte werden beim Laden verworfen.
- Größen werden auf den zulässigen Bereich begrenzt beziehungsweise bei nicht numerischen Werten ignoriert.
- Die Anzahl gespeicherter Ordner wird begrenzt, empfohlen sind 250 Einträge.
- Bei Erreichen des Limits werden die am längsten nicht verwendeten Einträge zuerst entfernt.
- Die Zeitangabe dient ausschließlich dieser Bereinigung und beeinflusst die Darstellung nicht.

Die bestehende Schema-Version wird nur erhöht, falls der aktuelle Loader optionale Felder nicht bereits rückwärtskompatibel behandelt. Andernfalls bleibt die Erweiterung innerhalb des vorhandenen Schemas optional.

### 3.4 Zuständigkeit und Mehrfensterbetrieb

Eine zentrale, widget-unabhängige Komponente verwaltet die Zuordnung `normalisierter Pfad -> Symbolgröße`. Sie wird auf Anwendungsebene gehalten und über den bestehenden `WindowManager` beziehungsweise `SharedSettingsController` an Fenster angebunden.

Die Zuständigkeiten sind:

- Der Store normalisiert Pfade, validiert Werte, verwaltet den LRU-Zeitstempel und erzeugt unveränderliche Snapshots.
- Der zentrale Settings-Controller ist der einzige persistente Schreiber für `ui_settings.json`.
- Die Fenster halten weiterhin ihren eigenen Browse-Stack und ihre eigene Auswahl.
- Eine Änderung für Ordner A aktualisiert alle gerade sichtbaren Ansichten von Ordner A.
- Ansichten anderer Ordner werden nicht neu aufgebaut.
- Ein neu geöffnetes Fenster liest denselben kanonischen Einstellungsstand.
- Beim Schließen eines Fensters darf keine veraltete lokale Kopie die neueren Werte überschreiben.

Für Änderungen wird ein Signal mit normalisiertem Pfad und optionaler Größe verwendet. `None` bedeutet, dass die Überschreibung entfernt wurde.

## 4. Voraussichtlich betroffene Dateien

Die endgültigen Dateinamen werden während der Umsetzung gegen die vorhandene Architektur geprüft. Voraussichtlich betroffen sind:

- `app/features/entries/folder_browse.py`
  - effektive Ordner-Symbolgröße anwenden
  - Reglerereignisse verarbeiten
  - Navigation und Zurücksetzen synchronisieren
- `app/ui/tabs/toolbox_tab.py`
  - Regler, Wertanzeige und Zurücksetzen-Schaltfläche in der Breadcrumb-Leiste erzeugen
- `app/domain/tab_context.py`
  - Referenzen auf die neuen Steuerelemente und optional kurzlebigen Debounce-Zustand halten
- `app/features/settings/io_snapshot.py`
  - `folder_browse` in Export und Snapshot aufnehmen
- bestehende Settings-Import- und Shared-Settings-Module
  - validiertes Laden, zentrale Speicherung und Fenster-Broadcast ergänzen
- neue Datei, beispielsweise `app/state/folder_browse_appearance.py`
  - widget-unabhängiger Store für Normalisierung, Fallback, LRU und Signale
- `tests/test_folder_browse.py`
  - Browse-Verhalten und Größenanwendung erweitern
- neue oder bestehende Settings- und Mehrfenstertests
  - Persistenz, Import/Export und Synchronisation abdecken
- Benutzerdokumentation
  - Bedienung und Fallback-Verhalten erläutern

Neue Registry-Schlüssel für Widgets werden als Konstanten definiert, sofern das Projekt dafür bereits eine zentrale Konvention verwendet. String-Literale sollen nicht über mehrere Module verteilt werden.

## 5. Sprintplan

## Sprint 0 – Bestandsaufnahme und Sicherheitsnetz

### Ziel

Die aktuellen Schnittstellen und das bestehende Verhalten werden exakt festgehalten, bevor produktiver Code verändert wird.

### Aufgaben

1. Aufrufkette von `enter_folder_browse()` über `_refresh_browse_view()` bis `canvas.set_entries()` dokumentieren.
2. Prüfen, wie globale Symbol- und Schriftgröße aktuell an den Canvas übergeben werden.
3. Settings-Lade-, Import-, Export- und Speicherkette vollständig verfolgen.
4. Eigentümer und Lebenszyklus von `WindowManager` und `SharedSettingsController` verifizieren.
5. Bestehende Canvas-Methode bestimmen, mit der nur das Layout aktualisiert werden kann, ohne den Ordner neu einzulesen.
6. Ausgangstests für Ordnernavigation, globale Größe, Drag-and-drop und mehrere Fenster ausführen.
7. Fehlende Charakterisierungstests ergänzen, bevor Verhalten verändert wird.

### Tests

- Bestehende Testsuite ohne Regression ausführen.
- Test festhalten: Die bisherige Ordneransicht verwendet die globale Symbolgröße.
- Test festhalten: Öffnen und Schließen einer Ordneransicht verändert `tools.json` nicht.
- Test festhalten: Auswahl und Browse-Stack bleiben bei einem normalen Layout-Refresh erhalten.

### Abnahmekriterium

Die aktuelle Daten- und Ereigniskette ist durch Tests abgedeckt; es gibt keine funktionalen Änderungen.

## Sprint 1 – Ordnerdarstellungs-Store

### Ziel

Eine UI-unabhängige, vollständig testbare Quelle für ordnerspezifische Symbolgrößen schaffen.

### Aufgaben

1. `FolderBrowseAppearanceStore` oder eine gleichwertige Komponente einführen.
2. Zentrale Pfadnormalisierung implementieren.
3. Methoden bereitstellen:
   - `get_override(path)`
   - `effective_icon_size(path, global_size)`
   - `set_icon_size(path, size)`
   - `reset_icon_size(path)`
   - `load_snapshot(data)`
   - `build_snapshot()`
4. Größenprüfung gegen die vorhandenen Konstanten implementieren.
5. No-op-Erkennung einbauen, damit identische Werte keine unnötigen Signale oder Schreibvorgänge erzeugen.
6. Änderungsrevision oder gleichwertige Versionskennung ergänzen.
7. LRU-Metadaten und Obergrenze implementieren.
8. Defensive Kopien für ein- und ausgehende Snapshots verwenden.

### Unit-Tests

- Gleiche Pfade in unterschiedlichen Schreibweisen ergeben denselben Schlüssel.
- Relative und `~`-Pfade werden korrekt normalisiert.
- Symbolische Links folgen der festgelegten kanonischen Regel.
- Fehlende Überschreibung liefert die globale Größe.
- Gültige Überschreibung hat Vorrang vor der globalen Größe.
- Zurücksetzen stellt den globalen Fallback wieder her.
- Minimum und Maximum werden akzeptiert.
- Werte außerhalb des Bereichs werden konsistent begrenzt oder abgelehnt.
- Boolesche Werte werden nicht versehentlich als Integer akzeptiert.
- Nicht numerische, leere und beschädigte Daten werden ignoriert.
- Identisches erneutes Setzen erzeugt keine Revision und kein Signal.
- Snapshots können den internen Zustand nicht von außen verändern.
- Beim Überschreiten der Grenze wird der älteste Eintrag entfernt.

### Abnahmekriterium

Der Store funktioniert ohne Qt-Widgets und ist vollständig durch Unit-Tests abgesichert.

## Sprint 2 – Bedienoberfläche in der Breadcrumb-Leiste

### Ziel

Die Funktion wird dort angeboten, wo Benutzer sie erwarten: direkt im geöffneten Ordner.

### Aufgaben

1. Horizontalen `QSlider` in die Breadcrumb-Leiste einfügen.
2. Wertebereich aus `MIN_ICON_SIZE` und `MAX_ICON_SIZE` beziehen.
3. Numerische `px`-Anzeige hinzufügen.
4. Zurücksetzen-Schaltfläche mit verständlichem Icon, Tooltip und Accessible Name ergänzen.
5. Regler und Beschriftung mit Accessible Names versehen.
6. Feste beziehungsweise sinnvolle Mindestbreiten definieren, damit lange Pfade die Steuerung nicht verdrängen.
7. Pfadlabel bei Platzmangel elidieren oder über einen Tooltip vollständig zugänglich halten.
8. Reglerwert bei Navigation mit `QSignalBlocker` setzen, damit Laden nicht als Benutzeränderung interpretiert wird.
9. Zurücksetzen nur aktivieren, wenn für den aktuellen Ordner eine echte Überschreibung existiert.
10. Tastaturbedienung mit Pfeiltasten, PageUp/PageDown und Fokusreihenfolge sicherstellen.

### UI-Tests

- Steuerelemente sind außerhalb der Ordneransicht verborgen.
- Steuerelemente erscheinen beim Öffnen eines Ordners.
- Reglergrenzen entsprechen den Konstanten.
- Anzeige zeigt exakt den Reglerwert mit `px`.
- Laden eines Wertes löst keinen Schreibvorgang aus.
- Reset ist ohne Überschreibung deaktiviert und mit Überschreibung aktiviert.
- Zurücknavigation blendet die Steuerung korrekt aus beziehungsweise lädt den Elternordnerwert.
- Lange Pfade machen den Regler nicht unbenutzbar.
- Tastaturnavigation erreicht Regler und Reset-Schaltfläche.

### Abnahmekriterium

Die Bedienelemente sind sichtbar, verständlich und zugänglich, verändern jedoch noch nicht zwingend persistent den Canvas.

## Sprint 3 – Live-Anwendung auf den Ordner-Canvas

### Ziel

Änderungen werden sofort und ohne unnötiges erneutes Einlesen des Dateisystems dargestellt.

### Aufgaben

1. `_refresh_browse_view()` auf die effektive Ordnergröße umstellen.
2. Einen gezielten Layout-Update-Pfad für Regleränderungen einführen.
3. Vorhandene `_browse_display_entries` wiederverwenden, anstatt den Ordner für jeden Reglerwert neu einzulesen.
4. Kurzes Single-Shot-Debouncing für Canvas-Layoutupdates implementieren.
5. Label unmittelbar aktualisieren, auch wenn das Canvas-Update noch debounced ist.
6. Endwert bei `sliderReleased` beziehungsweise Tastaturende zuverlässig anwenden.
7. Auswahl, Scrollposition und Browse-Stack soweit von der bestehenden Canvas-API unterstützt erhalten.
8. Sicherstellen, dass keine transienten Kachelpositionen in `tools.json` landen.
9. Automatische und feste Schriftgrößenlogik unverändert weiterverwenden.
10. Fehler beim zwischenzeitlichen Entfernen oder Aushängen des Ordners kontrolliert behandeln.

### Funktions- und Integrationstests

- Ein Ordner ohne Überschreibung wird mit der globalen Größe gerendert.
- Ein Ordner mit Überschreibung wird mit exakt dieser Größe gerendert.
- Der tatsächlich an `set_entries()` beziehungsweise `apply_layout_settings()` übergebene Wert wird geprüft.
- Verschieben des Reglers aktualisiert vorhandene Einträge, ohne `_make_browse_entries()` erneut aufzurufen.
- Auswahl bleibt während einer Größenänderung erhalten.
- Der Browse-Stack bleibt unverändert.
- `tools.json` und die persistenten Toolbox-Einträge bleiben unverändert.
- Automatische Schriftgröße reagiert über die bestehende Berechnung.
- Feste Schriftgröße bleibt konstant.
- Rasche 100 Reglerereignisse führen nur zu einer begrenzten Anzahl teurer Canvas-Updates.
- Ein während des Debounce-Intervalls geschlossenes Fenster verursacht keinen Callback auf gelöschte Widgets.

### Abnahmekriterium

Die Größenänderung wirkt live, flüssig und ausschließlich auf die aktuell betroffene Ordneransicht.

## Sprint 4 – Persistenz, Import und Export

### Ziel

Ordnerspezifische Größen bleiben nach Neustart erhalten und verhalten sich in Profilen korrekt.

### Aufgaben

1. Optionalen `folder_browse`-Abschnitt in den UI-Settings-Snapshot aufnehmen.
2. Loader um tolerante Validierung ergänzen.
3. Änderungen über den zentralen Settings-Controller speichern.
4. Schreibvorgänge bündeln, damit Reglerbewegungen nicht für jeden Zwischenwert auf die Platte schreiben.
5. Beim regulären Herunterfahren den letzten ausstehenden Wert sicher flushen.
6. Profil-Export um die neuen Daten ergänzen.
7. Profil-Import atomar validieren und anschließend anwenden.
8. Bei beschädigten Einträgen nur die betroffenen Einträge verwerfen, nicht die gesamten UI-Einstellungen.
9. Schreibfehler protokollieren und über das bestehende Error-Handling anzeigen, ohne die laufende Ansicht abstürzen zu lassen.

### Persistenztests

- Speichern und erneutes Laden ergibt dieselben Überschreibungen.
- Eine alte `ui_settings.json` ohne `folder_browse` lädt mit leerer Liste.
- Unbekannte Felder verhindern das Laden nicht.
- Beschädigte Einzelwerte werden verworfen.
- Grenzwerte überleben den Roundtrip.
- Reset entfernt den Eintrag aus dem nächsten Snapshot.
- Profil-Export enthält die Einstellungen.
- Profil-Import stellt sie wieder her.
- Import ohne Abschnitt löscht nicht unbeabsichtigt Daten, sofern die bestehende Importsemantik Zusammenführen vorsieht; bei Ersetzen folgt er konsistent der vorhandenen Semantik.
- Simulierter Schreibfehler wird behandelt und lässt den In-Memory-Zustand nutzbar.
- Viele schnelle Änderungen werden als gebündelter Schreibvorgang gespeichert.
- Der letzte Wert wird beim Beenden nicht verloren.

### Abnahmekriterium

Die Einstellung überlebt App-Neustarts und Profiltransfers, ohne alte Konfigurationen zu beschädigen.

## Sprint 5 – Mehrfenster-Synchronisation und Lebenszyklus

### Ziel

Die Funktion wird mit der bestehenden Mehrfensterarchitektur konsistent und konfliktfrei betrieben.

### Aufgaben

1. Store auf Anwendungsebene besitzen und an Fenster anbinden.
2. Pfadbezogenes Änderungssignal verteilen.
3. In jedem Fenster nur Tabs aktualisieren, deren aktueller Browse-Pfad betroffen ist.
4. Regler externer Ansichten per `QSignalBlocker` synchronisieren.
5. Sicherstellen, dass nur der zentrale Controller persistiert.
6. Fenster beim Schließen sauber vom Signal trennen.
7. Spät eintreffende Debounce-Callbacks abbrechen.
8. Zusammenwirken mit bestehenden Entwurfs-, Revisions- und Konfliktregeln der Shared Settings prüfen.

### Mehrfenstertests

- Fenster A und B zeigen denselben Ordner: Änderung in A aktualisiert B.
- Fenster A und B zeigen verschiedene Ordner: B bleibt unverändert.
- Zwei Tabs desselben Fensters mit demselben Ordner werden synchronisiert.
- Ein Tab in normaler Toolbox-Ansicht wird nicht aktualisiert.
- Ein nachträglich geöffnetes Fenster erhält den aktuellen Wert.
- Reset wird in allen Ansichten desselben Ordners sichtbar.
- Externe Synchronisation erzeugt keine Signalschleife.
- Gleichzeitige Änderungen enden deterministisch nach der bestehenden Last-Writer-/Revisionsregel.
- Schließen eines Fensters überschreibt keinen neueren Wert aus einem anderen Fenster.
- Beenden aller Fenster speichert genau den letzten kanonischen Stand.

### Abnahmekriterium

Alle Fenster zeigen für denselben Ordner konsistente Größen; andere Ordner und lokale Browse-Navigation bleiben isoliert.

## Sprint 6 – Regression, Performance, Dokumentation und AppImage

### Ziel

Die Änderung wird für den produktiven Linux-Mint-22.3-AppImage-Betrieb abgesichert.

### Aufgaben

1. Vollständige Test-Suite ausführen.
2. Statische Prüfungen, Formatierung und `git diff --check` ausführen.
3. Dokumentation um Bedienung, Fallback und Zurücksetzen ergänzen.
4. AppImage mit dem vorhandenen Build-Prozess neu erzeugen.
5. Inhalt des AppImage prüfen, damit alle neuen Python-Dateien enthalten sind.
6. AppImage auf Linux Mint 22.3 unter X11 testen.
7. Falls das Projekt Wayland unterstützt, zusätzlichen Wayland-Smoke-Test ausführen.
8. Test mit Ordnern auf lokaler Platte, externem Datenträger und nicht mehr vorhandenem Pfad durchführen.

### End-to-End-Tests

- AppImage starten und einen Ordner in die Toolbox aufnehmen.
- Ordner öffnen, Größe verändern, Ordner schließen und erneut öffnen.
- AppImage beenden und neu starten; Einstellung bleibt erhalten.
- Unterordner öffnen und eine abweichende Größe setzen.
- Zur Elternansicht wechseln; deren Größe wird wiederhergestellt.
- Überschreibung zurücksetzen; aktuelle globale Größe wird verwendet.
- Globale Größe ändern; nur Ordner ohne Überschreibung folgen ihr.
- Zweite Toolbox-Instanz öffnen und Synchronisation desselben Ordners prüfen.
- Datei- und Ordner-Drop in der Toolbox weiterhin prüfen.
- AppImage-, `.desktop`- und URL-Verknüpfungen weiterhin starten.
- AppImage- und Desktop-Datei-Icons weiterhin korrekt anzeigen.
- Tray-Icon, Tab-Erstellung, Einstellungen und normales Beenden prüfen.
- Ordner mit mindestens 500 Einträgen testen; Regler bleibt responsiv.
- Entfernten oder nicht erreichbaren Ordner testen; verständliche Fehlerbehandlung ohne Absturz.

### Abnahmekriterium

Die Funktion ist im gebauten AppImage auf Linux Mint 22.3 nutzbar und alle relevanten Regressionstests bestehen.

## 6. Testmatrix

| Bereich | Fall | Erwartung |
|---|---|---|
| Fallback | Kein Ordnerwert | Globale Größe wird verwendet |
| Überschreibung | Eigener Ordnerwert | Ordnerwert wird verwendet |
| Reset | Überschreibung entfernen | Sofortiger globaler Fallback |
| Navigation | Eltern- und Unterordner | Jeweils eigener Wert wird geladen |
| Schrift | Automatisch | Bestehende automatische Berechnung folgt der Kachelgröße |
| Schrift | Fest eingestellt | Schriftgröße bleibt unverändert |
| Persistenz | Neustart | Ordnerwert bleibt erhalten |
| Kompatibilität | Alte Settings-Datei | Start ohne Fehler und globaler Fallback |
| Fehlerdaten | Ungültige Größe | Eintrag wird sicher ignoriert oder begrenzt |
| Mehrfenster | Gleicher Ordner | Ansichten synchronisieren sich |
| Mehrfenster | Verschiedene Ordner | Keine unbeabsichtigte Änderung |
| Performance | Schnelles Verschieben | Debounced, keine Dateisystem-Neuladung je Event |
| Datenintegrität | Größenänderung | Keine Änderung an `tools.json` |
| Lebenszyklus | Schließen während Debounce | Kein Crash, letzter bestätigter Wert bleibt konsistent |
| AppImage | Linux Mint 22.3 | UI, Speicherung und Neustart funktionieren |

## 7. Fehlerbehandlung

- Nicht lesbarer Ordner: vorhandene Browse-Fehlermeldung verwenden; Regler darf keinen Folgefehler erzeugen.
- Ungültiger gespeicherter Pfad: Eintrag überspringen und protokollieren.
- Ungültige Größe: Eintrag überspringen oder nach klar definierter Regel begrenzen.
- Nicht schreibbare Settings-Datei: In-Memory-Funktion beibehalten, Fehler über bestehende UI melden und protokollieren.
- Entferntes Fenster oder Tab: Debounce-Timer stoppen und Signalverbindungen lösen.
- Import mit teilweise defekten Daten: gültige Einträge übernehmen, defekte Einträge melden beziehungsweise protokollieren.
- Überschrittenes LRU-Limit: deterministisch den ältesten Eintrag entfernen.

## 8. Risiken und Gegenmaßnahmen

### Zu viele Canvas-Neuberechnungen

Gegenmaßnahme: Anzeige sofort aktualisieren, Canvas-Updates kurz debouncen und den Ordnerinhalt nicht erneut einlesen.

### Versehentliche Änderung persistenter Toolbox-Einträge

Gegenmaßnahme: ausschließlich `_browse_display_entries` und Canvas-Layout verwenden; Tests überwachen Schreibzugriffe auf `tools.json`.

### Veraltete Fenster überschreiben neue Einstellungen

Gegenmaßnahme: ein zentraler kanonischer Store und genau ein Settings-Schreiber; keine vollständigen lokalen Snapshots beim Fensterschließen zurückschreiben.

### Unbegrenztes Wachstum der Pfadliste

Gegenmaßnahme: LRU-Obergrenze und Reset-Funktion.

### Signalschleifen zwischen Fenstern

Gegenmaßnahme: No-op-Erkennung, Revisionsprüfung und `QSignalBlocker` beim programmatischen Setzen.

### Langsame oder entfernte Datenträger

Gegenmaßnahme: Regleränderungen führen keine erneute Verzeichnisabfrage aus; fehlende Pfade werden kontrolliert behandelt.

## 9. Definition of Done

Die Umsetzung gilt als abgeschlossen, wenn alle folgenden Punkte erfüllt sind:

- Die Breadcrumb-Leiste enthält Regler, Wertanzeige und Reset-Funktion.
- Jeder Ordner kann eine eigene Symbolgröße im gültigen Bereich besitzen.
- Ordner ohne Überschreibung verwenden dynamisch die globale Größe.
- Einstellungen bleiben nach Neustart und Profilimport erhalten.
- `tools.json` wird durch die Funktion nicht verändert.
- Regleränderungen lesen den Ordner nicht bei jedem Ereignis neu ein.
- Auswahl und Browse-Navigation bleiben stabil.
- Mehrere Fenster und Tabs werden pfadbezogen korrekt synchronisiert.
- Alte und teilweise beschädigte Settings-Dateien werden sicher geladen.
- Die Zahl gespeicherter Pfade ist begrenzt.
- Unit-, Integrations-, Mehrfenster-, Persistenz- und AppImage-Smoke-Tests bestehen.
- Dokumentation ist aktualisiert.
- `git diff --check` und die vollständige Testsuite laufen ohne neue Fehler durch.

## 10. Empfohlene Umsetzungsreihenfolge

Die Sprints werden in der angegebenen Reihenfolge umgesetzt. Nach jedem Sprint werden dessen Tests ausgeführt und Fehler behoben, bevor der nächste Sprint beginnt. Besonders die zentrale Store- und Mehrfensterentscheidung darf nicht erst nach der UI-Implementierung nachgerüstet werden, da sie die Persistenz- und Signalschnittstellen festlegt.

Dieser Plan beschreibt ausschließlich die geplante Änderung. Er implementiert die Funktion noch nicht.
