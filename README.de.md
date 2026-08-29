# YouTube-Kurs-Manager

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2025.08.18-red)
![License](https://img.shields.io/badge/license-MIT-green)

Ein professioneller YouTube-Kurs-Downloader und -Manager mit Auto-Scheduling-Funktionen. Entwickelt zum Herunterladen von Bildungsplaylists mit Qualitätskontrolle, Wiederholungsmechanismen und umfassender Kursverfolgung.

## Funktionen

### Haupt-Downloader (`youtube_downloader.py`)
- **Playlist-Verwaltung**: Hinzufügen, Verfolgen und Verwalten mehrerer YouTube-Playlists
- **Qualitätskontrolle**: Download bis 1080p mit anpassbaren Qualitätseinstellungen
- **Größenlimits**: Maximale Dateigröße pro Video zur Speicherverwaltung festlegen
- **Intelligente Wiederholung**: Automatische Wiederholung mit Geo-Bypass bei fehlgeschlagenen Downloads
- **Fortschrittsverfolgung**: Echtzeit-Download-Fortschritt mit Geschwindigkeit und ETA
- **Fortsetzungsunterstützung**: Unterbrochene Downloads automatisch fortsetzen
- **Threaded-Analyse**: Schnelle Playlist-Analyse mit Multi-Threading
- **JSON-Zustandsverwaltung**: Dauerhafte Kursdaten und Download-Status

### Auto-Downloader (`auto_downloader.py`)
- **Geplante Downloads**: Automatischer Download ausstehender Kurse zu einer bestimmten Zeit
- **Interaktive Zeitkonfiguration**: Fragt beim Start nach der Zielzeit (HH:MM)
- **Nicht-interaktiver Modus**: Perfekt für Übernacht- oder geplante Downloads
- **Fehlerbehandlung**: Robuste Fehlerbehandlung mit detaillierter Protokollierung

## Projektstruktur

```
YouTube-Course-Manager/
├── youtube_downloader.py    # Hauptanwendung mit interaktivem Menü
├── auto_downloader.py       # Geplanter Auto-Download-Skript
├── YouTube_Courses/         # Verzeichnis für heruntergeladene Kurse
│   └── [Kursname]/
│       ├── playlist_info.json
│       └── *.mp4
└── README.md
```

## Installation

### Voraussetzungen

- Python 3.8 oder höher
- FFmpeg (empfohlen für beste Qualitätszusammenführung)

### Abhängigkeiten installieren

```bash
pip install yt-dlp colorama
```

### FFmpeg installieren (Optional aber empfohlen)

**Windows:**
```bash
# Mit Chocolatey
choco install ffmpeg

# Oder herunterladen von https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

## Verwendung

### Interaktiver Modus

Führen Sie den Haupt-Downloader für die interaktive Kursverwaltung aus:

```bash
python youtube_downloader.py
```

**Hauptmenü-Optionen:**
1. **[N]** Neuen Kurs von YouTube-Playlist-URL hinzufügen
2. **[D]** Alle ausstehenden Kurse herunterladen
3. **[U]** Alle gespeicherten Kurse aktualisieren (Playlists neu analysieren)
4. **[Q]** Beenden

**Kursaktionen:**
- **[1]** Download / Fortsetzen
- **[2]** Qualität / Größengrenze ändern
- **[3]** Qualität und Größe neu analysieren
- **[4]** Zusammenfassung anzeigen

### Auto-Download-Modus

Planen Sie automatische Downloads zu einer bestimmten Zeit:

```bash
python auto_downloader.py
```

**Konfiguration:**
- Zielzeit: **Wird interaktiv beim Start abgefragt** (z. B. `02:30` für 2:30 Uhr, `14:00` für 14:00 Uhr)
- Prüfintervall: 30 Sekunden
- Lädt automatisch alle ausstehenden Kurse einmal pro Tag zur angegebenen Zeit herunter

## Konfiguration

### Qualitätseinstellungen

Der Downloader unterstützt die folgenden Qualitätsoptionen:
- **Beste verfügbare**: Maximal 1080p (empfohlen)
- **1080p**: Full HD
- **720p**: HD
- **480p**: Standard Definition
- **360p**: Niedrige Bandbreite
- **Benutzerdefiniert**: Beliebig maximale Höhe einstellen (bis 1080p)

### Größenlimits

Sie können eine maximale Dateigröße pro Video zur Speicherverwaltung festlegen:
- Beispiel: `500 MB` - Videos größer als 500MB überspringen
- Auf `0` setzen für unbegrenzte Größe

## Funktionen im Detail

### Intelligente Download-Verwaltung
- Überspringt automatisch bereits heruntergeladene Videos
- Erkennt vorhandene Dateien durch Titelvergleich mit **Fuzzy-Matching-Fallback** (behandelt Unterschiede bei der Dateinamen-Bereinigung)
- Unterstützt mehrere Videoformate (.mp4, .mkv, .webm, .mov, .avi)
- **Aktualisiert JSON-Status automatisch nach Downloads** mit korrektem `downloaded`-Status und `downloaded_at`-Zeitstempeln

### Wiederholungsmechanismus
- Fehlgeschlagene Videos werden automatisch erneut versucht mit:
  - Geo-Bypass-Regionen (US, DE, GB, CA)
  - Format-Selektoren
- Dauerhafte Fehler werden im JSON-Zustand verfolgt

### Fortschrittsverfolgung
- Echtzeit-Fortschrittsbalken
- Download-Geschwindigkeitsüberwachung
- ETA-Schätzung
- Gesamtgrößenberechnung

### Datenpersistenz
Alle Kursdaten werden in `YouTube_Courses/[Kursname]/playlist_info.json` gespeichert:
```json
{
  "playlist": {
    "title": "Kurstitel",
    "channel": "Kanalname",
    "url": "https://youtube.com/playlist?list=...",
    "video_count": 50,
    "folder": "pfad/zum/kurs"
  },
  "settings": {
    "quality": "best",
    "max_size_mb": null,
    "max_quality": 1080
  },
  "videos": {
    "video_id": {
      "status": "success",
      "title": "Videotitel",
      "duration": 600,
      "resolution": "1080p",
      "filesize": 50000000,
      "downloaded": true
    }
  }
}
```

## Sicherheit

Dieses Projekt:
- **Sammelt oder überträgt** keine personenbezogenen Daten
- **Erfordert** keine API-Schlüssel oder Authentifizierungstoken
- **Verwendet** nur öffentliche YouTube-Daten über `yt-dlp`
- **Speichert** alle Daten lokal auf Ihrem Gerät

**Hinweis**: Die `playlist_info.json`-Dateien enthalten lokale Dateipfade. Committen Sie diese Dateien nicht in öffentliche Repositories, wenn Sie Ihre Verzeichnisstruktur privat halten möchten.

## Fehlerbehebung

### Häufige Probleme

**1. "Sign in to confirm you're not a bot"**
- Dies ist eine YouTube-Anti-Bot-Maßnahme
- Der Downloader probiert automatisch verschiedene Regionen
- Bei anhaltenden Problemen erwägen Sie die Verwendung von Cookies:
  ```bash
  yt-dlp --cookies-from-browser chrome "VIDEO_URL"
  ```

**2. FFmpeg nicht gefunden**
- Installieren Sie FFmpeg wie oben beschrieben
- Oder verwenden Sie `pip install yt-dlp[ffmpeg]`

**3. Langsame Downloads**
- YouTube könnte Ihre Verbindung drosseln
- Versuchen Sie Downloads außerhalb der Spitzenzeiten
- Erwägen Sie die Verwendung eines VPN

**4. Einige Videos können nicht heruntergeladen werden**
- Videos können geografisch eingeschränkt sein
- Private oder gelöschte Videos werden als fehlgeschlagen markiert
- Der Wiederholungsmechanismus wird es mehrmals versuchen

## Mitwirken

Beiträge sind willkommen! Bitte zögern Sie nicht, einen Pull Request einzureichen.

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE)-Datei für Details.

## Danksagungen

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Die leistungsstarke YouTube-Downloader-Bibliothek
- [colorama](https://github.com/tartley/colorama) - Plattformübergreifender farbiger Terminaltext

## Haftungsausschluss

Dieses Tool ist nur für den persönlichen Gebrauch bestimmt. Respektieren Sie die Nutzungsbedingungen von YouTube und die Rechte der Content-Ersteller. Laden Sie nur Inhalte herunter, für die Sie die Download-Berechtigung haben.
