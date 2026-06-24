import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ["TEMP"]) / "NetworkQuizApkBuild"
ANDROID_HOME = Path(os.environ["ANDROID_HOME"])
BUILD_TOOLS = ANDROID_HOME / "build-tools" / "35.0.0"
PLATFORM = ANDROID_HOME / "platforms" / "android-35" / "android.jar"


def run(args, cwd=None):
    cmd = [str(arg) for arg in args]
    print("RUN", subprocess.list2cmdline(cmd))
    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = completed.stdout or ""
    try:
        sys.stdout.write(output)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(output.encode(sys.stdout.encoding or "utf-8", errors="replace"))
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    if WORK.exists():
        shutil.rmtree(WORK)

    shutil.copytree(
        ROOT,
        WORK,
        ignore=shutil.ignore_patterns(".git", "build", ".codegraph", "tmp", "*.apk", "*.idsig"),
    )

    app = WORK / "app" / "src" / "main"
    build = WORK / "build"
    out = build / "out"
    for name in ("compiled", "gen", "classes", "dex", "out"):
        (build / name).mkdir(parents=True, exist_ok=True)

    aapt2 = BUILD_TOOLS / "aapt2.exe"
    d8 = BUILD_TOOLS / "d8.bat"
    zipalign = BUILD_TOOLS / "zipalign.exe"
    apksigner = BUILD_TOOLS / "apksigner.bat"

    run([aapt2, "compile", "--dir", app / "res", "-o", build / "compiled" / "res.zip"])
    run([
        aapt2,
        "link",
        "-I",
        PLATFORM,
        "--manifest",
        app / "AndroidManifest.xml",
        "--java",
        build / "gen",
        "-A",
        app / "assets",
        "--auto-add-overlay",
        "-o",
        out / "base-unsigned.apk",
        build / "compiled" / "res.zip",
    ])

    java_files = [str(path) for path in (app / "java").rglob("*.java")]
    java_files.extend(str(path) for path in (build / "gen").rglob("*.java"))
    run([
        "javac",
        "-encoding",
        "UTF-8",
        "-source",
        "8",
        "-target",
        "8",
        "-bootclasspath",
        PLATFORM,
        "-d",
        build / "classes",
        *java_files,
    ])

    run(["jar", "cf", build / "classes.jar", "-C", build / "classes", "."])
    run([d8, "--lib", PLATFORM, "--output", build / "dex", build / "classes.jar"])
    run(["jar", "uf", out / "base-unsigned.apk", "-C", build / "dex", "classes.dex"])
    run([zipalign, "-f", "-p", "4", out / "base-unsigned.apk", out / "network-quiz-aligned.apk"])

    keystore = WORK / "network_quiz_debug.keystore"
    if not keystore.exists():
        run([
            "keytool",
            "-genkeypair",
            "-v",
            "-keystore",
            keystore,
            "-storepass",
            "android",
            "-keypass",
            "android",
            "-alias",
            "networkquiz",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "10000",
            "-dname",
            "CN=DZ Network Quiz, OU=Study, O=DZ, L=Local, ST=Local, C=CN",
        ])

    signed_apk = out / "network-quiz.apk"
    run([
        apksigner,
        "sign",
        "--ks",
        keystore,
        "--ks-key-alias",
        "networkquiz",
        "--ks-pass",
        "pass:android",
        "--key-pass",
        "pass:android",
        "--out",
        signed_apk,
        out / "network-quiz-aligned.apk",
    ])
    run([apksigner, "verify", "--verbose", signed_apk])

    final_dir = ROOT / "build" / "out"
    final_dir.mkdir(parents=True, exist_ok=True)
    final_apk = final_dir / "计算机网络复习宝典.apk"
    shutil.copy2(signed_apk, final_apk)
    print("FINAL", final_apk, final_apk.stat().st_size)


if __name__ == "__main__":
    main()
