import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app" / "src" / "main" / "AndroidManifest.xml"
RELEASE_NOTES = ROOT / "release" / "RELEASE_NOTES.md"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update versionCode/versionName for the Network Quiz APK."
    )
    parser.add_argument("--version-name", required=True, help="New versionName, for example 2.10.1")
    parser.add_argument("--version-code", required=True, type=int, help="New versionCode, for example 26")
    parser.add_argument("--dry-run", action="store_true", help="Show intended changes without writing files")
    return parser.parse_args()


def replace_once(text: str, pattern: str, replacement: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise SystemExit(f"Pattern not found or replaced multiple times: {pattern}")
    return updated


def update_manifest(version_name: str, version_code: int, dry_run: bool):
    original = MANIFEST.read_text(encoding="utf-8")
    updated = replace_once(
        original,
        r'android:versionCode="\d+"',
        f'android:versionCode="{version_code}"',
    )
    updated = replace_once(
        updated,
        r'android:versionName="[^"]+"',
        f'android:versionName="{version_name}"',
    )
    if not dry_run:
        MANIFEST.write_text(updated, encoding="utf-8")
    return original, updated


def update_release_notes(version_name: str, dry_run: bool):
    if not RELEASE_NOTES.exists():
        original = ""
        updated = f"# v{version_name}\n\n- 在这里填写本次版本更新说明。\n"
    else:
        original = RELEASE_NOTES.read_text(encoding="utf-8")
        stripped = original.lstrip()
        if stripped.startswith("# v"):
            updated = replace_once(
                original,
                r'^# v[^\r\n]+',
                f"# v{version_name}",
            )
        else:
            updated = f"# v{version_name}\n\n" + original
    if not dry_run:
        RELEASE_NOTES.write_text(updated, encoding="utf-8")
    return original, updated


def main():
    args = parse_args()
    manifest_before, manifest_after = update_manifest(args.version_name, args.version_code, args.dry_run)
    notes_before, notes_after = update_release_notes(args.version_name, args.dry_run)

    print("Manifest:", MANIFEST)
    print("Release notes:", RELEASE_NOTES)
    if args.dry_run:
        print("Dry run only, no files were changed.")
    print(
        "versionCode/versionName preview:",
        re.search(r'android:versionCode="(\d+)"', manifest_before).group(1),
        "->",
        re.search(r'android:versionCode="(\d+)"', manifest_after).group(1),
        ",",
        re.search(r'android:versionName="([^"]+)"', manifest_before).group(1),
        "->",
        re.search(r'android:versionName="([^"]+)"', manifest_after).group(1),
    )
    first_heading_before = re.search(r'^# .+', notes_before, flags=re.M)
    first_heading_after = re.search(r'^# .+', notes_after, flags=re.M)
    print(
        "Release heading preview:",
        (first_heading_before.group(0) if first_heading_before else "(none)"),
        "->",
        (first_heading_after.group(0) if first_heading_after else "(none)"),
    )


if __name__ == "__main__":
    main()
