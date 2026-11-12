"""Create and compare portable SHA-256 directory manifests."""

import argparse
from fnmatch import fnmatchcase
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys


def raise_walk_error(error):
    raise error


def is_junction(path):
    return getattr(os.path, "isjunction", lambda _: False)(path)


def file_digest(path):
    digest = sha256()
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"Normal dosya değil: {path}")
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
        after = os.fstat(source.fileno())

    current = path.lstat()
    if (
        not stat.S_ISREG(current.st_mode)
        or not os.path.samestat(before, current)
        or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
        or (before.st_size, before.st_mtime_ns) != (current.st_size, current.st_mtime_ns)
    ):
        raise ValueError(f"Okunurken değişen dosya: {path}")
    return {"bytes": after.st_size, "sha256": digest.hexdigest()}


def snapshot(root, excludes=()):
    if not root.is_dir():
        raise ValueError(f"Klasör bulunamadı: {root}")

    def excluded(path):
        relative = path.relative_to(root).as_posix()
        return any(fnmatchcase(relative, pattern) for pattern in excludes)

    records = {}
    for directory, children, filenames in os.walk(root, onerror=raise_walk_error):
        parent = Path(directory)
        children[:] = [
            name for name in sorted(children)
            if not excluded(parent / name) and not (parent / name).is_symlink()
            and not is_junction(parent / name)
        ]
        for name in sorted(filenames):
            path = parent / name
            if excluded(path) or not stat.S_ISREG(path.lstat().st_mode):
                continue
            records[path.relative_to(root).as_posix()] = file_digest(path)

    return {"version": 1, "files": records}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON içinde yinelenen alan: {key!r}")
        result[key] = value
    return result


def read_manifest(path):
    with path.open(encoding="utf-8-sig") as source:
        document = json.load(source, object_pairs_hook=unique_keys)
    if not isinstance(document, dict) or type(document.get("version")) is not int:
        raise ValueError(f"Manifest biçimi geçersiz: {path}")
    records = document.get("files")
    if document["version"] != 1 or not isinstance(records, dict):
        raise ValueError(f"Manifest biçimi geçersiz: {path}")

    for name, metadata in records.items():
        if (
            any(part in {"", ".", ".."} for part in name.split("/"))
            or "\x00" in name
            or not isinstance(metadata, dict)
            or type(metadata.get("bytes")) is not int
            or metadata["bytes"] < 0
            or not isinstance(metadata.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
        ):
            raise ValueError(f"Manifest kaydı geçersiz: {name!r}")
    return records


def compare(old, new):
    return {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "changed": sorted(
            name for name in old.keys() & new.keys()
            if (old[name]["bytes"], old[name]["sha256"]) != (new[name]["bytes"], new[name]["sha256"])
        ),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Klasör içeriğini kaydeder ve iki kaydı karşılaştırır.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="SHA-256 manifesti oluştur")
    create.add_argument("directory", type=Path)
    create.add_argument("manifest", type=Path)
    create.add_argument("--exclude", action="append", default=[], metavar="DESEN")
    diff = commands.add_parser("diff", help="Eklenen, kaldırılan ve değişen yolları göster")
    diff.add_argument("old", type=Path)
    diff.add_argument("new", type=Path)
    diff.add_argument("--json", action="store_true", help="Sonucu JSON olarak yaz")
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            if os.path.lexists(args.manifest):
                raise FileExistsError(f"Çıktı dosyası zaten var: {args.manifest}")
            manifest = snapshot(args.directory, args.exclude)
            serialized = json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
            with args.manifest.open("x", encoding="utf-8", newline="\n") as target:
                target.write(serialized)
            print(f"{len(manifest['files'])} dosya kaydedildi.")
            return 0

        differences = compare(read_manifest(args.old), read_manifest(args.new))
        if args.json:
            print(json.dumps(differences, indent=2))
        elif any(differences.values()):
            for key, label in [("added", "Eklenen"), ("removed", "Kaldırılan"), ("changed", "Değişen")]:
                for path in differences[key]:
                    print(f"{label}: {path!r}")
        else:
            print("Dosya içeriğinde veya yollarında fark yok.")
        return int(any(differences.values()))
    except (OSError, ValueError) as error:
        print(f"Hata: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
