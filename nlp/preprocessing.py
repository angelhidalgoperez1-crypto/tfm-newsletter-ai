import re

def basic_preprocess(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
