# process_pdfs.py (Definitive Hybrid Engine)

import fitz  # PyMuPDF
import json
import re
from pathlib import Path
from collections import Counter, defaultdict

def heuristic_layout_analysis(doc):
    """
    Performs a deep, feature-based analysis of the document layout to identify
    structure when no TOC is available. This is the fallback engine.
    """
    blocks = []
    # 1. Reconstruct lines word-by-word for maximum accuracy
    for page_num, page in enumerate(doc, 1):
        words = page.get_text("words")
        if not words:
            continue

        lines = defaultdict(list)
        for w in words:
            # Group words by their vertical position (y0) to form lines
            lines[round(w[1])].append(w)

        y_pos = 0
        for y_key in sorted(lines.keys()):
            line_words = sorted(lines[y_key], key=lambda w: w[0]) # Sort words by horizontal position
            line_text = " ".join(w[4] for w in line_words).strip()
            if not line_text:
                continue

            first_word = line_words[0]
            bbox = fitz.Rect(first_word[:4])
            font_size = round(first_word[3] - first_word[1]) # Calculate size from word bbox
            
            # Extract font info using available PyMuPDF methods
            is_bold = False
            try:
                page_fonts = page.get_fonts()
                for font in page_fonts:
                    if len(font) > 3 and font[3]:  # Check if font name exists
                        font_name = font[3].lower()
                        if "bold" in font_name:
                            is_bold = True
                            break
            except:
                is_bold = False

            space_above = bbox.y0 - y_pos if y_pos > 0 else 20
            y_pos = bbox.y1

            blocks.append({
                "text": line_text,
                "style": (font_size, is_bold),
                "space_above": space_above,
                "page": page_num
            })

    if not blocks:
        return {"title": "", "outline": []}

    # 2. Identify body text style and spacing
    style_counter = Counter(b['style'] for b in blocks)
    body_style = style_counter.most_common(1)[0][0]
    body_spacing = [b['space_above'] for b in blocks if b['style'] == body_style]
    avg_body_spacing = (sum(body_spacing) / len(body_spacing)) if body_spacing else 10

    # 3. Calculate a "heading score" for each block
    for b in blocks:
        score = 0
        if b['style'] != body_style:
            score += (b['style'][0] - body_style[0]) * 5 # Size difference
            if b['style'][1]: score += 10 # Bold
            if b['space_above'] > avg_body_spacing * 1.8: score += 15 # Space above
        b['score'] = score
    
    # 4. Contextual Filter: Remove items that look like lists or form fields
    potential_headings = [b for b in blocks if b['score'] > 0]
    style_groups = defaultdict(list)
    for h in potential_headings:
        style_groups[h['style']].append(h)

    final_headings = []
    for style, items in style_groups.items():
        # If a style has many items, it's likely a list, not headings.
        if len(items) > 10:
            continue
        final_headings.extend(items)

    if not final_headings:
        title = doc.metadata.get('title', '') or (blocks[0]['text'] if blocks else "")
        return {"title": title, "outline": []}

    # 5. Cluster scores to find H1, H2, H3 thresholds
    scores = sorted(list(set(b['score'] for b in final_headings)), reverse=True)
    score_map = {}
    if len(scores) > 0: score_map[scores[0]] = "H1"
    if len(scores) > 1: score_map[scores[1]] = "H2"
    if len(scores) > 2: score_map[scores[2]] = "H3"
    
    outline = []
    for b in final_headings:
        if b['score'] in score_map:
            outline.append({
                "level": score_map[b['score']],
                "text": b['text'],
                "page": b['page']
            })
            
    # # 6. Determine title and clean up outline
    # title = doc.metadata.get('title', '')
    # if not title and outline:
    #     # Prefer first H1, then first outline item
    #     h1s = [h for h in outline if h['level'] == 'H1']
    #     title = h1s[0]['text'] if h1s else outline[0]['text']
    # elif not title and blocks:
    #     title = blocks[0]['text']

    # final_outline = [item for item in outline if item['text'] != title]
    # return {"title": title, "outline": final_outline}

    # /////////////////////

    # #WORKING FOR FILE 1 + FILE 2(WITHOUT TITLE)
    #     # 6. Determine title and clean up outline
    # content_title = None
    # h1s = [h for h in outline if h['level'] == 'H1']
    # if h1s:
    #     content_title = h1s[0]['text']

    # meta_title = doc.metadata.get('title', '').strip()
    

    
    # # Decide final title: prefer content title if it's significantly more readable
    # def is_meta_title_generic(meta_title):
    #     return bool(re.search(r'(microsoft word|untitled|\.doc|\.pdf)', meta_title.lower()))
    
    # if not meta_title or is_meta_title_generic(meta_title):
    #     title = content_title or (blocks[0]['text'] if blocks else '')
    # else:
    #     # If both exist, prefer the content title if it's much longer or more descriptive
    #     if content_title and len(content_title.split()) > len(meta_title.split()):
    #         title = content_title
    #     else:
    #         title = meta_title

    # # Remove duplicate from outline if it matches title
    # final_outline = [item for item in outline if item['text'] != title]
    # return {"title": title, "outline": final_outline}

        # /////////////////////


    # 6. Determine title and clean up outline
    meta_title = doc.metadata.get('title', '').strip()
    
    def is_meta_title_generic(meta_title):
        return bool(re.search(r'(microsoft word|untitled|\.doc|\.pdf)', meta_title.lower()))

    # Gather consecutive H1s from page 1 for potential title
    page1_h1s = [h for h in outline if h['level'] == 'H1' and h['page'] == 1]
    combined_content_title = "  ".join(h['text'] for h in page1_h1s) if page1_h1s else None

    # Decide on final title
    if not meta_title or is_meta_title_generic(meta_title):
        title = combined_content_title or (outline[0]['text'] if outline else '')
    else:
        if combined_content_title and len(combined_content_title.split()) > len(meta_title.split()):
            title = combined_content_title
        else:
            title = meta_title

    # Remove outline items matching parts of title
    title_parts = {part.strip() for part in title.split("  ") if part.strip()}
    final_outline = [item for item in outline if item['text'].strip() not in title_parts]

    return {"title": title, "outline": final_outline}



