# Plan: Umstrukturierung der Settings in Sub-Tabs

## Zielsetzung
Die derzeitige Einstellungsseite (`Settings`) besteht aus einer langen, scrollbaren Liste von Einstellungsgruppen (Appearance, FFmpeg, Grid, Colors, Tabs, Maintenance, Backup). Um die Übersichtlichkeit zu verbessern, sollen diese Gruppen in logische **Sub-Tabs** (Unter-Reiter) innerhalb des Haupt-Settings-Tabs aufgeteilt werden.

## 1. Analyse der aktuellen Struktur
Aktuell werden alle Gruppen in `app/ui/tabs/settings_tab.py` in ein vertikales `QVBoxLayout` innerhalb einer `QScrollArea` geladen.

Vorhandene Gruppen:
- `build_appearance_group`
- `build_ffmpeg_group`
- `build_grid_group`
- `build_section_separator_group`
- `build_section_colors_group`
- `build_tabs_group`
- `build_maintenance_group`
- `build_backup_group`

## 2. Neues Layout-Konzept
Ein neues `QTabWidget` wird innerhalb des Settings-Tabs erstellt. Die Gruppen werden wie folgt auf die Sub-Tabs verteilt:

### Tab 1: "Design & Layout"
Fokus auf optische Anpassungen.
- Appearance (Hell/Dunkel, Grunddesign)
- Grid (Rastereinstellungen)
- Section Separator (Trennlinien)
- Section Colors (Farben)
- Tabs (Tab-Verhalten/Design)

### Tab 2: "System"
Fokus auf externe Werkzeuge und Kern-Pfade.
- FFmpeg (Pfade und Einstellungen für Video-Konvertierung etc.)

### Tab 3: "Wartung & Backup"
Fokus auf Datenverwaltung.
- Maintenance (Cache leeren, Log-Dateien, etc.)
- Backup (Exporte/Importe der Konfiguration)

> **Hinweis:** Der `Apply`-Button (`build_apply_row`) sollte idealerweise *außerhalb* des `QTabWidget` (z.B. am unteren Rand verankert) platziert werden, damit Änderungen aus allen Sub-Tabs zentral und tab-übergreifend gespeichert werden können.

---

## 3. Sprints & Umsetzungsschritte

### Sprint 1: UI-Umbau (Refactoring `settings_tab.py`)
- **Aufgabe 1:** `create_settings_tab()` in `app/ui/tabs/settings_tab.py` anpassen.
- **Aufgabe 2:** Ein neues `QTabWidget` (die Sub-Tabs) erzeugen.
- **Aufgabe 3:** Drei neue Container-Widgets (für die 3 neuen Reiter) samt eigenen `QScrollArea`s erstellen.
- **Aufgabe 4:** Die bestehenden `build_*_group()`-Funktionen aufrufen und in die jeweils passenden Layouts der Sub-Tabs einhängen.
- **Aufgabe 5:** Den Apply-Button unterhalb des neuen `QTabWidget` platzieren.
- **Test (manuell):** App starten, überprüfen, ob die drei Reiter erscheinen und alle Gruppen korrekt zugewiesen sind.

### Sprint 2: Überprüfung der Logik & Controller
- **Aufgabe 1:** Da die Widget-Registrierung (das `widgets` dict, das von UI an Controller übergeben wird) auf den Namen (`objectName`) der Felder basiert, sollte die reine UI-Umstrukturierung die Logik nicht brechen. Dennoch muss dies verifiziert werden.
- **Aufgabe 2:** Klick auf `Apply` testen – werden Werte aus *nicht-aktiven* Sub-Tabs ebenfalls fehlerfrei ausgelesen und gespeichert?
- **Test:** Einstellungen in Tab 1 und Tab 3 ändern -> Apply klicken -> App neustarten -> Prüfen, ob beide übernommen wurden.

### Sprint 3: Feinschliff (Styling & UX)
- **Aufgabe 1:** Padding und Margins des inneren `QTabWidget` anpassen, damit es sich optisch gut vom Haupt-Tab abhebt (keine hässlichen doppelten Ränder).
- **Aufgabe 2:** Wenn nötig, `documentMode` für die Sub-Tabs aktivieren, um sie flacher wirken zu lassen.

---

## 4. Testplan (Zusammenfassung)
1. **Sichtbarkeit:** Werden alle alten Einstellungs-Blöcke in den neuen Kategorien korrekt und vollständig gerendert?
2. **Scrolling:** Wenn ein Sub-Tab zu viele Elemente hat (wie "Design & Layout"), greift dann die ScrollArea nur für diesen Tab?
3. **Data-Binding:** Funktioniert das Speichern (`Apply`) tab-übergreifend?
4. **Fehlertoleranz:** Gibt es Abstürze bei Klicks zwischen den Tabs oder beim Verwerfen/Schließen des Programms?
