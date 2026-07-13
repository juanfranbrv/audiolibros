import os
import io

def extract_from_pdf(file_path):
    """Extracts text from a PDF file using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required for PDF support. Install it with `pip install pymupdf`.")

    text_content = []
    try:
        with fitz.open(file_path) as doc:
            for page in doc:
                text_content.append(page.get_text())
        return "\n".join(text_content)
    except Exception as e:
        raise RuntimeError(f"Error reading PDF file: {e}")

def extract_from_epub(file_path):
    """Extracts text from an EPUB file using EbookLib and BeautifulSoup."""
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("EbookLib and beautifulsoup4 are required for EPUB support. Install them with `pip install EbookLib beautifulsoup4`.")

    try:
        book = epub.read_epub(file_path)
        text_content = []

        spine_text = []
        seen_ids = set()
        for spine_entry in book.spine:
            item_id = spine_entry[0] if isinstance(spine_entry, (tuple, list)) else spine_entry
            item = book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue
            if item.get_id() not in seen_ids:
                seen_ids.add(item.get_id())
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                item_text = soup.get_text()
                if item_text.strip():
                    spine_text.append(item_text)

        if spine_text:
            text_content = spine_text
        else:
            for item in book.get_items():
                if item.get_type() != ebooklib.ITEM_DOCUMENT:
                    continue
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                item_text = soup.get_text()
                if item_text.strip():
                    text_content.append(item_text)

        if not text_content:
            raise ValueError("El EPUB no contiene documentos legibles.")
        
        return "\n".join(text_content)
    except Exception as e:
        raise RuntimeError(f"Error reading EPUB file: {e}")

import re

def clean_text(text):
    """
    Cleans text using a 'smart' strategy based on punctuation.
    - Joins lines that do NOT end in sentence-ending punctuation (., ?, !, :, ;, ", ”).
    - Preserves lines that DO end in punctuation (likely paragraph ends).
    - Removes hyphenation at line breaks.
    """
    if not text:
        return ""

    lines = text.splitlines()
    cleaned_lines = []
    
    # regex for line-ending punctuation (including quotes)
    # We treat these as "valid places to pause/break".
    # All other lines are merged into the previous one.
    sentence_ender = re.compile(r'[.?!:;"”]$')

    current_paragraph = []

    for line in lines:
        line = line.strip()
        
        if not line:
            # Found a blank line.
            # LOGIC CHANGE: Only treat as paragraph break if the LAST paragraph chunk
            # actually LOOKS like a sentence end.
            if current_paragraph:
                prev_chunk = current_paragraph[-1]
                # If previous chunk ends with punctuation, we honor the break.
                if sentence_ender.search(prev_chunk):
                     cleaned_lines.append(" ".join(current_paragraph))
                     current_paragraph = []
                # If it DOES NOT end in punctuation (e.g. "que me"), we IGNORE the blank line
                # and continue adding to current_paragraph.
            continue
        
        # Check for hyphenation (word- \n next)
        if current_paragraph and current_paragraph[-1].endswith('-'):
            prefix = current_paragraph.pop()[:-1] 
            current_paragraph.append(prefix + line) 
            continue # Skip normal logic for this line as we handled it
        
        # Normal logic
        if not current_paragraph:
            current_paragraph.append(line)
        else:
            prev_line = current_paragraph[-1]
            
            # Logic: If previous line implies sentence end, we PUSH the current paragraph 
            if sentence_ender.search(prev_line):
                cleaned_lines.append(" ".join(current_paragraph))
                current_paragraph = [line]
            else:
                # Previous line did NOT end in punctuation. Merge it.
                if prev_line.endswith('-'):
                    merged = prev_line[:-1] + line 
                    current_paragraph[-1] = merged
                else:
                    current_paragraph.append(line)

    # Flush remaining
    if current_paragraph:
        cleaned_lines.append(" ".join(current_paragraph))

    return "\n\n".join(cleaned_lines)


def get_text_content(file_path):
    """Auto-detects file type and returns extracted text content."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    text = ""
    if ext == '.pdf':
        text = extract_from_pdf(file_path)
    elif ext == '.epub':
        text = extract_from_epub(file_path)
    elif ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except UnicodeDecodeError:
            # Fallback to latín-1 if utf-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()
            
    else:
        raise ValueError(f"Unsupported file format: {ext}")
    
    return clean_text(text)