def extract_structure_from_pdf(pdf_path):
    """
    Main orchestrator. Runs the high-accuracy TOC engine first, then falls back
    to the deep layout analysis engine.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"  -> ERROR: Could not open {pdf_path.name}. Reason: {e}")
        return {"title": "Error opening file", "outline": []}

    # # --- Lens 1: High-Fidelity Table of Contents Extraction ---
    # toc = doc.get_toc(simple=False)
    # if toc:
    #     outline = []
    #     for level, toc_title, page, _ in toc:
    #         # The problem asks for H1, H2, H3. Cap the level here.
    #         h_level = min(level, 3)
    #         outline.append({"level": f"H{h_level}", "text": toc_title.strip(), "page": page})
        
    #     if outline:
    #         # Use PDF metadata title if available, otherwise use the first TOC item.
    #         title = doc.metadata.get('title', '').strip() or outline[0]['text']
    #         # Remove the title from the outline if it was duplicated
    #         final_outline = [item for item in outline if item['text'] != title]
    #         return {"title": title, "outline": final_outline}

    # # --- Lens 2: Fallback to Deep Heuristic Layout Analysis Engine ---
    return heuristic_layout_analysis(doc)


def main():
    """
    Sets up input/output folders and processes all PDFs found in the input folder.
    """
    # Assume the script is run from the project root.
    # Create paths relative to the script's location.
    script_dir = Path(__file__).parent
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"

    # Create folders if they don't exist
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    print(f"Looking for PDFs in: {input_dir.resolve()}")
    
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print("\n--- No PDF files found! ---")
        print("Please place your PDF files in the 'input' folder next to this script.")
        return

    print(f"\nFound {len(pdf_files)} PDF(s). Starting processing...")
    for pdf_file in sorted(pdf_files):
        print(f"Processing: {pdf_file.name}")
        output_data = extract_structure_from_pdf(pdf_file)
        
        # Define the output path with _output suffix
        output_file_path = output_dir / f"{pdf_file.stem}_output.json"
        
        # Write the JSON output
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        print(f"  -> Saved output to: {output_file_path.resolve()}")
        
    print("\nProcessing complete.")


if __name__ == "__main__":
    main()

