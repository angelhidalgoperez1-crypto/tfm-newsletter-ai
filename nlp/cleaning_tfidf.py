import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

nlp_es = spacy.load("es_core_news_sm")
nlp_en = spacy.load("en_core_web_sm")

def clean_for_tfidf(text, lang):

    if lang == "es":
        doc = nlp_es(text)
    elif lang == "en":
        doc = nlp_en(text)
    else:
        return ""

    tokens = [
        token.lemma_.lower()
        for token in doc
        if token.is_alpha and not token.is_stop
    ]

    return " ".join(tokens)

def compute_tfidf(texts):
    vectorizer = TfidfVectorizer(
        max_df=0.9,
        min_df=5,
        ngram_range=(1, 2)
    )
    X = vectorizer.fit_transform(texts)
    return X, vectorizer
