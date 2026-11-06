"""Explicit corpus fixtures for retained historical-runtime tests."""

from pathlib import Path

from cbra.corpus import (
    ACTIVE_SECTION,
    CANONICAL_MANIFEST,
    LEGACY_EXECUTION_GRAMMAR,
    load_canonical_snapshot,
)


LEGACY_CORPUS_FILENAMES = (
    "CBRA_Glossary_v3.md",
    "CBRA_Loops_Core.md",
    "Drift_Constraints.md",
    "CBRA_Kernel_v10_2.md",
)
REPOSITORY_CORPUS_ROOT = Path(__file__).resolve().parents[1] / "corpus"


def write_legacy_corpus(root: Path) -> Path:
    """Create a bounded entity-stream-v1 corpus for historical tests."""
    root.mkdir(parents=True, exist_ok=True)
    manifest = [
        "# Historical runtime test corpus",
        "",
        "Execution grammar: {0}".format(LEGACY_EXECUTION_GRAMMAR),
        "",
        ACTIVE_SECTION,
    ]
    manifest.extend(
        "{0}. {1}".format(index, filename)
        for index, filename in enumerate(LEGACY_CORPUS_FILENAMES, start=1)
    )
    manifest.extend(
        [
            "",
            "## Scope",
            "- Generated only for retained entity-stream-v1 tests.",
        ]
    )
    (root / CANONICAL_MANIFEST).write_text(
        "\n".join(manifest) + "\n",
        encoding="utf-8",
    )
    for index, filename in enumerate(LEGACY_CORPUS_FILENAMES, start=1):
        source = REPOSITORY_CORPUS_ROOT / filename
        text = (
            source.read_text(encoding="utf-8")
            if source.is_file()
            else "Historical test strand {0}; not active canonical material.\n".format(
                index
            )
        )
        (root / filename).write_text(
            text,
            encoding="utf-8",
        )
    return root


def load_historical_test_snapshot(root: Path):
    """Load an explicit four-strand snapshot for historical-runtime tests."""
    return load_canonical_snapshot(write_legacy_corpus(root))
