# DAVTester 2.x  
*Modern WebDAV upload‑and‑execution tester*  

_rewrite of **davtest.pl 1.x** (2015) in Python 3_  

© 2015 – 2025 Websec SC & Contributors · GPL‑3.0‑or‑later  

---

## Table of Contents
1. [About](#about)  
2. [License](#license)  
3. [Features](#features)  
4. [Requirements](#requirements)  
5. [Installation](#installation)  
6. [Usage](#usage)  
   * [Command‑line](#command-line-mode)  
   * [TUI menu](#tui-menu-mode)  
7. [Tests & Backdoors](#tests--backdoors)  
8. [Examples](#examples)  
9. [Roadmap / TODO](#roadmap--todo)  
10. [Changelog](#changelog)  
11. [Credits](#credits)

---

## About
`DAVTester` targets WebDAV‑enabled servers to determine which script types can be **uploaded** and **executed**.

Workflow:

1. **MKCOL** — create temporary directory (optional)  
2. **PUT**    — upload language‑specific test payloads  
3. **MOVE** / **COPY** — bypass extension filters (optional)  
4. **GET**    — execute & validate via regex  
5. **Backdoor upload** if execution succeeded  
6. **Cleanup** artefacts (optional)

Python 3 rewrite adds: robust retry, rich progress bars, ncurses TUI, YAML test packs, JSON reporting.

---

## License
```
GNU General Public License v3.0 or later
See LICENSE for full text.
```

---

## Features

| Capability                              | v1.x (Perl) | v2.x (Python) |
|-----------------------------------------|:-----------:|:-------------:|
| Upload test payloads                    | ✅ | ✅ |
| MOVE / COPY extension bypass            | ✅ | ✅ |
| Backdoor auto‑upload                    | ✅ | ✅ |
| Retry & back‑off                        | ❌ | ✅ |
| Rich progress bars                      | ❌ | ✅ |
| ncurses TUI (npyscreen)                 | ❌ | ✅ |
| JSON reporting                          | ❌ | ✅ |
| Cross‑platform                          | ⚠️ | ✅ |

---

## Requirements
* Python ≥ 3.8  
* `webdavclient3`, `requests`, `rich`, `pyyaml`, `npyscreen`  

```bash
pip install webdavclient3 requests rich pyyaml npyscreen
```

---

## Installation
```bash
git clone https://github.com/yourorg/davtester.git
cd davtester
pip install -r requirements.txt
```

---

## Usage

### Command‑line mode
```bash
python davtester.py -u https://host/webdav/dir     -A user:pass --create-dir testDir --move --backdoors auto --cleanup
```

### TUI menu mode
Simply run without arguments:
```bash
python davtester.py
```
An ncurses form collects options.

---

## Tests & Backdoors
* **tests/** — YAML files named `php.yaml`, `aspx.yaml`, …  
  * Fields: `content`, `execmatch` (regex)  
* **backdoors/** — actual shells; must match a successful test extension.

`$$FILENAME$$` inside `content` is auto‑replaced with the random session filename.

---

## Examples
| Description | Command |
|-------------|---------|
| Basic upload test | `python davtester.py -u http://victim/dav/` |
| Test & drop shells automatically | `python davtester.py -u http://victim/dav/ -backdoors auto` |
| Authenticated upload of custom file | `python davtester.py -u https://victim/dav/ -A admin:pw -uploadfile backdoor.aspx -uploadloc shell.aspx` |

---

## Roadmap / TODO
* NTLM / Negotiate authentication  
* More language backdoors and tests  
* COPY/MOVE auth headers  
* Unit‑test harness for new YAML packs  

---

## Changelog
**2.1.0** (2025‑04‑19) — Python rewrite, rich UI, npyscreen TUI  
**1.2.x** — legacy Perl branch fixes  

---

## Credits
* **Chris Sullo**  (author 1.0)  
* **Paulino Calderón** (author 1.1)  
* **RewardOne** – modern Python rewrite  
* Community contributors – see `AUTHORS.md`
* SWORD - John - Version 2.0
