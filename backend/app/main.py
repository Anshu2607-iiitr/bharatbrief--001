
import base64
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.database import test_connection, create_tables, engine
from backend.app.models import News, TranslationCache
from backend.app.news_service import save_pib_news
from backend.app.category_classifier import CATEGORIES, get_category_string
from backend.app.related_news import get_related_news
from backend.app.auth import router as auth_router

from backend.app.translation_service import (
    SUPPORTED_LANGUAGES,
    translate_text as translate_service_text,
    translate_article
)

from backend.app.tts_service import generate_long_speech
from backend.app.chat_service import generate_chat_response

from backend.app.podcast_service import (
    generate_podcast_script,
    generate_podcast_audio,
    SUPPORTED_PODCAST_LANGUAGES
)


IST = ZoneInfo("Asia/Kolkata")

COLLECTION_INTERVAL_MINUTES = 30
RETENTION_DAYS = 30
MAX_NEWS_RECORDS = 500

# On Vercel the app only runs while handling a request, so the in-process
# scheduler can't work there. News collection is triggered by calling
# GET /cron/collect-news instead (cron-job.org every 30 min + Vercel daily cron).
RUNNING_ON_VERCEL = bool(os.getenv("VERCEL"))
CRON_SECRET = os.getenv("CRON_SECRET")


class TranslationRequest(BaseModel):
    text: str
    source_language: str = "en-IN"
    target_language: str = "hi-IN"


class ChatRequest(BaseModel):
    message: str
    language_code: str = "hi-IN"


class PodcastRequest(BaseModel):
    categories: list[str] = Field(default_factory=list)
    language_code: str = "hi-IN"
    duration: int = Field(default=5, ge=1, le=15)


scheduler = BackgroundScheduler(timezone=IST)


app = FastAPI(
    title="Bharat Brief",
    description="AI-powered multilingual news platform",
    version="1.0.0"
)

# Frontend URL(s) allowed to call this API directly, comma-separated.
# On Vercel the frontend forwards /api/* to the backend, so this is optional.
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


def generate_short_description(description, content, max_length=350):

    text = description or content or ""

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "Read the official PIB release for more information."

    sentences = re.split(r"(?<=[.!?।])\s+", text)

    result = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        if len(result) + len(sentence) > max_length:
            break

        result = (result + " " + sentence).strip()

        if len(result) >= 180:
            break

    if not result:
        result = text[:max_length].rsplit(" ", 1)[0]

    if len(result) > max_length:
        result = result[:max_length].rsplit(" ", 1)[0]

    if len(result) < len(text):
        result = result.rstrip(" .") + "..."

    return result


def cleanup_old_news():

    with Session(engine) as session:

        cutoff_date = datetime.now(IST) - timedelta(
            days=RETENTION_DAYS
        )

        old_news_count = (
            session.query(News)
            .filter(News.published_date < cutoff_date)
            .delete(synchronize_session=False)
        )

        session.commit()

        remaining_news = (
            session.query(News)
            .order_by(
                News.published_date.desc().nullslast(),
                News.id.desc()
            )
            .all()
        )

        excess_news = remaining_news[MAX_NEWS_RECORDS:]

        for item in excess_news:
            session.delete(item)

        session.commit()

        return {
            "deleted_old_news": old_news_count,
            "deleted_excess_news": len(excess_news),
            "remaining_news": min(
                len(remaining_news),
                MAX_NEWS_RECORDS
            )
        }


def automatic_news_collection():

    try:

        print("\nAutomatic news collection started...")

        result = save_pib_news(limit=20)

        cleanup_result = cleanup_old_news()

        print("News collection completed:", result)
        print("Storage cleanup completed:", cleanup_result)

    except Exception as error:

        print("Automatic news collection failed:", error)


