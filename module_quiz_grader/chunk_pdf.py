import pypdf, pandas as pd, textwrap, os, re, sys
from pathlib import Path
from datetime import datetime

CHUNK_LEN = 50  # words per chunk
OVERLAP = 20


def pdf_to_chunks(pdf_path: Path, module_code: str):
    reader = pypdf.PdfReader(str(pdf_path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    words = full_text.split()
    chunks = []
    idx = 0
    chunk_num = 0  # Add a separate counter for chunk IDs

    while idx < len(words):
        chunk_words = words[idx: idx + CHUNK_LEN]
        chunk_text = " ".join(chunk_words)
        chunk_id = f"{module_code}_{chunk_num:04d}"  # Use chunk_num instead
        chunks.append({"id": chunk_id, "text": chunk_text})
        idx += CHUNK_LEN - OVERLAP
        chunk_num += 1  # Increment the chunk counter

    return pd.DataFrame(chunks)

def main():
    pdf_path = Path(sys.argv[1]).resolve()
    module_code = sys.argv[2]           # e.g. PH01
    out_csv = Path("chunks_processed") / f"{module_code}_chunks.csv"
    out_csv.parent.mkdir(exist_ok=True)
    df = pdf_to_chunks(pdf_path, module_code)
    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} chunks → {out_csv}")

if __name__ == "__main__":
    """
    Example:
        python chunk_pdf.py "Phishing 101.pdf" PH01
    """
    main()
