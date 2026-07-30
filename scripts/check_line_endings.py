#!/usr/bin/env python3
"""Rifiuta gli script di shell con terminatori CRLF.

Bash rifiuta `set -euo pipefail\\r` con `invalid option name`, e il container si
ferma prima di eseguire qualunque cosa. È successo due volte in un giorno, per
due cause diverse: git che converte al commit — risolto da `.gitattributes` — e
`pathlib.write_text` che su Windows traduce `\\n` in `\\r\\n` salvo indicare
`newline="\\n"`. La seconda `.gitattributes` non la copre.

Un difetto che si ripete per cause diverse non è una distrazione: è una
condizione che il progetto non controlla. Questo la controlla.

    python scripts/check_line_endings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PATTERNS = ("*.sh",)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    offenders: list[tuple[Path, int]] = []
    checked = 0

    for pattern in PATTERNS:
        for path in sorted(root.rglob(pattern)):
            if ".git" in path.parts:
                continue
            checked += 1
            data = path.read_bytes()
            if b"\r\n" in data:
                line = data.split(b"\r\n")[0].count(b"\n") + 1
                offenders.append((path.relative_to(root), line))

    for path, line in offenders:
        print(f"ERRORE  {path}: terminatori CRLF dalla riga {line}. "
              f"Bash rifiuta uno script con \\r: usa LF.")

    status = "pass" if not offenders else "fail"
    print(f"\n{checked} script verificati, {len(offenders)} con CRLF — {status}")
    return 0 if not offenders else 1


if __name__ == "__main__":
    raise SystemExit(main())