@app.on_event("startup")
def startup():

    create_tables()

    if RUNNING_ON_VERCEL:
        print("Running on Vercel: scheduler disabled, use /cron/collect-news.")
        return

    if not scheduler.running:

        scheduler.add_job(
            automatic_news_collection,
            trigger="interval",
            minutes=COLLECTION_INTERVAL_MINUTES,
            id="pib_news_collection",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            next_run_time=datetime.now(IST)
        )

        scheduler.start()

        print("Bharat Brief scheduler started.")
        print("News collection interval: 30 minutes.")


@app.on_event("shutdown")
def shutdown():

    if scheduler.running:

        scheduler.shutdown(wait=False)

        print("Bharat Brief scheduler stopped.")


@app.get("/")
def home():

    return {
        "message": "Welcome to Bharat Brief",
        "status": "Backend is running successfully"
    }


@app.get("/health")
def health_check():

    return {"status": "healthy"}


@app.get("/test-db")
def test_db():

    try:

        result = test_connection()

        return {
            "status": "success",
            "database": "connected",
            "test_result": result
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/collect-news")
def collect_news():

    try:

        result = save_pib_news(limit=20)

        cleanup_result = cleanup_old_news()

        return {
            "status": "success",
            "message": "PIB news collection completed",
            "results": result,
            "storage_cleanup": cleanup_result
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/cron/collect-news")
def cron_collect_news(authorization: str = Header(default=None)):

    if CRON_SECRET and authorization != f"Bearer {CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:

        result = save_pib_news(limit=20)

        cleanup_result = cleanup_old_news()

        return {
            "status": "success",
            "results": result,
            "storage_cleanup": cleanup_result
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/classify-news")
def classify_existing_news():

    try:

        classified_count = 0
        uncategorized_count = 0

        with Session(engine) as session:

            news_list = (
                session.query(News)
                .filter(
                    (News.category == "Uncategorized")
                    | (News.category.is_(None))
                    | (News.category == "")
                )
                .all()
            )

            for item in news_list:

                category = get_category_string(
                    title=item.title,
                    description=item.description or "",
                    content=item.content or ""
                )

                item.category = category

                if category == "Uncategorized":
                    uncategorized_count += 1
                else:
                    classified_count += 1

            session.commit()

        return {
            "status": "success",
            "total_processed": classified_count + uncategorized_count,
            "classified": classified_count,
            "uncategorized": uncategorized_count
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/reclassify-news")
def reclassify_all_news():

    try:

        processed_count = 0
        changed_count = 0
        classified_count = 0
        uncategorized_count = 0

        with Session(engine) as session:

            news_list = session.query(News).all()

            for item in news_list:

                old_category = item.category or "Uncategorized"

                new_category = get_category_string(
                    title=item.title,
                    description=item.description or "",
                    content=item.content or ""
                )

                item.category = new_category

                processed_count += 1

                if old_category != new_category:
                    changed_count += 1

                if new_category == "Uncategorized":
                    uncategorized_count += 1
                else:
                    classified_count += 1

            session.commit()

        return {
            "status": "success",
            "message": "All news articles reclassified successfully",
            "total_processed": processed_count,
            "categories_changed": changed_count,
            "classified": classified_count,
            "uncategorized": uncategorized_count
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/categories")
def get_categories():

    try:

        with Session(engine) as session:

            news_list = session.query(News.category).all()

            category_counts = {
                category: 0
                for category in CATEGORIES
            }

            category_counts["Uncategorized"] = 0

            for row in news_list:

                stored_categories = row[0] or "Uncategorized"

                for category in stored_categories.split(","):

                    category = category.strip()

                    if category not in category_counts:
                        category_counts[category] = 0

                    category_counts[category] += 1

            return {
                "status": "success",
                "total_categories": len(category_counts),
                "categories": [
                    {
                        "name": category,
                        "article_count": count
                    }
                    for category, count in category_counts.items()
                ]
            }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/storage-status")
def storage_status():

    try:

        with Session(engine) as session:

            total_news = session.query(News).count()

            cutoff_date = datetime.now(IST) - timedelta(
                days=RETENTION_DAYS
            )

            recent_news = (
                session.query(News)
                .filter(News.published_date >= cutoff_date)
                .count()
            )

            old_news = (
                session.query(News)
                .filter(
                    (News.published_date < cutoff_date)
                    | (News.published_date.is_(None))
                )
                .count()
            )

            available_storage = max(
                0,
                MAX_NEWS_RECORDS - total_news
            )

            usage_percentage = round(
                (total_news / MAX_NEWS_RECORDS) * 100,
                2
            )

            return {
                "status": "success",
                "storage": {
                    "total_articles": total_news,
                    "maximum_capacity": MAX_NEWS_RECORDS,
                    "available_slots": available_storage,
                    "usage_percentage": usage_percentage,
                    "articles_within_30_days": recent_news,
                    "articles_older_than_30_days_or_without_date": old_news
                }
            }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/news")
def get_news(
    limit: int = Query(default=20, ge=1, le=100),
    category: str = Query(default=None)
):

    try:

        with Session(engine) as session:

            query = session.query(News)

            if category:

                allowed_categories = list(CATEGORIES.keys()) + [
                    "Uncategorized"
                ]

                if category not in allowed_categories:

                    raise HTTPException(
                        status_code=400,
                        detail="Invalid news category"
                    )

                query = query.filter(
                    News.category.ilike(f"%{category}%")
                )

            news_list = (
                query
                .order_by(
                    News.published_date.desc().nullslast(),
                    News.id.desc()
                )
                .limit(limit)
                .all()
            )

            return {
                "status": "success",
                "total_news": len(news_list),
                "news": [
                    {
                        "id": item.id,
                        "title": item.title,
                        "description": generate_short_description(
                            item.description,
                            item.content
                        ),
                        "url": item.url,
                        "published_date": item.published_date,
                        "source": item.source,
                        "category": item.category
                    }
                    for item in news_list
                ]
            }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/news/timeline")
def get_news_timeline(
    days: int = Query(default=30, ge=1, le=30),
    limit: int = Query(default=100, ge=1, le=500)
):

    try:

        with Session(engine) as session:

            current_time = datetime.now(IST)

            cutoff_date = current_time - timedelta(days=days)

            news_list = (
                session.query(News)
                .filter(
                    News.published_date >= cutoff_date,
                    News.published_date <= current_time
                )
                .order_by(
                    News.published_date.desc(),
                    News.id.desc()
                )
                .limit(limit)
                .all()
            )

            timeline = {}

            for item in news_list:

                if item.published_date is None:
                    continue

                date_key = item.published_date.strftime("%Y-%m-%d")

                if date_key not in timeline:

                    timeline[date_key] = {
                        "date": date_key,
                        "total_news": 0,
                        "news": []
                    }

                timeline[date_key]["total_news"] += 1

                timeline[date_key]["news"].append({
                    "id": item.id,
                    "title": item.title,
                    "description": generate_short_description(
                        item.description,
                        item.content
                    ),
                    "published_date": item.published_date,
                    "source": item.source,
                    "category": item.category,
                    "url": item.url
                })

            return {
                "status": "success",
                "days": days,
                "total_news": len(news_list),
                "total_dates": len(timeline),
                "timeline": list(timeline.values())
            }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/news/{news_id}/related")
def get_related_news_api(
    news_id: int,
    limit: int = Query(default=5, ge=1, le=10)
):

    try:

        related_articles = get_related_news(
            news_id=news_id,
            limit=limit
        )

        if not related_articles:

            with Session(engine) as session:

                exists = session.query(News.id).filter(
                    News.id == news_id
                ).first()

                if not exists:

                    raise HTTPException(
                        status_code=404,
                        detail="News article not found"
                    )

        return {
            "status": "success",
            "current_news_id": news_id,
            "total_related_news": len(related_articles),
            "related_news": [
                {
                    **article,
                    "description": generate_short_description(
                        article.get("description"),
                        article.get("title")
                    )
                }
                for article in related_articles
            ]
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/news/{news_id}")
def get_news_detail(news_id: int):

    try:

        with Session(engine) as session:

            news = session.query(News).filter(
                News.id == news_id
            ).first()

            if news is None:

                raise HTTPException(
                    status_code=404,
                    detail="News article not found"
                )

            return {
                "status": "success",
                "news": {
                    "id": news.id,
                    "title": news.title,
                    "description": generate_short_description(
                        news.description,
                        news.content
                    ),
                    "content": news.content,
                    "url": news.url,
                    "published_date": news.published_date,
                    "source": news.source,
                    "category": news.category
                }
            }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.get("/languages")
def get_supported_languages():

    return {
        "status": "success",
        "total_languages": len(SUPPORTED_LANGUAGES),
        "languages": [
            {
                "name": name,
                "code": code
            }
            for name, code in SUPPORTED_LANGUAGES.items()
        ]
    }


@app.post("/translate")
def translate_text_api(request: TranslationRequest):

    try:

        if not request.text.strip():

            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )

        if request.source_language not in SUPPORTED_LANGUAGES.values():

            raise HTTPException(
                status_code=400,
                detail="Unsupported source language"
            )

        if request.target_language not in SUPPORTED_LANGUAGES.values():

            raise HTTPException(
                status_code=400,
                detail="Unsupported target language"
            )

        translated_text = translate_service_text(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language
        )

        return {
            "status": "success",
            "original_text": request.text,
            "translated_text": translated_text,
            "source_language": request.source_language,
            "target_language": request.target_language
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/news/{news_id}/translate")
def translate_news_article(
    news_id: int,
    target_language: str = Query(...)
):

    try:

        if target_language not in SUPPORTED_LANGUAGES.values():

            raise HTTPException(
                status_code=400,
                detail="Unsupported target language"
            )

        with Session(engine) as session:

            article = session.query(News).filter(
                News.id == news_id
            ).first()

            if article is None:

                raise HTTPException(
                    status_code=404,
                    detail="News article not found"
                )

            cached_translation = session.query(
                TranslationCache
            ).filter(
                TranslationCache.news_id == news_id,
                TranslationCache.target_language == target_language
            ).first()

            if cached_translation:

                translated_article = {
                    "title": cached_translation.title,
                    "description": cached_translation.description,
                    "content": cached_translation.content,
                    "target_language": target_language
                }

                return {
                    "status": "success",
                    "message": "Translation fetched from cache",
                    "cached": True,
                    "news_id": article.id,
                    "original_language": "en-IN",
                    "target_language": target_language,
                    "original_article": {
                        "title": article.title,
                        "description": article.description,
                        "content": article.content
                    },
                    "translated_article": translated_article
                }

            translated_article = translate_article(
                article=article,
                target_language=target_language
            )

            new_cache = TranslationCache(
                news_id=article.id,
                target_language=target_language,
                title=translated_article.get("title"),
                description=translated_article.get("description"),
                content=translated_article.get("content")
            )

            session.add(new_cache)
            session.commit()

            return {
                "status": "success",
                "message": "Article translated and saved in cache",
                "cached": False,
                "news_id": article.id,
                "original_language": "en-IN",
                "target_language": target_language,
                "original_article": {
                    "title": article.title,
                    "description": article.description,
                    "content": article.content
                },
                "translated_article": translated_article
            }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ==========================================
# TEXT TO SPEECH - FULL ARTICLE AUDIO
# ==========================================

@app.post("/news/{news_id}/listen")
def listen_to_news(
    news_id: int,
    target_language: str = Query(default="en-IN")
):

    try:

        if target_language not in SUPPORTED_LANGUAGES.values():

            raise HTTPException(
                status_code=400,
                detail="Unsupported language"
            )

        with Session(engine) as session:

            article = session.query(News).filter(
                News.id == news_id
            ).first()

            if article is None:

                raise HTTPException(
                    status_code=404,
                    detail="News article not found"
                )

            if target_language == "en-IN":

                title = article.title or ""
                description = article.description or ""
                content = article.content or ""

            else:

                cached_translation = session.query(
                    TranslationCache
                ).filter(
                    TranslationCache.news_id == news_id,
                    TranslationCache.target_language == target_language
                ).first()

                if cached_translation is None:

                    raise HTTPException(
                        status_code=404,
                        detail="Please translate this article first"
                    )

                title = cached_translation.title or ""
                description = cached_translation.description or ""
                content = cached_translation.content or ""

            text_to_speak = "\n\n".join(
                part.strip()
                for part in [title, description, content]
                if part and part.strip()
            )

        if not text_to_speak.strip():

            raise HTTPException(
                status_code=400,
                detail="Article has no content to read"
            )

        audio_data = generate_long_speech(
            text=text_to_speak,
            language_code=target_language
        )

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=news_audio.mp3"
            }
        )

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ==========================================
# AI CHATBOT - MULTILINGUAL TEXT TO TEXT
# ==========================================

@app.post("/chat")
def chat_with_ai(request: ChatRequest):

    try:

        if not request.message or not request.message.strip():

            raise HTTPException(
                status_code=400,
                detail="Message cannot be empty"
            )

        if request.language_code not in SUPPORTED_LANGUAGES.values():

            raise HTTPException(
                status_code=400,
                detail="Unsupported language"
            )

        chatbot_response = generate_chat_response(
            message=request.message.strip(),
            language_code=request.language_code
        )

        return {
            "status": "success",
            "message": request.message,
            "language_code": request.language_code,
            "response": chatbot_response
        }

    except HTTPException:
        raise

    except Exception as error:

        print("Chatbot error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to generate chatbot response. Please try again."
        )


# ==========================================
# AI DAILY NEWS PODCAST
# ==========================================

@app.post("/podcast/generate")
def generate_daily_podcast(request: PodcastRequest):

    try:

        if request.language_code not in SUPPORTED_PODCAST_LANGUAGES:

            raise HTTPException(
                status_code=400,
                detail="Podcast voice is not available for this language"
            )

        allowed_categories = list(CATEGORIES.keys()) + [
            "Uncategorized"
        ]

        for category in request.categories:

            if category not in allowed_categories:

                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}"
                )

        with Session(engine) as session:

            query = session.query(News)

            if request.categories:

                category_conditions = [
                    News.category.ilike(f"%{category}%")
                    for category in request.categories
                ]

                from sqlalchemy import or_
                query = query.filter(or_(*category_conditions))

            articles = (
                query
                .order_by(
                    News.published_date.desc().nullslast(),
                    News.id.desc()
                )
                .limit(20)
                .all()
            )

            podcast_articles = []

            for article in articles:

                podcast_articles.append({
                    "id": article.id,
                    "title": article.title or "",
                    "description": article.description or "",
                    "content": article.content or "",
                    "url": article.url,
                    "source": article.source,
                    "category": article.category,
                    "published_date": (
                        article.published_date.isoformat()
                        if article.published_date else None
                    )
                })

        if not podcast_articles:

            raise HTTPException(
                status_code=404,
                detail="No news articles found for selected categories"
            )

        print("\nGenerating podcast script...")

        script = generate_podcast_script(
            articles=podcast_articles,
            language_code=request.language_code,
            duration=request.duration
        )

        print("\nGenerating podcast audio...")

        audio_data = generate_podcast_audio(
            script=script,
            language_code=request.language_code
        )

        audio_base64 = base64.b64encode(
            audio_data
        ).decode("utf-8")

        return {
            "status": "success",
            "message": "Podcast generated successfully",
            "language_code": request.language_code,
            "duration_minutes": request.duration,
            "transcript": script,
            "audio_base64": audio_base64,
            "audio_mime_type": "audio/mpeg",
            "total_articles": len(podcast_articles),
            "sources": [
                {
                    "id": article["id"],
                    "title": article["title"],
                    "url": article["url"],
                    "source": article["source"],
                    "category": article["category"],
                    "published_date": article["published_date"]
                }
                for article in podcast_articles
            ]
        }

    except HTTPException:
        raise

    except Exception as error:

        print("Podcast generation error:", error)

        raise HTTPException(
            status_code=500,
            detail="Unable to generate podcast. Please try again."
        )
