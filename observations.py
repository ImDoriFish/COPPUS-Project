"""
One observation = one COPUS page 1 (0-30 min) + one page 2 (30-50 min).
Pages come in upload order. The two pages of an observation must be
NEXT TO EACH OTHER, in either order (A1 A2 or A2 A1). Mixing observations
(A1 B1 A2 B2) or leaving a page without its partner is an error.
"""

def group_observations(pages): 
    """Pair each page 1 with the page 2 next to it.

    pages: the list from prepare_pages, in upload order:
           [(source, page, table), ...]   e.g. ("filled_page.pdf p1", 1, table)

    Returns a list of observations, each a pair (page 1 item, page 2 item),
    always with page 1 first.

    Raises ValueError (naming the page) if a page has no partner or two
    neighbours aren't one page 1 + one page 2.
    """

    observation = []


        #If there is a page after the current page to pair it
        if i + 1 >= len(pages):
            source = pages[i][0]
            raise ValueError(f"{source}: no matching page - upload both pages of each observation together")

        # (source, page, table)
        a = pages[i] # either page 1 or 2
        b = pages[i + 1] #also page 1 or 2
        a_page_number = a[1]
        b_page_number = b[1]

        if {a_page_number, b_page_number} == {1, 2}:
            if a_page_number == 1: #checking if the first page is page 1
                observation.append((a, b)) # insert if the right order
            else:
                observation.append((b, a)) #flip if the order is wrong then insert
        else:
            raise ValueError(
                f"{a[0]} (page {a_page_number}) and {b[0]} (page {b_page_number}) are not a page 1 + page 2 pair - "
                "keep each observation's two pages next to each other")

    return observation