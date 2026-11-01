
from datetime import timedelta, timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models import News


def get_related_news(news_id, limit=5):
    db = Session(engine)

    try:
        current_news = db.query(News).filter(
            News.id == news_id
        ).first()

        if not current_news:
            return []

        current_date = current_news.published_date

        if not current_date:
            return []

        if current_date.tzinfo is None:
            current_date = current_date.replace(
                tzinfo=timezone.utc
            )

        start_date = current_date - timedelta(days=30)

        articles = db.query(News).filter(
            News.id != news_id,
            News.published_date >= start_date,
            News.published_date <= current_date
        ).all()

        if not articles:
            return []

        current_text = " ".join(filter(None, [
            current_news.title,
            current_news.description,
            current_news.content
        ]))

        documents = [current_text]

        for article in articles:
            article_text = " ".join(filter(None, [
                article.title,
                article.description,
                article.content
            ]))

            documents.append(article_text)

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 2)
        )

        tfidf_matrix = vectorizer.fit_transform(documents)

        similarity_scores = cosine_similarity(
            tfidf_matrix[0:1],
            tfidf_matrix[1:]
        ).flatten()

        results = []

        for i, score in enumerate(similarity_scores):
            if score <= 0:
                continue

            article = articles[i]

            results.append({
                "id": article.id,
                "title": article.title,
                "description": article.description,
                "url": article.url,
                "published_date": article.published_date,
                "source": article.source,
                "category": article.category,
                "similarity_score": round(float(score), 4)
            })

        results.sort(
            key=lambda x: x["similarity_score"],
            reverse=True
        )

        return results[:limit]

    except Exception as e:
        print("Related news error:", str(e))
        return []

    finally:
        db.close()
