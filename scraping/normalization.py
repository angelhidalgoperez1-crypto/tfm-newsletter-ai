from langdetect import detect, LangDetectException

def normalize_article(article):

    content = article["content"]

    article["content_length"] = len(content)
    article["word_count"] = len(content.split())

    try:
        article["language"] = detect(content)
    except LangDetectException:
        article["language"] = "unknown"

    article["is_valid"] = (
        article["word_count"] > 150 and
        article["language"] in ["es", "en"]
    )

    return article
