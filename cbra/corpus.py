from pathlib import Path
from typing import List


def load_manifest(corpus_dir: Path) -> List[str]:
    """
    Reads CBRA_Corpus_Index.md and extracts active canonical filenames.
    """
    manifest_path = corpus_dir / "CBRA_Corpus_Index.md"

    if not manifest_path.exists():
        raise FileNotFoundError("CBRA_Corpus_Index.md not found in corpus directory")

    active_files = []
    in_active_section = False

    with manifest_path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped.startswith("## Canonical Files (Active)"):
                in_active_section = True
                continue

            if stripped.startswith("##") and in_active_section:
                break  # exit section when next header begins

            if in_active_section and stripped and stripped[0].isdigit():
                # format: "1. CBRA_Glossary_v3.md"
                parts = stripped.split(".", 1)
                if len(parts) == 2:
                    filename = parts[1].strip()
                    active_files.append(filename)

    return active_files


def load_canonical_corpus(corpus_dir: Path) -> str:
    """
    Loads and concatenates active canonical files into a single text blob.
    """
    active_files = load_manifest(corpus_dir)

    combined_text = []

    for filename in active_files:
        file_path = corpus_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Canonical file missing: {filename}")

        combined_text.append(file_path.read_text(encoding="utf-8"))

    return "\n\n".join(combined_text)
