"""One-time tool: measure where the grid lines are on the blank forms.

Run it once:   python measure_grid.py
It prints the x positions of the vertical lines and the y positions of the
horizontal lines for each page. Copy those lists into layout.py.
"""

from image_prep import (load_pages, to_gray, rotate_upright, threshold,
                        find_table_corners, order_corners, warp_table)
from grid import find_lines


if __name__ == "__main__":
    for source, img in load_pages(["blank_50.pdf", "blank_80.pdf", "blank_110.pdf"]):
        gray = to_gray(img)
        upright = rotate_upright(gray)
        corners = order_corners(find_table_corners(threshold(upright)))
        table = warp_table(upright, corners)

        binary = threshold(table)
        ys = find_lines(binary, "horizontal")
        xs = find_lines(binary, "vertical")

        print(f"\n===== {source}, table {table.shape[1]} x {table.shape[0]} =====")
        print(f"horizontal: {len(ys)} lines")
        print(f"vertical:   {len(xs)} lines")
        print(f"row lines: {ys}")
        print(f"col lines: {xs}")
