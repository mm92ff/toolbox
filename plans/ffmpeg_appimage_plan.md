# Plan: FFmpeg in das AppImage bündeln

## Zielsetzung
Das Programm soll auf jedem Linux-System sofort einsatzbereit sein ("Plug & Play"), ohne dass der Benutzer manuell FFmpeg installieren oder konfigurieren muss. Dies wird erreicht, indem eine statisch kompilierte Version von FFmpeg direkt in das AppImage integriert wird. Die App soll diese gebündelte Version automatisch erkennen und bevorzugt verwenden.

---

## Sprint 1: Build-Prozess anpassen (Integration ins AppImage)
**Ziel:** FFmpeg-Binaries automatisiert herunterladen und in die Verzeichnisstruktur des AppImages (`AppDir`) einfügen.

- **Aufgabe 1:** Einbau eines Download-Schritts in das AppImage-Build-Skript (z.B. `build_appimage.sh` oder ähnlich).
  - Herunterladen eines aktuellen, statischen FFmpeg-Builds für Linux (Linux amd64), z.B. von *johnvansickle.com/ffmpeg*.
- **Aufgabe 2:** Entpacken des Archivs während des Build-Prozesses.
- **Aufgabe 3:** Kopieren der Dateien `ffmpeg` und `ffprobe` in das Zielverzeichnis des AppImages, vorzugsweise nach `AppDir/usr/bin/`.
- **Aufgabe 4:** Sicherstellen, dass beide Dateien ausführbar sind (`chmod +x AppDir/usr/bin/ff*`).
- **Test:** Das Build-Skript ausführen, das generierte AppImage mounten (z.B. mit `--appimage-extract`) und prüfen, ob die Dateien `usr/bin/ffmpeg` und `usr/bin/ffprobe` existieren und ausführbar sind.

---

## Sprint 2: Python-Logik anpassen (Erkennung des gebündelten FFmpeg)
**Ziel:** Die App soll beim Start prüfen, ob sie in einem AppImage läuft, und den Pfad zu FFmpeg entsprechend setzen.

- **Aufgabe 1:** Lokalisierung der Logik, die den FFmpeg-Pfad festlegt (vermutlich in einem Config-Manager oder App-Initialisierungs-Modul).
- **Aufgabe 2:** Auslesen der Umgebungsvariable `$APPDIR` (diese wird vom AppImage automatisch gesetzt).
- **Aufgabe 3:** Fallback-Logik implementieren:
  1. Prüfen, ob der User manuell einen benutzerdefinierten Pfad in den Settings gesetzt hat. (Wenn ja -> diesen verwenden).
  2. Falls nicht: Prüfen, ob `$APPDIR/usr/bin/ffmpeg` existiert. (Wenn ja -> diesen als Standard-Pfad nutzen).
  3. Falls beides nicht zutrifft (z.B. beim Ausführen aus dem Source-Code): Suche im System via `shutil.which('ffmpeg')`.
- **Aufgabe 4:** Gleiche Logik für `ffprobe` implementieren.
- **Test:** App aus dem Source-Code starten und per `print()` oder Log überprüfen, ob sie das System-FFmpeg nutzt.

---

## Sprint 3: Benutzeroberfläche (UI) & Edge-Cases
**Ziel:** Den Benutzer in den Settings transparent darüber informieren, welche FFmpeg-Version gerade aktiv ist.

- **Aufgabe 1:** In den neuen "System"-Subtabs der Settings den Status anzeigen (z.B. ein Label: *"Status: Gebündeltes FFmpeg aus AppImage wird verwendet"* vs. *"System-FFmpeg wird verwendet"*).
- **Aufgabe 2:** Sicherstellen, dass der "Reset"-Button für den FFmpeg-Pfad in der GUI korrekt auf den gebündelten Pfad zurückspringt, wenn die App im AppImage-Modus läuft.
- **Test 1 (AppImage-Ausführung):** Das neu gebaute AppImage auf einem System *ohne* installiertes FFmpeg starten und ein Video verarbeiten. Es muss fehlerfrei durchlaufen.
- **Test 2 (Settings-Override):** Im AppImage-Modus in den Settings manuell einen falschen FFmpeg-Pfad angeben -> Fehlermeldung provozieren. Dann auf "Reset" klicken -> prüfen, ob wieder das gebündelte FFmpeg aktiv ist.
- **Test 3 (Source-Code-Modus):** Prüfen, ob die App für Entwickler beim lokalen Ausführen via Python weiterhin problemlos funktioniert.
