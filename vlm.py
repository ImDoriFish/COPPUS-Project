import ollama 
from ollama import ChatResponse
import re
import cv2
# The vision model to use - exact tag, so every machine uses the same one
VLM_MODEL = "qwen3-vl:4b"

def check_vlm(model=VLM_MODEL):
    """Make sure Ollama is running and the model is downloaded. Call ONCE at the start.

    Downloads the model the first time (a few GB), so later runs start straight away.
    Raises RuntimeError with what to do if the Ollama app isn't running.
    """
    installed = []
    try:
        for m in ollama.list().models:
            installed.append(m.model)
    except ConnectionError:
        raise RuntimeError("Ollama is not running - install it from https://ollama.com/download, "
                           "start it, then run again") from None

    if model not in installed:
        print(f"Downloading {model} (first run only, a few GB)...")
        ollama.pull(model)
        print("Done.")


# The question for tally cells. Neutral wording: mentioning "groups of 5" made
COUNT_PROMPT = ("Count the pen lines in this image, including any diagonal line. "
                "Reply with one number only.")

# A count above this is almost certainly a misread -> treat as "needs review"
MAX_COUNT = 10

def ask_vlm(image, prompt, model=VLM_MODEL):
    """Send one picture and a question to the model, return its reply as text.

    image:  a NumPy image (e.g. a crop from extract.inter_crops)
    prompt: the question to ask about it
    """
    status, png = cv2.imencode(".png", image)
    if not status:
        raise ValueError("could not turn the image into a PNG")

    response: ChatResponse = ollama.chat(
        model=model,
        messages=[
            {
                'role': 'user',
                'content': prompt,
                'images': [png.tobytes()],
            }
        ],
        think = False,
        options={"temperature": 0},  
    )

    return response.message.content.strip()

def count_tallies(image, model=VLM_MODEL):
    """Ask the model how many tally lines are in one cell.

    Returns the count as an int, or None if the reply isn't a clean number
    (or is unbelievably large) - None means "needs review", never a guess.
    """
    reply = ask_vlm(image, COUNT_PROMPT, model)
    if not re.fullmatch(r"\d+", reply):               # only digits, nothing else
        return None
    count = int(reply)
    if count > MAX_COUNT:
        return None
    return count

def count_tallies(image, model=VLM_MODEL):
    """Ask the model how many tally lines are in one cell.

    Returns the count as an int, or None if the reply isn't a clean number
    (or is unbelievably large) - None means "needs review", never a guess.
    """
    reply = ask_vlm(image, COUNT_PROMPT, model)
    if not reply.isdigit():
        return None
    count = int(reply)
    if count > MAX_COUNT:
        return None
    return count

    
if __name__ == "__main__":
    check_vlm()
    print(f"Ollama is running and {VLM_MODEL} is ready")

    import sys
    path = sys.argv[1]                                  # the image file given on the command line
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    print("reply:", repr(ask_vlm(image, COUNT_PROMPT)))
    print("count:", count_tallies(image))