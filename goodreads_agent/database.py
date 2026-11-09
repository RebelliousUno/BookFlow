import json
import os
from typing import Any

from hardcover_activities_models import ActivityItem, Book
from neo4j import GraphDatabase

ADD_BOOK_CYPHER = """
MERGE (b:Book {title: $title})
ON CREATE SET 
    b.hardcover_book_link = $hardcover_book_link,
    b.page_count = $page_count,
    b.audio_seconds = $audio_seconds,
    b.description = $description,
    b.image_url = $image_url
ON MATCH SET 
    b.hardcover_book_link = coalesce($hardcover_book_link, b.hardcover_book_link),
    b.page_count = coalesce($page_count, b.page_count),
    b.audio_seconds = coalesce($audio_seconds, b.audio_seconds),
    b.description = coalesce($description, b.description),
    b.image_url = coalesce($image_url, b.image_url)
WITH b, $authors AS authors
UNWIND coalesce(authors, []) AS author_name
MERGE (a:Author {name: author_name})
MERGE (a)-[:WROTE]->(b)
RETURN b.title AS title
"""

GET_BOOK_BY_TITLE = """
MATCH (b:Book {title: $book_title})
OPTIONAL MATCH (a:Author)-[:WROTE]->(b)
RETURN b.title AS title,
       b.hardcover_book_link AS hardcover_book_link,
       b.page_count AS page_count,
       b.audio_seconds AS audio_seconds,
       b.synopsis AS description,
       b.image_url AS image_url,
       collect(a.name) AS authors
"""


GET_LAST_RUN_TIME = """
MATCH (c:Config {name: 'last_run_time'})
RETURN c.value AS last_run_time
"""

SET_LAST_RUN_TIME = """
MERGE (c:Config {name: 'last_run_time'})
SET c.value = $last_run_time
"""

UPDATE_POSTS_AND_ACTIVITIES = """
CREATE (p:Social_Post {
    content: $social_media_post,
    posted_at: datetime()
})
WITH p
UNWIND $activities AS activity
MERGE (u:Goodreads_Update {update_id: toString(activity.id)})
ON CREATE SET
    u.date = activity.created_at,
    u.post_type = activity.event,
    u.content = activity.data_json,
    u.image_url = activity.image_url,
    u.hardcover_book_id = activity.book_id
MERGE (u)-[:PROCESSED_BY]->(p)
WITH p, u, activity
OPTIONAL MATCH (b:Book {hardcover_book_link: activity.hardcover_book_link})
FOREACH (_ IN CASE WHEN b IS NULL THEN [] ELSE [1] END |
    MERGE (u)-[:IS_ABOUT]->(b)
)
RETURN count(DISTINCT u) AS activities_saved
"""


def _activity_database_params(activity: ActivityItem) -> dict[str, Any]:
    book_id = activity.book_id
    return {
        "id": activity.id,
        "created_at": activity.created_at,
        "event": activity.event,
        "data_json": json.dumps(activity.data, ensure_ascii=False),
        "image_url": (
            activity.book.image.url
            if activity.book and activity.book.image
            else None
        ),
        "book_id": book_id,
        "hardcover_book_link": (
            f"https://hardcover.app/books/{book_id}" if book_id is not None else None
        ),
    }


def update_posts_and_activities(
    social_media_post: str, activities: list[ActivityItem]
) -> int:
    """Save a social post, its source activities, and links to known books."""
    activity_params = [_activity_database_params(activity) for activity in activities]

    with driver.session(database=database) as session:
        result = session.run(
            UPDATE_POSTS_AND_ACTIVITIES,
            social_media_post=social_media_post,
            activities=activity_params,
        )
        record = result.single()
        return record["activities_saved"] if record else 0


def get_last_run_time() -> str:
    with driver.session(database=database) as session:
        result = session.run(GET_LAST_RUN_TIME)
        record = result.single()
        if record:
            return record["last_run_time"]
        return None


def set_last_run_time(last_run_time: str):
    with driver.session(database=database) as session:
        session.run(SET_LAST_RUN_TIME, last_run_time=last_run_time)


def get_book_by_title(book_title: str) -> Book | None:
    with driver.session(database=database) as session:
        result = session.run(GET_BOOK_BY_TITLE, book_title=book_title)
        record = result.single()
        if record:
            return Book(
                title=record["title"],
                hardcover_book_link=record["hardcover_book_link"],
                pageCount=record["page_count"],
                audioSeconds=record["audio_seconds"],
                description=record["description"],
                imageUrl=record["image_url"],
                authors=record["authors"],
            )
        return None


def add_book(book: Book):        
    
    hardcover_link = f"https://hardcover.app/books/{book.id}" if book.id else ""    
    authors_list = (
            [c.author.name for c in book.contributions]
            if book
            and book.contributions
            else []
        )
    params = {
        "title": book.title,
        "hardcover_book_link": hardcover_link,
        "page_count": book.pages if book.pages else None,
        "audio_seconds": book.audio_seconds if book.audio_seconds else None,
        "description": book.description if book.description else None,
        "image_url": book.image.url if book.image and book.image.url else None,
        "authors": authors_list if authors_list else [],
    }

    with driver.session() as session:
        session.run(ADD_BOOK_CYPHER, params)

    print(f"[NEO4J] Merged book: {params['title']} with authors {params['authors']}")


def check_if_book_exists(book_title: str) -> bool:
    with driver.session(database=database) as session:
        result = session.run(
            "MATCH (b:Book {title: $book_title}) RETURN b", book_title=book_title
        )
        result = result.single()
        print(
            f"Database check for book title '{book_title}': {'Found' if result is not None else 'Not Found'}"
        )
        return result is not None


def check_if_goodreadsentry_exists(entry_id: str) -> bool:
    with driver.session(database=database) as session:
        result = session.run(
            "MATCH (e:GoodreadsEntry {update_id: $entry_id}) RETURN e",
            entry_id=entry_id,
        )
        print(
            f"Database check for entry_id {entry_id}: {'Found' if result.single() is not None else 'Not Found'}"
        )
        return result.single() is not None


def connect_to_neo4j():
    neo4j_url = os.getenv("NEO4J_URL", "neo4j://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "goodreads")
    neo4j_database = os.getenv("NEO4J_DATABASE", "goodreads")

    driver = GraphDatabase.driver(neo4j_url, auth=(neo4j_username, neo4j_password))
    return driver, neo4j_database


driver, database = connect_to_neo4j()

driver.verify_connectivity()
