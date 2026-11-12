"""Zentrale lokale Sessionwerte: .env lesen, ohne Werte auszugeben oder Code auszuführen."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile

SESSION_FILE = Path(__file__).resolve().parent / ".env"
TOKEN_ENV = "OPENBIS_PLAYGROUND_TOKEN"
_KEY = re.compile(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


class SessionConfigError(ValueError):
    """Die Nachricht enthält niemals den eingelesenen Inhalt."""


def _read(path):
    try:
        return path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    except (OSError, UnicodeError):
        raise SessionConfigError("Sessiondatei .env ist nicht als UTF-8 lesbar.") from None


def _values(text):
    result = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _KEY.match(line)
        if not match or match[1] in result:
            raise SessionConfigError(f"Sessiondatei .env: Schlüssel fehlt oder ist doppelt in Zeile {number}.")
        value = line[match.end():].strip()
        try:
            if value.startswith('"'):
                value, end = json.JSONDecoder().raw_decode(value)
                tail = line[match.end():].strip()[end:].strip()
                if not isinstance(value, str) or tail and not tail.startswith("#"):
                    raise ValueError
            elif value.startswith("'"):
                end = value.index("'", 1)
                value, tail = value[1:end], value[end+1:].strip()
                if tail and not tail.startswith("#"):
                    raise ValueError
            else:
                value = "" if value.startswith("#") else re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        except (ValueError, TypeError):
            raise SessionConfigError(f"Sessiondatei .env: ungültige Schreibweise in Zeile {number}.") from None
        result[match[1]] = value
    return result


def session_value(key, path=None):
    """Nichtleere Prozessvariable hat Vorrang; Datei wird bei jedem Aufruf neu gelesen."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        raise SessionConfigError("Ungültiger Name für einen Sessionwert.")
    existing = os.environ.get(key, "")
    if existing.strip():
        return existing
    return _values(_read(Path(path) if path is not None else SESSION_FILE)).get(key, "")


def session_status():
    """Geeignet zum Anzeigen im Notebook: nur Herkunft/Status, niemals Werte."""
    try:
        if not session_value(TOKEN_ENV).strip():
            return ("Kein Zugang: OPENBIS_PLAYGROUND_TOKEN fehlt. GaSi_00_Session_einrichten.ipynb "
                    "ausführen oder den Wert in der lokalen .env eintragen.")
        source = "Umgebungsvariable" if os.environ.get(TOKEN_ENV, "").strip() else "lokale .env"
        return f"Sessionwert aus {source} verfügbar; Gültigkeit wird erst bei der Verbindung geprüft."
    except SessionConfigError as exc:
        return str(exc)


def save_playground_token(token, path=None):
    """Nur diesen Schlüssel atomar ändern; andere Sessionwerte und Kommentare erhalten."""
    if not isinstance(token, str):
        raise SessionConfigError("Token muss verdeckt als Text eingegeben werden.")
    token = token.strip()
    if not token:
        return "Leere Eingabe: vorhandene Sessiondatei unverändert."
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
        raise SessionConfigError("Token enthält Leer-/Steuerzeichen; erneut eingeben.")
    path = Path(path) if path is not None else SESSION_FILE
    text = _read(path)
    _values(text)  # Bei ungültiger vorhandener Datei nichts überschreiben.
    lines = text.splitlines()
    replacement = TOKEN_ENV + "=" + json.dumps(token, ensure_ascii=True)
    index = next((i for i, line in enumerate(lines)
                  if (m := _KEY.match(line.strip())) and m[1] == TOKEN_ENV), None)
    if index is None:
        lines.append(replacement)
    else:
        lines[index] = replacement
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".env.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
    except OSError:
        raise SessionConfigError("Sessiondatei konnte nicht gespeichert werden; lokalen Dateizugriff prüfen.") from None
    finally:
        if temporary is not None and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass  # Eventueller Rest bleibt unter dem ignorierten .env.*-Muster.
    return "Token in der lokalen .env gespeichert. Keine Ausgabe des Wertes; keine Verbindung aufgebaut."
