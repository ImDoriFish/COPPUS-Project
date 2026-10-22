import cv2
import numpy as np


from image_prep import (load_pages, to_gray, rotate_upright, threshold,
                        find_table_corners, order_corners, warp_table)
"""One-time tool: measure where the grid lines are on the blank forms.

Run it once:   python measure_grid.py
It prints the x positions of the vertical lines and the y positions of the
horizontal lines for each page. Copy those lists into layout.py.
"""



# How long the "stick" is: ink shorter than this (text, specks) gets erased,
# longer straight lines stay. (Need tunning)
STICK_LENGTH = 100

# A row (or column) counts as a line if more than this fraction of it is white.
MIN_FILL = 0.3 

# Rows/columns this close together belong to the same (thick) line.
MERGE_GAP = 3

# How many lines each page should have - used to warn if something is off.
EXPECTED = {
    1: {"horizontal": 20, "vertical": 33},
    2: {"horizontal": 13, "vertical": 33},
}


def find_lines(binary, direction):
    """Return the positions of the grid lines in one direction.

    binary:    thresholded table(wrapped), ink = white (255)
    direction: "horizontal" -> returns y positions (one per horizontal line)
               "vertical"   -> returns x positions (one per vertical line)
    """

    #---------------erase everything that isn't a long straight line---------------------
    if direction == "horizontal":
        stick = cv2.getStructuringElement(cv2.MORPH_RECT, (STICK_LENGTH, 1)) #stick is the structural element (kernel), it defines the shape of the neighborhood pixel like a tempelate shape.
    else:
        stick = cv2.getStructuringElement(cv2.MORPH_RECT, (1, STICK_LENGTH))

    #Modify the threshold image so that the kernel fit on the line (basicly modifying the image so it only contain the grid line (numpy Array))
    only_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, stick)

    #--------------count white pixels in every row (or column)----------------------
    if direction == "horizontal":
        sum_of_white_pixel = only_lines.sum(axis=1) / 255 # calculate the sum of each row
        full_length = binary.shape[1] # Since shape(height, width), and get the table acutal width
    else:
        sum_of_white_pixel = only_lines.sum(axis=0) / 255 # calculate the sum of each column
        full_length = binary.shape[0] # Since shape(height, width), and get the table acutal height

    line_pixels_location = np.where(sum_of_white_pixel > MIN_FILL * full_length)[0] # where return tuple (since only 1 argument pass in).

    # --------------merge neighbours (one thick line -> one position) ----------------

    group_line = [] #a list of list of line 
    for p in line_pixels_location:
        # Check if the list is not empty and if the current line belong in a group by checking the difference 
        #between the current line with the most recent added line in the most added group [-1][-1] means that.
        if group_line and  p - group_line[-1][-1] <= MERGE_GAP:
            group_line[-1].append(p)  # right next to the previous one: same line
        else:
            group_line.append([p])          # a gap: a new line starts

    # Merge all the group together by finding the average per each group and set it as the pixel location for new lines.
    merged_line = []
    for group in group_line:
        average = np.mean(group)
        rounded = round(average)
        position = int(rounded)
        merged_line.append(position)

    return merged_line

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
