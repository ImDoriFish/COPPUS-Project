import cv2
import pymupdf
import numpy as np
from pathlib import Path
from layout import PAGE_SIZES
from identify import identify_page


# ---------- Folders and settings ----------

BASE_DIR = Path(__file__).parent              # folder this .py file lives in
SCANS_DIR = BASE_DIR / "scans"                # input scans (PDF / PNG / JPG)
CONVERTED_DIR = SCANS_DIR / "converted_png"   # PDF pages converted to PNG
OUT_DIR = BASE_DIR / "out"                    # debug images, CSVs, etc.

IMAGE_EXTS = {".png", ".jpg", ".jpeg"}        # image types we load directly


# ---------- Helpers ----------

def resolve_path(file_name):
    """Turn a file name into a full path.

    - Just a name ("blank_01.pdf")  -> looked up inside scans/
    - Already a full path           -> used as-is (handy for tests)
    """
    path = Path(file_name)
    if not path.is_absolute():
        path = SCANS_DIR / path
    return path


# ---------- load ----------

def image_converter(pdf_name, out_dir=CONVERTED_DIR, dpi=300):
    """Convert EVERY page of a PDF to its own PNG.

    Returns a list of PNG paths in page order, e.g.
    stack.pdf (3 pages) -> [stack_p1.png, stack_p2.png, stack_p3.png]
    """
    pdf_path = resolve_path(pdf_name)
    stem = pdf_path.stem                       # "stack.pdf" -> "stack"

    #make sure it exists
    out_dir.mkdir(parents=True, exist_ok=True)

    png_paths = []

    with pymupdf.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            out_path = out_dir / f"{stem}_p{page_num}.png"
            pix = page.get_pixmap(dpi=dpi)    # render the page to pixels
            pix.save(out_path)
            png_paths.append(out_path)

    return png_paths


def read_image(path):
    img = cv2.imread(str(path))             
    if img is None:
        raise FileNotFoundError(f"Could not load image: {path}")
    return img


def load_pages(file_names):
    """Load any mix of PDFs and images into ONE flat list of pages.

    file_names: a list like ["stack.pdf"] or ["p1.png", "p2.png"]
                (a single name also works)

    Returns a list of (source, image) tuples, in upload order, e.g.
    [("stack.pdf p1", img), ("stack.pdf p2", img), ("x.png", img)]
    """
    # Allow load_pages("blank_01.pdf") as a shortcut for a one-item list
    if isinstance(file_names, (str, Path)):
        file_names = [file_names]

    pages = []

    for file_name in file_names:
        name = Path(file_name).name
        suffix = Path(file_name).suffix.lower()   

        if suffix == ".pdf":
            # One PDF can hold many pages -> add each one
            for page_num, png_path in enumerate(image_converter(file_name), start=1):
                pages.append((f"{name} p{page_num}", read_image(png_path)))

        elif suffix in IMAGE_EXTS:
            # An image file is always exactly one page
            pages.append((name, read_image(resolve_path(file_name))))

        else:
            raise ValueError(f"Unsupported file type: {suffix} ({name})")

    return pages


# ---------- grayscale ----------

