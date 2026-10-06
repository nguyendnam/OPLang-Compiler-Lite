"""Generate ANTLR Python sources on Windows, Linux, and macOS."""

from pathlib import Path
import shutil
import subprocess
from urllib.request import urlretrieve


ROOT = Path(__file__).resolve().parents[1]
VERSION = "4.13.2"


def main() -> None:
    if shutil.which("java") is None:
        raise SystemExit("Java is required to generate ANTLR sources. Install Java 17+.")

    output = ROOT / "build"
    output.mkdir(exist_ok=True)
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    jar = cache / f"antlr-{VERSION}-complete.jar"
    if not jar.exists():
        download = jar.with_suffix(".download")
        try:
            urlretrieve(f"https://www.antlr.org/download/{jar.name}", download)
            download.replace(jar)
        finally:
            download.unlink(missing_ok=True)

    subprocess.run(
        ["java", "-jar", str(jar), "-Dlanguage=Python3", "-visitor",
         "-no-listener", "-o", str(output), "OPLang.g4"],
        cwd=ROOT / "src" / "grammar",
        check=True,
    )
    (output / "__init__.py").touch()
    shutil.copyfile(ROOT / "src" / "grammar" / "lexererr.py", output / "lexererr.py")
    print(f"ANTLR {VERSION} sources generated in {output}")


if __name__ == "__main__":
    main()
