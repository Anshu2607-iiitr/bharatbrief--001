
from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models import News
from backend.app.news_collector import fetch_pib_news
from backend.app.category_classifier import get_category_string


def save_pib_news(limit=20):

    news_list = fetch_pib_news(limit=limit)

    saved_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    categorized_count = 0

    with Session(engine) as session:

        try:
            for item in news_list:

                if not item.get("url") or not item.get("title"):
                    failed_count += 1
                    continue

                published_date = None

                if item.get("published_date"):
                    try:
                        published_date = datetime.fromisoformat(
                            item["published_date"]
                        )
                    except (ValueError, TypeError):
                        published_date = None

                existing_news = session.query(News).filter_by(
                    url=item["url"]
                ).first()

                if existing_news:

                    updated = False

                    if item.get("content") and not existing_news.content:
                        existing_news.content = item["content"]
                        updated = True

                    if item.get("description") and not existing_news.description:
                        existing_news.description = item["description"]
                        updated = True

                    if not existing_news.published_date and published_date:
                        existing_news.published_date = published_date
                        updated = True

                    if (
                        not existing_news.category
                        or existing_news.category == "Uncategorized"
                    ):

                        category = get_category_string(
                            title=existing_news.title,
                            description=(
                                existing_news.description
                                or item.get("description", "")
                            ),
                            content=(
                                existing_news.content
                                or item.get("content", "")
                            )
                        )

                        if category != "Uncategorized":
                            existing_news.category = category
                            updated = True
                            categorized_count += 1

                    if updated:
                        updated_count += 1
                    else:
                        skipped_count += 1

                    continue

                category = get_category_string(
                    title=item["title"],
                    description=item.get("description", ""),
                    content=item.get("content", "")
                )

                if category != "Uncategorized":
                    categorized_count += 1

                news = News(
                    title=item["title"],
                    description=item.get("description", ""),
                    content=item.get("content", ""),
                    url=item["url"],
                    published_date=published_date,
                    source=item.get(
                        "source",
                        "Press Information Bureau"
                    ),
                    category=category
                )

                session.add(news)
                saved_count += 1

            session.commit()

        except Exception:
            session.rollback()
            raise

    return {
        "total_fetched": len(news_list),
        "saved": saved_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "failed": failed_count,
        "categorized": categorized_count
    }