def to_gray(img):
    """BGR color image (h, w, 3) -> grayscale (h, w)."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


# ---------- rotate upright ----------

def rotate_upright(gray):
    """Rotate a grayscale page so the form reads normally.
    Tall image -> turn 90 degrees.
    More ink in the bottom strip than the top -> upside down -> turn 180.
    """
    h, w = gray.shape

    if h > w:
        gray = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
        h, w = gray.shape                      # height and width swapped

    strip = h // 7                             # ~14% of the height
    top = gray[:strip, :]                      # first `strip` rows, all columns
    bottom = gray[-strip:, :]                  # last `strip` rows, all columns

    # Lower mean = darker = more ink (0 = black, 255 = white)
    if bottom.mean() < top.mean():
        gray = cv2.rotate(gray, cv2.ROTATE_180)

    return gray


# -------- threshold ----------

def threshold(gray):
    """Grayscale -> pure black/white. INK = WHITE (255), paper = black (0).

    Otsu picks the cutoff automatically from the image, so scans that are
    lighter or darker still split cleanly. INV flips it so ink is white,
    because findContours looks for white shapes.
    """
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


# ---------- Step 5: find the table ----------
MIN_TABLE_FRACTION = 0.2


def find_table_corners(binary):
    """Find the table's 4 corners on a thresholded page (ink = white).

    1. Find the outline of every white shape.
    2. The biggest one is the table's thick outer border.
    3. Wrap the smallest (possibly tilted) box around it. This treats the
       table as a full rectangle - it fills in the missing corner next to
       "min" - so we get 4 clean corners.

    Returns a (4, 2) float32 array of (x, y) corners, in NO particular order.
    """
    # RETR_EXTERNAL = outermost shapes only (the table, not every cell inside)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No shapes found on the page - is it blank?")

    table = max(contours, key=cv2.contourArea)    # find the bigest shape

    page_area = binary.shape[0] * binary.shape[1]
    if cv2.contourArea(table) < MIN_TABLE_FRACTION * page_area:
        raise ValueError("Biggest shape is too small to be the table - table not found")

    box = cv2.minAreaRect(table)     # create the box over the table
    corners = cv2.boxPoints(box)     # the box's 4 corner points
    return corners





"""Debug picture: the found box in red, its corners in green."""
def draw_corners(gray, corners):
    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)   
    pts = corners.astype(np.int32).reshape(-1, 1, 2) 
    cv2.polylines(color, [pts], isClosed=True, color=(0, 0, 255), thickness=5)
    for x, y in corners:
        cv2.circle(color, (int(x), int(y)), 15, (0, 255, 0), -1)
    return color




def order_corners(corners):
    """Put 4 corner points in a fixed order:
    top-left, top-right, bottom-right, bottom-left (clockwise).

    (x grows right, y grows down):
      x + y  -> smallest = top-left,  biggest = bottom-right
      y - x  -> smallest = top-right, biggest = bottom-left
    """
    corners = np.asarray(corners, dtype=np.float32).reshape(4, 2)

    s = corners.sum(axis=1)                 # x + y for each point
    d = np.diff(corners, axis=1).ravel()    # y - x for each point

    return np.array([
        corners[np.argmin(s)],   # top-left
        corners[np.argmin(d)],   # top-right
        corners[np.argmax(s)],   # bottom-right
        corners[np.argmax(d)],   # bottom-left
    ], dtype=np.float32)


# ---------- straighten the table ----------

def table_size(corners):
    """Measure the table's (width, height) in pixels from its 4 ORDERED corners.

    Averages the two opposite edges, so a slight tilt doesn't matter.
    """
    tl, tr, br, bl = corners
    width = (np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2
    height = (np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2
    return int(round(width)), int(round(height))


def warp_table(gray, corners):
    """Cut the table out of the page and straighten it.

    gray:    the upright GRAYSCALE page (not the threshold image -
             gray keeps faint marks; thresholds the table itself)
    corners: 4 ORDERED corners (TL, TR, BR, BL) from order_corners

    Returns a new image containing only the table, at its measured size (NumPy Array).
    """
    w, h = table_size(corners)

    # Where each corner should land in the new image - SAME order as corners
    dst = np.array([
        [0, 0],            # top-left
        [w - 1, 0],        # top-right
        [w - 1, h - 1],    # bottom-right
        [0, h - 1],        # bottom-left
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(corners, dst)   # the "how to move pixels" recipe
    return cv2.warpPerspective(gray, matrix, (w, h))     # size is (width, height)!


# ---------- normalized the table ----------

def normalize_table(table, page):
    """Resize a warped table to its page's exact stored size (layout.PAGE_SIZES).
    """

    return cv2.resize(table, PAGE_SIZES[page])

# ---------- Pipeline: run all prep steps on every page ----------

def debug_name(source, step):
    """
    ("blank_01.pdf p1", "upright") -> "blank_01_pdf_p1_upright.png"
    """
    return source.replace(".", "_").replace(" ", "_") + f"_{step}.png"


def prepare_pages(file_names, debug_dir=None):
    """Load every page and run the prep steps on it.

    file_names: list of PDFs / images (or a single name), in upload order
    debug_dir:  None (default) -> keep everything in memory, save nothing
                a folder       -> also save each page's result there to look at

    Returns a list of (source, page, table) tuples, in upload order:
        source  "stack.pdf p1"  - where the page came from
        page    1 or 2          - which COPUS page (0-30 or 30-50 min)
        table   the straight table, exactly PAGE_SIZES[page]
    """
    if debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)

    prepared = []

    for source, img in load_pages(file_names):
        gray = to_gray(img)
        upright = rotate_upright(gray)
        binary = threshold(upright)

        corners = find_table_corners(binary)
        corners = order_corners(corners)
        table = warp_table(upright, corners) 

        try:
            page = identify_page(table)
        except ValueError as e:
            # Same error, but with the page's label so the user knows WHICH page
            raise ValueError(f"{source}: {e}") from e

        table = normalize_table(table, page)

        if debug_dir is not None:
            cv2.imwrite(str(debug_dir / debug_name(source, "upright")), upright)
            cv2.imwrite(str(debug_dir / debug_name(source, "thresh")), binary)
            cv2.imwrite(str(debug_dir / debug_name(source, "border")), draw_corners(upright, corners))
            cv2.imwrite(str(debug_dir / debug_name(source, "warped")), table)
        prepared.append((source, page, table))

    return prepared




# ---------- Manual check ----------

if __name__ == "__main__":
    # Run the whole prep pipeline and save each page's result to out/ to look at
    pages = prepare_pages(["blank_01.pdf", "blank_02.pdf"], debug_dir=OUT_DIR)

    for source, page, table in pages:
        print(source,"-> page", page, table.shape)