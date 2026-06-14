"""
Batch-convert a folder of PDFs to Markdown using MinerU.

Usage:
    python pdf_to_markdown.py
    python pdf_to_markdown.py input_folder
    python pdf_to_markdown.py input_folder output_folder

How to run (in the VS Code terminal, Ctrl+`):

    Step 1 (one-time setup):
        pip install "mineru[all]"
        pip install albumentations

    Step 2 (run the script):
        python pdf_to_markdown.py

    That's it. The first run will also download ~20 GB of AI models (one-time).

Notes:
    - Default input folder: "financial incentives literature/"
    - .md files are saved alongside the PDFs in the same folder.
    - IMPORTANT: PDF filenames must be under 117 characters (including .pdf).
      Longer names will cause errors due to the Windows 260-character path limit.
      The script checks this at startup and lists any files that are too long.
    - Calls MinerU's pipeline directly in Python (bypasses the v3 API server
      which has issues on Windows).
    - Uses the "pipeline" backend (works on CPU, no GPU required).
    - Equations are converted to LaTeX, tables to HTML within Markdown.
    - Figures are extracted and saved to a subfolder named {stem}_images/
      next to the .md file, with references updated in the Markdown.
"""

import shutil
import sys
import time
from pathlib import Path

DEFAULT_INPUT = Path("literature")
TEMP_WORK_DIR = Path("C:/temp/mineru_work")

# Workaround: fasttext C library can't open paths with non-ASCII chars (ø).
# Copy the model to a clean path and patch fast_langdetect to use it.
_FT_MODEL_SRC = Path(sys.prefix) / "lib/site-packages/fast_langdetect/ft_detect/resources/lid.176.ftz"
_FT_MODEL_DST = Path("C:/temp/fasttext_models/lid.176.ftz")
if _FT_MODEL_SRC.exists() and not _FT_MODEL_DST.exists():
    _FT_MODEL_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_FT_MODEL_SRC, _FT_MODEL_DST)
if _FT_MODEL_DST.exists():
    import os
    os.environ["FTLANG_CACHE"] = str(_FT_MODEL_DST.parent)
    try:
        import fast_langdetect.ft_detect.infer as _fti
        _fti.LOCAL_SMALL_MODEL_PATH = _FT_MODEL_DST
    except Exception:
        pass


def check_filename_lengths(pdfs: list, final_dir: Path):
    """Warn about filenames that are too long for Windows and exit."""
    # Longest output path: {final_dir}/{stem}_images/{image_name}
    # Reserve extra chars for "_images/" (8) + image filename (~20)
    max_stem = 255 - len(str(final_dir.resolve())) - 8 - 20
    too_long = [f for f in pdfs if len(f.stem) > max_stem]
    if too_long:
        max_name = max_stem + 4
        print("Error: The following PDF filenames are too long.")
        print(f"Max: {max_name} characters (including .pdf).\n")
        for f in too_long:
            print(f"  {len(f.name)} chars | {f.name}")
        print("\nPlease shorten these filenames and re-run.")
        sys.exit(1)


def init_model():
    """Initialize the MinerU pipeline model once (reused across all PDFs)."""
    print("Loading MinerU model (first time takes ~30s) ...", flush=True)
    from mineru.backend.pipeline.model_init import MineruPipelineModel
    model = MineruPipelineModel(
        device="cpu",
        table_config={"enable": True},
        formula_config={"enable": True},
        lang=None,
    )
    print("Model loaded.\n")
    return model


def convert_pdf(pdf_path: Path, final_dir: Path, work_dir: Path,
                model) -> bool:
    """Convert a single PDF to Markdown. Returns True on success."""
    stem = pdf_path.stem
    final_md = final_dir / f"{stem}.md"

    if final_md.exists():
        print(f"  [skip] {stem}.md already exists")
        return True

    print(f"  [converting] {pdf_path.name} ...", flush=True)
    t0 = time.time()

    temp_output = work_dir / "output"

    if temp_output.exists():
        shutil.rmtree(temp_output, ignore_errors=True)
    temp_output.mkdir(parents=True, exist_ok=True)

    try:
        pdf_bytes = pdf_path.read_bytes()
    except OSError as e:
        print(f"  FAILED (could not read PDF: {e})")
        return False

    try:
        from mineru.cli.common import do_parse

        do_parse(
            output_dir=str(temp_output),
            pdf_file_names=[stem],
            pdf_bytes_list=[pdf_bytes],
            p_lang_list=["en"],
            backend="pipeline",
            parse_method="auto",
            formula_enable=True,
            table_enable=True,
            f_dump_md=True,
            f_dump_middle_json=False,
            f_dump_model_output=False,
            f_dump_orig_pdf=False,
            f_dump_content_list=False,
        )

        elapsed = time.time() - t0

        md_candidates = list(temp_output.rglob("*.md"))
        if not md_candidates:
            print(f"  done ({elapsed:.1f}s) but no .md file found")
            return False

        md_text = md_candidates[0].read_text(encoding="utf-8")

        img_dirs = list(temp_output.rglob("images"))
        img_dirs = [d for d in img_dirs if d.is_dir()]
        if img_dirs:
            src_images = img_dirs[0]
            images = list(src_images.iterdir())
            if images:
                dest_images = final_dir / f"{stem}_images"
                if dest_images.exists():
                    shutil.rmtree(dest_images)
                shutil.copytree(src_images, dest_images)
                md_text = md_text.replace("](images/",
                                          f"]({stem}_images/")
                print(f"  extracted {len(images)} figure(s)")

        final_md.write_text(md_text, encoding="utf-8")

        print(f"  done ({elapsed:.1f}s)")
        return True

    except (OSError, ValueError, RuntimeError) as e:
        elapsed = time.time() - t0
        print(f"  FAILED ({elapsed:.1f}s)")
        print(f"  Error: {e}")
        return False
    finally:
        if temp_output.exists():
            shutil.rmtree(temp_output, ignore_errors=True)


def main():
    """Batch-convert all PDFs in the input folder to Markdown."""
    args = sys.argv[1:]
    input_dir = Path(args[0]) if len(args) >= 1 else DEFAULT_INPUT
    final_dir = Path(args[1]) if len(args) >= 2 else input_dir

    if not input_dir.is_dir():
        print(f"Error: Input folder '{input_dir}' does not exist.")
        sys.exit(1)

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in '{input_dir}'.")
        sys.exit(0)

    check_filename_lengths(pdfs, final_dir)

    TEMP_WORK_DIR.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    model = init_model()

    print(f"Converting {len(pdfs)} PDFs from '{input_dir}'")
    print(f".md files will be saved to '{final_dir}'")
    print("(MinerU pipeline, CPU mode)\n")

    success, failed = 0, 0
    t_total = time.time()

    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf.name}")
        if convert_pdf(pdf, final_dir, TEMP_WORK_DIR, model):
            success += 1
        else:
            failed += 1

    elapsed_total = time.time() - t_total
    print(f"\nDone. {success} converted, {failed} failed.")
    print(f"Total time: {elapsed_total:.0f}s")


if __name__ == "__main__":
    main()
