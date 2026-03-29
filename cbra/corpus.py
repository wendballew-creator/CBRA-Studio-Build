from __future__ import annotations

from pathlib import Path
from typing import Dict, List


CANONICAL_ROLE_MAP: Dict[str, str] = {
    "CBRA_Kernel_v10_2.md": "ground_anchor",
    "CBRA_Loops_Core.md": "ground_anchor",
    "Drift_Constraints.md": "constraint_anchor",
    "CBRA_Glossary_v3.md": "operator_anchor",
}


def load_manifest(corpus_dir: Path) -> List[str]:
    """
    Reads CBRA_Corpus_Index.md and extracts active canonical filenames.
    """
    manifest_path = corpus_dir / "CBRA_Corpus_Index.md"

    if not manifest_path.exists():
        raise FileNotFoundError("CBRA_Corpus_Index.md not found in corpus directory")

    active_files: List[str] = []
    in_active_section = False

    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped.startswith("## Canonical Files (Active)"):
                in_active_section = True
                continue

            if stripped.startswith("##") and in_active_section:
                break

            if in_active_section and stripped and stripped[0].isdigit():
                parts = stripped.split(".", 1)
                if len(parts) == 2:
                    filename = parts[1].strip()
                    active_files.append(filename)

    return active_files


def get_active_corpus_files(corpus_dir: Path) -> List[Path]:
    """
    Returns only canonical active corpus files listed in the manifest.
    """
    files: List[Path] = []
    for filename in load_manifest(corpus_dir):
        path = corpus_dir / filename
        if path.exists():
            files.append(path)
    return files


def get_source_role(filename: str) -> str:
    """
    Returns the runtime retrieval role for a canonical file.
    """
    return CANONICAL_ROLE_MAP.get(filename, "contextual_evidence")


def load_canonical_corpus(corpus_dir: Path) -> str:
    """
    Loads and concatenates active canonical files into a single text blob.
    """
    combined_text: List[str] = []

    for file_path in get_active_corpus_files(corpus_dir):
        combined_text.append(file_path.read_text(encoding="utf-8", errors="replace"))

    return "\n\n".join(combined_text)
