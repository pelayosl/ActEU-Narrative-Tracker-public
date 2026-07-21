#!/usr/bin/env python3
"""Generate pydoc HTML documentation for the whole ``app`` backend package.

Walks every module under ``app/``, runs pydoc on each, and writes the resulting
HTML files plus an ``index.html`` into an output directory (``docs/code`` by
default).

pydoc imports each module to document it, so a module whose third-party
dependencies are missing (e.g. the NLP tasks needing BERTopic / FastText, which
are not installed outside the worker image) cannot be documented. Such modules
are reported and skipped rather than aborting the whole run, so the script works
in a plain dev environment and produces a fuller set inside the NLP image.

Usage::

    python scripts/utils/generate_docs.py                 # -> docs/code/
    python scripts/utils/generate_docs.py -o build/apidocs # custom output dir
    python scripts/utils/generate_docs.py --only app.repositories  # subtree filter
"""

import argparse
import inspect
import os
import pydoc
import sys
from pathlib import Path

# Project root is two levels above this script (scripts/utils/), so the script
# works regardless of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = PROJECT_ROOT / "app"


def _patch_pydoc_show_private() -> None:
    """Make pydoc document single-underscore helper functions and methods.

    By default pydoc hides any name starting with ``_`` (unless a module defines
    ``__all__``), which omits this codebase's documented private helpers, such as the
    Celery task helpers (``_run``, ``_label``) and repository/service methods
    (``_build_filter``, ``_relevance_stage``). This widens the rule to reveal
    single-underscore (non-dunder) names on modules and on our own classes, while
    leaving pydantic models untouched so their schema pages are not flooded with
    framework internals.
    """
    original = pydoc.visiblename

    def is_pydantic(cls) -> bool:
        try:
            return any(base.__module__.startswith("pydantic") for base in cls.__mro__)
        except Exception:
            return False

    def visiblename(name, all=None, obj=None):
        is_private = name.startswith("_") and not (
            name.startswith("__") and name.endswith("__")
        )
        if all is None and is_private:
            if inspect.ismodule(obj):
                return True
            if (
                inspect.isclass(obj)
                and getattr(obj, "__module__", "").startswith("app")
                and not is_pydantic(obj)
            ):
                return True
        return original(name, all, obj)

    pydoc.visiblename = visiblename


def discover_modules(package_dir: Path) -> list[str]:
    """List the dotted module names of every Python file under a package.

    :param package_dir: The package directory to walk (e.g. ``<root>/app``).
    :returns: Sorted dotted module names, including ``__init__`` packages as the
        package name itself (e.g. ``app``, ``app.services``).
    """
    modules: list[str] = []
    for path in package_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(PROJECT_ROOT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]  # the package itself
        modules.append(".".join(parts))
    return sorted(set(modules))


def write_index(output_dir: Path, documented: list[str], skipped: list[tuple[str, str]]) -> None:
    """Write an ``index.html`` linking every documented module.

    :param output_dir: Directory the per-module HTML files were written to.
    :param documented: Dotted names of the modules that were documented.
    :param skipped: ``(module, reason)`` pairs for modules that could not be imported.
    """
    rows = "\n".join(
        f'<li><a href="{name}.html">{name}</a></li>' for name in documented
    )
    skipped_rows = "\n".join(
        f"<li><code>{name}</code> &mdash; {reason}</li>" for name, reason in skipped
    )
    skipped_section = (
        f"<h2>Skipped ({len(skipped)})</h2>\n"
        "<p>These modules could not be imported in this environment "
        "(typically missing NLP dependencies). Run inside the worker image "
        "to document them.</p>\n"
        f"<ul>\n{skipped_rows}\n</ul>"
        if skipped
        else ""
    )
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        "<title>ActEU backend API documentation</title>\n"
        "</head>\n<body>\n"
        "<h1>ActEU backend API documentation</h1>\n"
        f"<h2>Modules ({len(documented)})</h2>\n"
        f"<ul>\n{rows}\n</ul>\n"
        f"{skipped_section}\n"
        "</body>\n</html>\n"
    )
    (output_dir / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    """Generate the HTML docs and write an index. Returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "-o",
        "--output",
        default="docs/code",
        help="Output directory for the generated HTML (default: docs/code).",
    )
    parser.add_argument(
        "--only",
        default="app",
        help="Only document modules whose dotted name starts with this prefix "
        "(default: app).",
    )
    args = parser.parse_args()

    # pydoc must be able to import the app package, so the project root has to be
    # on sys.path regardless of where the script is invoked from.
    sys.path.insert(0, str(PROJECT_ROOT))

    # Reveal documented single-underscore helpers/methods that pydoc hides by default.
    _patch_pydoc_show_private()

    output_dir = (PROJECT_ROOT / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    modules = [m for m in discover_modules(PACKAGE_DIR) if m.startswith(args.only)]
    if not modules:
        print(f"No modules found under prefix '{args.only}'", file=sys.stderr)
        return 1

    documented: list[str] = []
    skipped: list[tuple[str, str]] = []

    # pydoc.writedoc writes "<module>.html" into the current directory, so run it
    # from the output directory and restore the cwd afterwards.
    previous_cwd = Path.cwd()
    os.chdir(output_dir)
    try:
        for name in modules:
            try:
                pydoc.writedoc(name)
                documented.append(name)
                print(f"  ok   {name}")
            except pydoc.ErrorDuringImport as exc:
                reason = str(getattr(exc, "value", exc))
                skipped.append((name, reason))
                print(f"  skip {name}: {reason}", file=sys.stderr)
            except Exception as exc:  # never let one bad module abort the run
                skipped.append((name, repr(exc)))
                print(f"  skip {name}: {exc!r}", file=sys.stderr)
    finally:
        os.chdir(previous_cwd)

    write_index(output_dir, documented, skipped)

    print(
        f"\nDocumented {len(documented)} module(s), skipped {len(skipped)}.\n"
        f"Open {output_dir / 'index.html'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
