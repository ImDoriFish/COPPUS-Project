# COPUS Reader — Project Instructions

## What this project is
A Python tool that reads scanned paper COPUS sheets (Classroom Observation Protocol
for Undergraduate STEM) and extracts the data into a CSV for research analysis.

The COPUS sheet is a checkbox grid:
- Rows: 15 two-minute intervals (0-2, 2-4, ... 28-30)
- Columns: 14 student codes, 12 instructor codes, engagement (L, M, H), Inter, Comments
- Observers put a check in every cell where that code happened in that interval.
  They may also draw a vertical line through several rows to show an activity continued.
- The form is printed landscape, so scans come out rotated 90 degrees.

Most of the sheet is checkboxes, so this is Optical Mark Recognition (detect ink in each
cell), NOT handwriting OCR. Handwriting (Inter numbers, Comments, header) comes later.

## How I want you to help — IMPORTANT
I am building this myself to LEARN. I do the work. You are here for context and for
help when I ask for it — like a mentor sitting next to me, not someone driving.

Default behavior:
- Only respond to what I ask. Do not take initiative or jump ahead.
- Do NOT edit, create, or delete files, and do NOT run commands, unless I explicitly
  ask you to in that message.
- Do NOT write my code for me. If I ask how to do something, explain the idea and
  point me to the OpenCV function(s) or docs page to look at.
- Do not move on to the next step or milestone on your own.

When I ask for help:
- Answer the specific question, briefly. Use this file's context so I don't have
  to re-explain the project.
- If I'm stuck: hint first. If I'm still stuck, a small example (a few lines),
  not a full solution.
- When I share code or an error: explain what's wrong and why, and let me fix it.
- Explain new terms simply. Use C++ comparisons when helpful (I know C++ well).
- Mention the relevant OpenCV-Python Tutorials page (docs.opencv.org) if useful.

If I explicitly say "write it", "fix it", or "do it", then you may do it.

## About me
- C/C++: strong (9/10). TypeScript: 5/10. Python: 6/10.
- New to OpenCV, computer vision, and using third-party packages.
- Windows, VS Code, PowerShell. Project uses a venv at .venv

## Stack
- Python, OpenCV (opencv-python), NumPy, pandas, Matplotlib
- .py files for the real tool
- Later: TrOCR or a vision AI model for handwriting; maybe Streamlit for a UI

## The pipeline (what the finished program does for each scan)
1. Load image
2. Grayscale
3. Rotate upright
4. Threshold to black/white (Otsu)
5. Find the table's outer border (contours, biggest rectangle)
6. Perspective-warp it to a fixed size so every scan has identical geometry
7. Use known cell positions (measured once from a blank form)
8. For each cell: crop, shrink inward to avoid grid lines, count ink, compare to threshold
9. Build table: one row per interval, one column per code (1/0)
10. Validate (e.g. only one of L/M/H per row) and save CSV

## Milestones (build order)
1. Load, grayscale, rotate, save                         -> steps 1-3
2. Find and straighten the table                         -> steps 4-6
3. Locate cells, draw boxes to verify alignment          -> step 7
4. Detect checkmarks on a filled sheet                   -> step 8
5. Build table, validate, export CSV                     -> steps 9-10
6. (Later) Handwriting: Inter, Comments, header

## Planned file structure
- layout.py     form structure (code lists) + cell positions
- image_prep.py steps 1-6
- extract.py    steps 7-8
- export.py     steps 9-10
- main.py       runs everything: scan in, CSV out
- scans/        test images (blank + filled sheets)

## Code lists (for layout.py)
INTERVALS  = 0-2 ... 28-30 (15 rows)
STUDENT    = L, Ind, Fol, CG, WG, OG, AnQ, SQ, WC, Prd, SP, TQ, W, O
INSTRUCTOR = Lec, RtW, FUp, PQ, CQ, AnQ, MG, 1o1, D/V, Adm, W, O
ENGAGEMENT = L, M, H, Inter

## Two-page sheets and upload rules
- One observation = 2 pages: page 1 covers 0-30 min, page 2 covers 30-50 min.
- Pages can arrive in any mix of files: one PDF with many pages, several PDFs,
  PNGs/JPGs, or a mix. load_pages() flattens everything into one ordered list of
  (source, image) pages, e.g. ("stack.pdf p3", img).
- Later (after Milestone 3): identify_page() labels each page 1 or 2 by looking at
  the page itself (easiest signal: after the warp, page 1's table is tall with 15
  interval rows, page 2's is short with 10). The source label ("stack.pdf p1") is
  only the position in the file and is NOT used to decide page type.
- group_observations() walks the list in upload order, looking at 2 neighbouring
  pages at a time: if one is page 1 and the other is page 2 (EITHER order), they
  are a pair -> sort to (page 1, page 2), skip ahead 2. Otherwise report an error
  naming the page by its source label and move on.
  Do NOT just chunk the list by 2 (one missing page silently shifts every pair).
- RULE for users: every upload must contain complete observations. Both pages of
  an observation go in the SAME upload, NEXT TO EACH OTHER. Order within the pair
  doesn't matter (A2, A1 is fine - code can tell page 1 from page 2), but
  observations can't be mixed (A1, B1, A2, B2 is wrong - code can't tell A from B).
  Uploading page 1 now and page 2 in a later run is not supported (each run
  starts fresh).
- Not detectable until Milestone 6 (handwriting): A1 + B2 looks like a valid pair.
- Errors to show: lone page 2 -> error; page 1 with no page 2 -> error
  (unless short observations are allowed; still undecided).
- Converted PDF pages are named {stem}_p{n}.png in scans/converted_png/.
- Observation names: source file + number (e.g. stack_obs1). CSV gets
  'observation' and 'source' columns so rows trace back to the paper sheet.
- Blank page 2 = blank_02.pdf (move from Sup_pic/ to scans/). rotate_upright works
  on it: page 2 also has the header text, table fills only the top half.

## Gotchas to remind me about
- cv2.imread returns None (no error) if the path is wrong
- OpenCV colors are BGR, not RGB
- Drawing uses (x, y), array indexing uses img[y, x]
- Always check (.venv) is active before pip install

## Current status
Milestone: 1 (not started)
Notes: