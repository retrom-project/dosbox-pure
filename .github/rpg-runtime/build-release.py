#!/usr/bin/env python3
"""Build and describe immutable DOSBox Pure EmulatorJS release assets."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--tag", required=True)
args = parser.parse_args()
fork = json.loads((ROOT / "retrom-fork.json").read_text())
baseline = fork["defaultBranch"].split("/", 1)[1]
if not re.fullmatch(r"retrom-core-" + re.escape(baseline) + r"-r[1-9][0-9]*(?:-rc\.[1-9][0-9]*)?", args.tag):
    raise SystemExit("RETROM_CORE_RELEASE_TAG_INVALID")
if not args.output.is_absolute() or not args.output.is_dir() or any(args.output.iterdir()):
    raise SystemExit("RETROM_CORE_RELEASE_OUTPUT_INVALID")

commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
    raise SystemExit("RETROM_CORE_RELEASE_WORKTREE_DIRTY")
expected = set(fork["releaseAssets"]) - {"rpg-runtime-release.json"}
with tempfile.TemporaryDirectory() as temporary:
    candidate = Path(temporary) / "candidate"
    candidate.mkdir()
    subprocess.run([str(ROOT / ".github/rpg-runtime/build-candidate.sh"), str(candidate)], check=True)
    descriptor = json.loads((candidate / "retrom-core-candidate.json").read_text())
    if descriptor["commit"] != commit or descriptor["dirty"] or descriptor["adapterAbi"] != fork["adapterAbi"]:
        raise SystemExit("RETROM_CORE_RELEASE_CANDIDATE_INVALID")
    if {path.name for path in candidate.iterdir()} != expected | {"retrom-core-candidate.json"}:
        raise SystemExit("RETROM_CORE_RELEASE_ASSETS_INVALID")

    archive = candidate / "dosbox_pure-thread-wasm.data"
    extracted = Path(temporary) / "extracted"
    extracted.mkdir()
    subprocess.run(["7z", "x", "-bd", "-bso0", "-bsp0", f"-o{extracted}", str(archive)], check=True)
    members = {"dosbox_pure_libretro.js", "dosbox_pure_libretro.wasm", "core.json", "build.json", "license.txt"}
    if {path.name for path in extracted.iterdir()} != members or any(
        not path.is_file() or path.is_symlink() for path in extracted.iterdir()
    ):
        raise SystemExit("RETROM_CORE_ARCHIVE_INVALID")
    if (extracted / "dosbox_pure_libretro.wasm").read_bytes()[:8] != b"\0asm\x01\0\0\0":
        raise SystemExit("RETROM_CORE_WASM_INVALID")
    if json.loads((extracted / "core.json").read_text())["name"] != "dosbox_pure":
        raise SystemExit("RETROM_CORE_ARCHIVE_INVALID")
    if (extracted / "license.txt").read_bytes() != (candidate / "LICENSE.md").read_bytes():
        raise SystemExit("RETROM_CORE_LICENSE_INVALID")
    for name in sorted(expected):
        shutil.copy2(candidate / name, args.output / name)

assets = [{"filename": name, "sizeBytes": (args.output / name).stat().st_size,
           "observedSha256": hashlib.sha256((args.output / name).read_bytes()).hexdigest()}
          for name in sorted(expected)]
metadata = {"schemaVersion": 1, "repository": fork["forkRepository"], "tag": args.tag,
            "commit": commit, "adapterAbi": fork["adapterAbi"], "assets": assets,
            "digestPolicy": "OBSERVED_CACHE_INTEGRITY_ONLY"}
(args.output / "rpg-runtime-release.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
