
import re
import math



CATEGORIES = {
    "Politics & Governance": [
        "prime minister", "chief minister", "lok sabha",
        "rajya sabha", "parliament", "cabinet decision",
        "government policy", "governance reform",
        "election commission", "public administration",
        "union cabinet", "presidential address",
        "ministry of parliamentary affairs",
        "vice-president", "vice president",
        "national unity pledge", "rashtriya ekta diwas",
        "legislative department", "iipa",
        "inclusive capacity building", "government officials",
        "state governments", "public welfare",
        "my bharat", "youth campaign","ministry of social justice",
"social justice and empowerment",
"government initiative",
"public welfare",
"empowerment of persons with disabilities"
    ],

    "Agriculture": [
        "agriculture", "agricultural", "farmer",
        "farmers", "crop production", "crop yield",
        "minimum support price", "msp",
        "irrigation", "fertilizer", "fertiliser",
        "horticulture", "agricultural research",
        "kisan", "dairy farming", "livestock"
    ],

    "Sports": [
        "sports", "sportsperson", "cricket",
        "football", "hockey", "badminton",
        "olympics", "olympic games", "paralympics",
        "asian games", "world cup", "sports tournament",
        "sports championship", "sports federation",
        "athlete", "medal winner"
    ],

    "Economy": [
        "gross domestic product", "gdp",
        "inflation", "reserve bank of india",
        "rbi monetary policy", "fiscal deficit",
        "union budget", "income tax",
        "customs duty", "foreign trade",
        "foreign investment", "export growth",
        "import duty", "economic growth",
        "stock market", "banking sector",
        "financial inclusion", "tax revenue",
        "tax devolution", "capital spending",
        "equity share", "share capital",
        "shareholding", "acquisition",
        "merger", "cci approves",
        "competition commission of india",
        "infrastructure investment", "epfo",
        "provident fund", "corporate transaction",
        "financial transaction", "renewables","traditional artisans",
"artisan products",
"traditional craftsmanship",
"economic empowerment",
"livelihood programme",
"market their products",
"handicrafts",
"craft demonstrations"
    ],

    "Science & Technology": [
        "artificial intelligence", "machine learning",
        "space research", "indian space research organisation",
        "isro", "drdo research", "quantum technology",
        "semiconductor", "supercomputer",
        "scientific research", "satellite launch",
        "space mission", "robotics",
        "technological innovation", "scientist"
    ],

    "Defence": [
        "indian army", "indian navy",
        "indian air force", "armed forces",
        "defence ministry", "defense ministry",
        "military exercise", "missile system",
        "fighter aircraft", "warship",
        "border security", "defence production",
        "defense production", "military operation",
        "naval exercise", "air force",
        "air chief marshal", "maritime security",
        "naval security", "military service"
    ],

    "Education": [
        "education policy", "school education",
        "higher education", "university",
        "universities", "scholarship",
        "student examination", "entrance examination",
        "educational institution", "curriculum",
        "teacher training", "literacy",
        "academic research", "vidyanjali",
        "education ministry", "youth programmes",
        "youth programme", "student cadets",
        "capacity building"
    ],

    "Health": [
        "public health", "healthcare",
        "health ministry", "medical research",
        "health services", "hospital",
        "vaccination", "vaccine",
        "infectious disease", "disease prevention",
        "medical treatment", "nutrition programme",
        "ayush", "health mission"
    ],

    "Environment": [
        "climate change", "global warming",
        "air pollution", "water pollution",
        "environmental protection", "wildlife conservation",
        "biodiversity", "forest conservation",
        "renewable energy", "solar energy",
        "carbon emission", "water conservation",
        "ecosystem", "environment ministry",
        "clean delhi", "cleanliness",
        "environmental cleanliness"
    ],

    "International Relations": [
        "foreign affairs", "foreign minister",
        "foreign secretary", "bilateral relations",
        "diplomatic relations", "international cooperation",
        "united nations", "international summit",
        "g20 summit", "brics summit",
        "ambassador", "diplomatic mission",
        "international treaty", "foreign policy",
        "bimstec", "maritime security exercise",
        "regional cooperation"
    ]
}


MAX_CATEGORIES = 3
MIN_CONFIDENCE = 35
MIN_RELATIVE_SCORE = 0.45


def normalize_text(text):

    if not text:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def count_keyword_matches(text, keywords):

    score = 0

    for keyword in keywords:

        keyword = normalize_text(keyword)

        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"

        if re.search(pattern, text):
            score += 1

    return score


def get_category_scores(title="", description="", content=""):

    title = normalize_text(title)
    description = normalize_text(description)
    content = normalize_text(content)

    category_scores = {}

    for category, keywords in CATEGORIES.items():

        title_score = count_keyword_matches(title, keywords)
        description_score = count_keyword_matches(
            description, keywords
        )
        content_score = count_keyword_matches(content, keywords)

        raw_score = (
            title_score * 5
            + description_score * 3
            + min(content_score, 5)
        )

        if raw_score > 0:

            confidence = 100 * (
                1 - math.exp(-raw_score / 5)
            )

            category_scores[category] = round(confidence, 2)

    return dict(
        sorted(
            category_scores.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )


def classify_news(title="", description="", content=""):

    scores = get_category_scores(
        title=title,
        description=description,
        content=content
    )

    if not scores:
        return []

    highest_score = max(scores.values())

    selected_categories = []

    for category, confidence in scores.items():

        if len(selected_categories) >= MAX_CATEGORIES:
            break

        if confidence < MIN_CONFIDENCE:
            continue

        if confidence < highest_score * MIN_RELATIVE_SCORE:
            continue

        selected_categories.append(category)

    return selected_categories


def get_category_string(title="", description="", content=""):

    categories = classify_news(
        title=title,
        description=description,
        content=content
    )

    if not categories:
        return "Uncategorized"

    return ", ".join(categories)
