---
name: sunday-school-handouts
description: Generate publication-ready Sunday School scripture reading handouts, prophetic profile guides, and illustrated archaeological guides using WeasyPrint and ESV scripture text. Use when creating or updating weekly Sunday School reading pages, archaeological handouts, or PDF lesson materials.
triggers:
  - sunday school
  - reading handout
  - add pages for this reading
  - archaeological guide
  - archaeology guide
  - zephaniah_day_of_the_lord
  - josiah_reform_and_the_law
  - manasseh_dark_reign
  - weasyprint
---

# Sunday School Handouts & Curriculum Production

Produce publication-ready PDF handouts and companion Python generator scripts for the Sunday School curriculum (`~/code/jpshackelford/sunday-school-2026-27`).

## Bundled CLI Tools

Resolve paths relative to this skill's directory:

1. **`scripts/render_reading.py`** — Renders 2-column ESV scripture reading handouts from a JSON specification, automatically fetching ESV passages via `esv-scripture`, auto-fitting typography (`font-size`, `line-height`, `margin-bottom`) in memory via WeasyPrint's `Document.pages` so it never spills a few lines onto an extra page, and emitting a standalone `<name>.py` script matching the repository's convention.
2. **`scripts/pdf_check.py`** — Inspects any generated PDF (`pdfinfo` / `pdftotext` / `pypdf`), verifies expected page count, flags low-density spillover pages, and optionally renders 150 DPI PNG page previews via `pdftoppm`.
3. **`scripts/wikimedia_fetch.py`** — Resolves Wikimedia Commons `File:` titles or URLs via the MediaWiki API with a compliant `User-Agent` and exponential backoff, downloads high-resolution images into `images/`, records image dimensions (`landscape` vs `portrait`), and writes license/attribution metadata to `images/attribution.json`.

---

## Workflow 1: Scripture Reading Handouts

When asked to produce a scripture reading handout (following the pattern of `zephaniah_day_of_the_lord.py`, `josiah_reform_and_the_law.py`, or `manasseh_dark_reign.py`):

### Step 1: Prepare a JSON Spec (or Use `esv.py --format json --batch`)
Instead of running 10 separate `esv.py` shell commands and manually stripping headers or `(ESV)` tags, write a JSON spec with the section titles, references, and theological introductions. Leave `"paragraphs"` omitted (or empty) to let `render_reading.py` fetch them automatically via `ESV_API_KEY`:

```json
{
  "title": "King Josiah’s Major Religious Reform & Finding the Book of the Law",
  "subtitle": "c. 622 BC · Nov 1, 2026 · 2 Kings 22–23; 2 Chronicles 34–35 · Zephaniah, Huldah, & Jeremiah",
  "running_header": "KING JOSIAH'S REFORM & THE BOOK OF THE LAW (c. 622 BC)",
  "target_pages": 2,
  "sections": [
    {
      "title": "The Boy King Who Sought the God of David",
      "reference": "2 Chronicles 34:1–4, 8",
      "intro": "Ascending the throne of Judah at just eight years old after the fifty-seven-year apostasy of Manasseh and Amon, young Josiah seeks the LORD..."
    }
  ]
}
```

### Step 2: Render PDF & Emit Standalone `.py` Generator in One Command
Run `scripts/render_reading.py` (it automatically re-executes inside `./bin/python` if `weasyprint` is installed in the project virtualenv):

```bash
python3 scripts/render_reading.py /tmp/reading_spec.json \
  --pdf 2026-11-01/josiah_reform_and_the_law.pdf \
  --emit-py 2026-11-01/josiah_reform_and_the_law.py \
  --target-pages 2 \
  --cache-dir esv-cli/.cache
```

### Step 3: Verify Page Count & Density with `pdf_check.py`
```bash
python3 scripts/pdf_check.py 2026-11-01/josiah_reform_and_the_law.pdf --expect-pages 2
```

---

## Workflow 2: Illustrated Archaeological & Historical Guides

When creating illustrated handouts (such as `zephaniah_archaeology.py` or `hezekiah_tunnel.py`):

1. **Fetch Wikimedia Commons Images with `wikimedia_fetch.py`**:
   ```bash
   python3 scripts/wikimedia_fetch.py \
     --out-dir 2026-10-25/images \
     "File:Paleo-Hebrew_seal.jpg=nathan_melech_bulla.jpg" \
     "File:Jerusalem-Broad-Wall-770.jpg=broad_wall_jerusalem.jpg" \
     "File:Broadwall8.jpg=broad_wall_detail.jpg" \
     "File:Tel_Arad_280321_03_Temple.jpg=tel_arad_temple.jpg"
   ```
2. **Image Layout & Cropping Rules (Critical)**:
   - **Never crop archaeological photos**: Do not use `object-fit: cover` with a restrictive `max-height` that slices off important upper/lower details (such as the height of the Tel Arad temple mound or the thickness of the Broad Wall).
   - **Landscape Images (`width >= height`)**: Display at full page width (`width: 100%; height: auto;`) inside `.full-width-img-block`. When two photos illustrate the same site, stack them sequentially (`image -> narrative text -> second image`) rather than squeezing or cropping them into cards.
   - **Portrait Images (`height > width`)**: Center inside `.portrait-img-block` (`max-width: 60%; max-height: 300px; height: auto; margin: 0 auto;`).
   - **Pure Historical Captions**: Never mention editorial or layout choices (e.g., *"Full uncropped view"*, *"Shown full width"*) in reader-facing captions. Keep captions strictly historical, archaeological, and museum-focused, with license/author credit in `.img-credit`.
3. **Biblical Sequence Ordering**:
   - Arrange archaeological articles and pages in the **canonical / chronological order of the biblical passages** to which they relate (e.g., Zephaniah 1:4–5 -> Zephaniah 1:10 -> Zephaniah 1:11 -> 2 Kings 23:11 -> 2 Kings 22:8).
4. **Shared Visual Identity**:
   - Keep the dark slate header banner (`#0F172A` with `3px solid #991B1B` bottom border), warm ivory page background (`#FAFAF7`), crimson section headings (`#991B1B`), italic slate `.reading-intro` callout (`border-left: 2px solid #CBD5E1`), and Crossway ESV copyright attribution footer.
5. **Verify Layout**:
   - Always run `python3 scripts/pdf_check.py <output.pdf> --preview-dir /tmp/previews` to confirm no orphaned headings or accidental overflow pages exist.
