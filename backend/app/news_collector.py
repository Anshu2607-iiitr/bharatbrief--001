
import feedparser
import re
import httpx

from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime


PIB_RSS_URL = "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3"

IST = ZoneInfo("Asia/Kolkata")


def extract_pib_article(article_url):
    try:
        response = httpx.get(
            article_url,
            timeout=30,
            follow_redirects=True
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        page_text = soup.get_text(" ", strip=True)

        date_match = re.search(
            r"प्रविष्टि तिथि:\s*(\d{1,2}\s+[A-Z]{3}\s+\d{4}\s+\d{1,2}:\d{2}\s*[AP]M)",
            page_text,
            re.IGNORECASE
        )

        published_date = None

        if date_match:
            try:
                date_text = date_match.group(1)

                date_value = datetime.strptime(
                    date_text,
                    "%d %b %Y %I:%M%p"
                )

                published_date = date_value.replace(
                    tzinfo=IST
                ).isoformat()

            except ValueError:
                pass

        content_selectors = [
            "#ContentPlaceHolder1_lblContent",
            "#ContentPlaceHolder1_divContent",
            ".innner-page-main-about-us-content-right-part",
            ".content-area",
            "article",
            "main"
        ]

        content_element = None

        for selector in content_selectors:
            content_element = soup.select_one(selector)

            if content_element and len(
                content_element.get_text(strip=True)
            ) > 200:
                break

            content_element = None

        if content_element is None:
            candidates = soup.find_all("div")

            candidates = sorted(
                candidates,
                key=lambda element: len(
                    element.get_text(strip=True)
                ),
                reverse=True
            )

            for element in candidates:
                text = element.get_text(" ", strip=True)

                if len(text) > 500:
                    content_element = element
                    break

        content = ""

        if content_element:
            for unwanted in content_element.select(
                "script, style, nav, footer, header, button, form"
            ):
                unwanted.decompose()

            paragraphs = []

            for paragraph in content_element.find_all(
                ["p", "h1", "h2", "h3", "li"]
            ):
                text = paragraph.get_text(" ", strip=True)

                if len(text) > 20:
                    paragraphs.append(text)

            content = "\n\n".join(paragraphs)

            if not content:
                content = content_element.get_text(
                    "\n",
                    strip=True
                )

        content = re.sub(
            r"\n{3,}",
            "\n\n",
            content
        ).strip()

        return {
            "published_date": published_date,
            "content": content
        }

    except Exception as error:
        print("Article extraction failed:", article_url, error)

        return {
            "published_date": None,
            "content": ""
        }


def fetch_pib_news(limit=20):

    response = httpx.get(
        PIB_RSS_URL,
        timeout=30,
        follow_redirects=True
    )

    response.raise_for_status()

    feed = feedparser.parse(response.content)

    news_list = []

    for entry in feed.entries[:limit]:

        title = entry.get("title", "").strip()
        article_url = entry.get("link", "")

        if not title or not article_url:
            continue

        description = entry.get("summary", "")

        clean_description = BeautifulSoup(
            description,
            "html.parser"
        ).get_text(" ", strip=True)

        article_data = extract_pib_article(article_url)

        published_date = article_data["published_date"]

        if not published_date:
            rss_date = entry.get("published")

            if rss_date:
                try:
                    rss_datetime = parsedate_to_datetime(
                        rss_date
                    )

                    if rss_datetime.tzinfo is None:
                        rss_datetime = rss_datetime.replace(
                            tzinfo=IST
                        )

                    published_date = rss_datetime.isoformat()

                except (TypeError, ValueError):
                    published_date = None

        news = {
            "id": entry.get("id") or entry.get("guid") or article_url,
            "title": title,
            "description": clean_description,
            "content": article_data["content"],
            "url": article_url,
            "published_date": published_date,
            "source": "Press Information Bureau"
        }

        news_list.append(news)

    def get_sort_timestamp(item):
        try:
            if item["published_date"]:
                return datetime.fromisoformat(
                    item["published_date"]
                ).timestamp()

        except (ValueError, TypeError):
            pass

        return 0

    news_list.sort(
        key=get_sort_timestamp,
        reverse=True
    )

    return news_list


if __name__ == "__main__":

    try:
        news = fetch_pib_news()

        print(f"\nTotal news collected: {len(news)}")

        for index, item in enumerate(news, start=1):

            print("\n", index, item["title"])
            print("Date:", item["published_date"])
            print("Content length:", len(item["content"]))
            print("Content preview:", item["content"][:300])
            print("Link:", item["url"])

    except Exception as error:
        print("News collection failed:", error)
