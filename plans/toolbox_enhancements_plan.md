# Plan: Erweiterungen der Toolbox (Features 1, 3, 4, 5)

Dieses Dokument beschreibt die Umsetzung von vier essenziellen neuen Features für die Toolbox, unterteilt in strukturierte Sprints mit entsprechenden Tests. Die globale Suchfunktion (Feature 2) wurde auf Wunsch vorerst ausgenommen.

---

## Sprint 1: Kachel-Eigenschaften bearbeiten (Tile Properties)

**Ziel:** Nutzer sollen Kacheln (Namen und Icons) manuell anpassen können.
* **Architektur:**
  * Erweiterung des Datenmodells (`app/domain/models.py` -> `ToolEntry`), um `custom_title` und `custom_icon_path` zu speichern.
  * Neues Dialog-Fenster (`app/ui/dialogs/tile_properties_dialog.py`), das Eingabefelder für Name und Icon-Pfad bietet.
  * Hinzufügen des Menüpunkts "Eigenschaften bearbeiten" zum Kachel-Rechtsklick-Menü in `app/features/entries/controller_context_menu.py`.
  * Anpassung der UI (`canvas_widgets.py`), sodass bevorzugt die benutzerdefinierten Werte geladen werden.
* **Tests:**
  * *Unit Tests:* Testen der `ToolEntry`-Serialisierung (stellen sicher, dass die neuen Felder ins JSON gespeichert und korrekt wieder geladen werden).
  * *UI Tests:* Überprüfen, ob das Setzen eines `custom_title` das Label auf dem Canvas sofort aktualisiert.

---

## Sprint 2: System Tray & Hintergrund-Modus

**Ziel:** Die App soll im Hintergrund (System Tray) weiterlaufen und nicht die Taskleiste blockieren.
* **Architektur:**
  * Implementierung eines `QSystemTrayIcon` (in `app/main_window.py` oder einem eigenen Tray-Service).
  * Hinzufügen eines Kontextmenüs im Tray (Öffnen, Beenden, Einstellungen).
  * Ändern des Schließen-Verhaltens (`closeEvent` überschreiben): Statt die App zu beenden, wird das Fenster versteckt, sofern die Option "In den Tray minimieren" in den Settings aktiv ist.
  * *Hinweis zum Globalen Hotkey:* Ein systemweiter Hotkey erfordert oft externe Bibliotheken (wie `pynput` oder `keyboard`). In diesem Sprint wird die Tray-Integration als Basis gebaut und evaluiert, welche Cross-Platform-Bibliothek für den Hotkey integriert wird.
* **Tests:**
  * *Manuelle Tests:* Fenster schließen -> Prüfen, ob Tray-Icon existiert. Klick auf Tray-Icon -> Fenster erscheint wieder im Vordergrund. Beenden über Tray-Icon -> App schließt sauber.
  * *Unit Tests:* Mocking des `closeEvent`, um sicherzustellen, dass die App-Instanz am Leben bleibt.

---

## Sprint 3: Plattform-Kompatibilität für FFmpeg-Download

**Ziel:** Der neue FFmpeg-Download-Button in den Settings soll auch auf Windows korrekt funktionieren.
* **Architektur:**
  * Anpassung der Funktion `download_and_extract_ffmpeg` in `app/services/ffmpeg_downloader.py`.
  * Einbau einer Systemabfrage via `platform.system()`.
  * Wenn Linux: Beibehalten der aktuellen Logik (Download von johnvansickle, Entpacken von `.tar.xz`).
  * Wenn Windows: Download einer statischen Windows-Binary (z. B. von *gyan.dev* als `.zip`), Entpacken via `zipfile`-Modul und Ablegen als `ffmpeg.exe` im `.bin/`-Ordner.
* **Tests:**
  * *Unit Tests:* `unittest.mock.patch` auf `platform.system` anwenden, um die korrekte URL-Auswahl und das korrekte Entpack-Verhalten für Windows und Linux zu verifizieren, ohne tatsächliche Downloads durchzuführen.

---

## Sprint 4: Automatische Sortierung (Auto-Sort)

**Ziel:** Kacheln innerhalb einer Sektion oder im gesamten Tab per Rechtsklick alphabetisch sortieren.
* **Architektur:**
  * Erweiterung des Kontextmenüs auf dem Canvas (Hintergrund) und auf Sektions-Überschriften: Eintrag "Alphabetisch sortieren (A-Z)".
  * Logik in `app/features/entries/controller.py` oder `tab_manager.py`: Eine Funktion, die alle Einträge (`ToolEntry`) der selektierten Gruppe nimmt, nach `title` (oder `custom_title`) sortiert und deren Array-Index neu anordnet.
  * Anschließend Auslösen eines Reflows (Neu-Anordnung der Kacheln im Raster).
* **Tests:**
  * *Unit Tests:* Erstellen eines virtuellen Tabs mit unsortierten Dummies ("Zeta", "Alpha", "Gamma"). Aufruf der Sortier-Funktion und Assert auf die neue Reihenfolge ["Alpha", "Gamma", "Zeta"].
  * *Integration Tests:* Sicherstellen, dass auch verschobene Kacheln nach dem Sortieren korrekt ins JSON exportiert werden.
