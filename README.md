# Challenge 1a: PDF Structure Extractor

This solution addresses Round 1A of the Adobe India Hackathon, focusing on extracting a structured outline (Title, H1, H2, H3) from PDF documents.

## Approach

The solution uses a **heuristic-based approach** without any machine learning models to meet the strict performance and resource constraints. The core logic is as follows:

1.  **Text Block Extraction:** It uses the `PyMuPDF` library to parse each PDF and extract all text blocks along with their metadata (text, font size, and page number).
2.  **Statistical Analysis:** It determines the most common font size in the document, which is assumed to be the **body text**.
3.  **Heading Identification:** Any text with a font size significantly larger than the body text is classified as a potential heading.
4.  **Hierarchical Mapping:** The identified heading font sizes are sorted in descending order to map the top three largest sizes to levels H1, H2, and H3.
5.  **Title Extraction:** The title is assumed to be the first piece of text found on the first page that has the largest heading font size.

This method is extremely fast, has a minimal memory footprint, and works entirely offline.

## Libraries Used

* **PyMuPDF (`fitz`):** A high-performance Python library for PDF parsing and manipulation.

## How to Build and Run

### Build Command

```bash
docker build --platform linux/amd64 -t pdf-processor:latest .