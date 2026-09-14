#!/usr/bin/env python3
"""Exercise installed codec/hash tools and SQLite through real consumers."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

SQLITE_PROBE = r'''
import json, sqlite3, sys
from pathlib import Path
root = Path(sys.argv[1])
expected = sys.argv[2]
assert sqlite3.sqlite_version == expected, (sqlite3.sqlite_version, expected)
path = root / "smoke.sqlite"
with sqlite3.connect(path) as db:
    assert db.execute("pragma journal_mode=WAL").fetchone()[0] == "wal"
    db.execute("create table sample(id integer primary key, value integer)")
    db.executemany("insert into sample values (?, ?)", [(n,n*n) for n in range(200)])
    assert db.execute("select count(*), sum(value) from sample").fetchone() == (200,2646700)
    assert db.execute("select json_extract('{\"answer\":42}', '$.answer'), sqrt(81)").fetchone() == (42,9.0)
with sqlite3.connect(path) as db:
    db.execute("update sample set value=-1")
    db.rollback()
    assert db.execute("select value from sample where id=199").fetchone()[0] == 39601
    assert db.execute("pragma integrity_check").fetchone()[0] == "ok"
print(json.dumps({"sqlite_version": sqlite3.sqlite_version, "rows": 200,
                  "checks": ["WAL", "aggregate", "JSON", "math", "rollback", "reopen", "integrity"]}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, default=Path.home()/"toolchains/deps")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sqlite-version", default="3.54.0")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prefix = args.prefix.resolve()
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(prefix/"lib")
    env["PATH"] = str(prefix/"bin")+os.pathsep+env["PATH"]
    commands = []

    def run(name, command):
        commands.append(command)
        proc = subprocess.run(command, cwd=output, env=env, capture_output=True)
        (output/(name+".stdout")).write_bytes(proc.stdout)
        (output/(name+".stderr")).write_bytes(proc.stderr)
        proc.check_returncode()
        return proc.stdout

    (output/"empty.bin").write_bytes(b"")
    hashed = run("xxh64", [str(prefix/"bin/xxhsum"), "-H1", "empty.bin"])
    assert hashed.decode().split()[0] == "ef46db3751d8e999", hashed
    data = (b"emergent> repeated token induction\n"+bytes(range(256))) * 4096
    (output/"input.bin").write_bytes(data)
    run("zstd-encode", [str(prefix/"bin/zstd"), "input.bin", "-o", "data.zst"])
    run("zstd-decode", [str(prefix/"bin/zstd"), "-d", "data.zst", "-o", "decoded.bin"])
    assert (output/"decoded.bin").read_bytes() == data

    width, height = 64, 48
    pixels = bytes(channel for y in range(height) for x in range(width)
                   for channel in ((x*7+y*3)%256, (x*2+y*11)%256, (x*13+y*5)%256, 255))
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload))+kind+payload+
                struct.pack(">I", zlib.crc32(kind+payload)))
    rows = b"".join(b"\0"+pixels[y*width*4:(y+1)*width*4] for y in range(height))
    png = (b"\x89PNG\r\n\x1a\n"+
           chunk(b"IHDR", struct.pack(">IIBBBBB",width,height,8,6,0,0,0))+
           chunk(b"IDAT", zlib.compress(rows))+chunk(b"IEND", b""))
    (output/"input.png").write_bytes(png)
    run("webp-encode", [str(prefix/"bin/cwebp"), "-lossless", "input.png", "-o", "data.webp"])
    run("webp-decode", [str(prefix/"bin/dwebp"), "data.webp", "-pam", "-o", "decoded.pam"])
    header, decoded = (output/"decoded.pam").read_bytes().split(b"ENDHDR\n",1)
    assert b"WIDTH 64" in header and b"HEIGHT 48" in header and b"DEPTH 4" in header, header
    assert decoded == pixels
    sqlite = json.loads(run("sqlite", [sys.executable, "-c", SQLITE_PROBE,
                                      str(output), args.sqlite_version]))
    report = {"status":"PASS", "prefix":str(prefix), "commands":commands,
              "xxh64_empty":"ef46db3751d8e999", "zstd_bytes":len(data),
              "webp_lossless_rgba":[width,height], "sqlite":sqlite}
    (output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
