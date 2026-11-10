import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.adk import Event, Workflow
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.genai import types

from goodreads_agent import database
from goodreads_agent.buffer import post_to_buffer
from goodreads_agent.database import (
    add_book,
    check_if_book_exists,
    get_last_run_time,
    set_last_run_time,
)
from goodreads_agent.hardcover_activities_models import ActivityItem
from goodreads_agent.hardcover_api import get_activites
from goodreads_agent.prompt import (
    create_social_media_post_footer,
    create_social_media_post_header,
)

load_dotenv()
client = genai.Client()


def set_last_run_time_in_database(last_run_time: str):
    set_last_run_time(last_run_time)
    return Event(state={"last_run_time": last_run_time})


def get_last_run_time_from_database():
    last_run_time = get_last_run_time()
    if last_run_time is None:
        last_run_time = "2024-06-01T00:00:00Z"  # Default value if not set
    return Event(state={"last_run_time": last_run_time})


async def read_activities_from_hardcover(last_run_time: str = "2024-06-01T00:00:00Z"):
    # Fetch activities from the Hardcover API
    activities = await get_activites(last_run_time)
    print(f"[HARDCOVER] Fetched {len(activities)} activities since {last_run_time}.")
    return Event(
        state={
            "activities": activities.copy(),
            "all_activities": activities.copy(),
        }
    )


def fetch_next_entry_router(
    activities: list[ActivityItem] | None,
    all_activities: list[ActivityItem] | None = None,
):
    if activities and len(activities) > 0:
        return Event(route="HAS_MORE_ENTRIES")
    if not all_activities:
        return Event(route="NO_ACTIVITIES")
    else:
        return Event(route="NO_MORE_ENTRIES")


def fetch_next_entry(activities: list[ActivityItem] | None):
    if not activities:
        return Event(state={"current_entry": None})

    current_activity = activities.pop(0)

    return Event(state={"activities": activities, "current_activity": current_activity})


def is_new_book_router(current_activity: ActivityItem = None):
    book_title = current_activity.book.title if current_activity else None

    if not book_title:
        print("No book title found in current entry.")
        return Event(route="IS_EXISTING_BOOK")

    book_exists = check_if_book_exists(book_title)
    return Event(route="IS_EXISTING_BOOK" if book_exists else "IS_NEW_BOOK")


def add_book_to_database(current_activity: ActivityItem = None):
    if current_activity.book:
        add_book(current_activity.book)
        print("Book added to database.")
    return Event(state={})


def prepare_post_input(
    current_activity: ActivityItem | None, batched_prompts: list[str] | None = None
):
    if batched_prompts is None:
        batched_prompts = []
    user_book_data = (
        current_activity.data.get("userBook", {}) if current_activity else {}
    )
    edition = user_book_data.get("edition", {})

    # Map status_id to a readable label
    status_id = user_book_data.get("statusId")
    status_map = {
        1: "Want to Read",
        2: "Currently Reading",
        3: "Read",
        5: "Did Not Finish",
    }
    reading_status = status_map.get(status_id, "Updated Progress")

    # Extract format and runtime/pages
    edition_format = edition.get("editionFormat", "Unknown Format")
    audio_seconds = edition.get("audioSeconds")
    pages = edition.get("pages") or (
        current_activity.book.pages
        if current_activity and current_activity.book
        else None
    )

    # Format runtime nicely if it's an audiobook (e.g., converting seconds to hours)
    runtime_str = ""
    if audio_seconds:
        hours = audio_seconds // 3600
        minutes = (audio_seconds % 3600) // 60
        runtime_str = f"{hours}h {minutes}m"

    # Extract specific activity metrics
    progress = user_book_data.get("progress")
    rating = user_book_data.get("rating")
    review = user_book_data.get("review") or user_book_data.get("reviewSlate")

    # Format progress nicely if present
    progress_str = f"{progress:.1f}%" if progress is not None else ""
    authors_list = (
        [c.author.name for c in current_activity.book.contributions]
        if current_activity
        and current_activity.book
        and current_activity.book.contributions
        else []
    )

    new_post_details = f"""
        Post Timestamp: {current_activity.created_at if current_activity else ""}
        Activity Type: {current_activity.event if current_activity else ""}
        Reading Status: {reading_status}
        Format: {edition_format}
        Runtime/Length: {runtime_str if runtime_str else f"{pages} pages" if pages else "Unknown"}
        Book Title: {current_activity.book.title if current_activity.book else "Unknown"}
        Book Description: {current_activity.book.description if current_activity.book else "No description available."}
        Author(s): {authors_list if authors_list else []}
        --- Activity Details ---
        Progress: {progress_str if progress_str else "N/A"}
        Rating: {f"{rating} / 5" if rating else "N/A"}
        Review / Notes: {review if review else "None provided"}
    """
    print(
        f"[POST PREP] Prepared post details for entry: {current_activity.id if current_activity else 'N/A'}"
    )
    print(new_post_details)
    batched_prompts.append(new_post_details.strip())
    return Event(state={"batched_prompts": batched_prompts})


def create_social_media_post_instruction_provider(context: ReadonlyContext) -> str:
    return (
        create_social_media_post_header
        + "\n".join(context.state.get("batched_prompts", []))
        + create_social_media_post_footer
    )


create_social_media_post_agent = LlmAgent(
    name="create_social_media_post_agent",
    model="gemini-3.8-flash",
    instruction=create_social_media_post_instruction_provider,
    output_key="social_media_post",
)


async def create_social_media_post(batched_prompts: list[str] | None):
    if not batched_prompts:
        print("No prompts to process for social media post.")
        return Event(state={"buffer_status": "no_prompts"})

    create_social_media_prompt = (
        create_social_media_post_header
        + "\n".join(batched_prompts)
        + create_social_media_post_footer
    )
    print(create_social_media_prompt)
    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=create_social_media_prompt,
        config=types.GenerateContentConfig(
            system_instruction="", response_mime_type="text/plain", temperature=0.7
        ),
    )
    print("Generated social media post:", response.text)
    if os.getenv("GOODREADS_BACKFILL"):
        print("[BACKFILL MODE] Skipping actual post creation.")
    else:
        # Here you would implement the actual posting logic to X/Bluesky/Mastodon
        print("[STUB] Social media post created successfully.")
    return Event(state={"buffer_status": "created_all"})

def post_to_social_media(social_media_post: str | None, current_activity: ActivityItem | None = None):
    # Call the refactored function which returns a status dict
    image_url = current_activity.book.image.url if current_activity and current_activity.book and current_activity.book.image else None
    status_dict = post_to_buffer(social_media_post, image_url=image_url) 
    
    # Wrap the dictionary result in an Event for your agent graph
    return Event(state=status_dict)


def update_database_with_post_info(
    social_media_post: str | None,
    all_activities: list[ActivityItem] | None = None,
    pending_run_time: str | None = None,
):
    # update the database with the activities, books, and the post and link them together
    if not social_media_post:
        print("No social media post content to update in the database.")
        return Event(state={"buffer_status": "no_post_content"})
    if not all_activities:
        print("No activities to update in the database.")
        return Event(state={"buffer_status": "no_activities"})

    saved_count = database.update_posts_and_activities(
        social_media_post, all_activities
    )
    print(f"[NEO4J] Saved social post and {saved_count} activities.")
    if pending_run_time:
        database.set_last_run_time(pending_run_time)
    return Event(state={"workflow_complete": True, "activities_saved": saved_count})


def finish_batch():
    # The last run time is only persisted once the post has been created successfully,
    # so a model failure (e.g. 503) doesn't skip these activities on the next run.
    current_run_time = datetime.now().isoformat()
    return Event(
        state={
            "pending_run_time": current_run_time,
            "status": f"Current Run Time {current_run_time}",
        }
    )


def finish_empty_batch():
    print("[HARDCOVER] No activities found; finishing the run.")
    current_run_time = datetime.now().isoformat()
    database.set_last_run_time(current_run_time)
    return Event(state={"status": f"Current Run Time {current_run_time}"})


def end_node():
    print("Workflow completed successfully.")
    return Event(state={})


# --- WORKFLOW GRAPH ---

root_agent = Workflow(
    name="goodreads_workflow",
    edges=[
        ("START", get_last_run_time_from_database, read_activities_from_hardcover),
        (read_activities_from_hardcover, fetch_next_entry_router),
        (
            fetch_next_entry_router,
            {
                "HAS_MORE_ENTRIES": fetch_next_entry,
                "NO_MORE_ENTRIES": finish_batch,
                "NO_ACTIVITIES": finish_empty_batch,
            },
        ),
        (finish_empty_batch, end_node),
        (fetch_next_entry, is_new_book_router),
        (
            is_new_book_router,
            {
                "IS_NEW_BOOK": add_book_to_database,
                "IS_EXISTING_BOOK": prepare_post_input,
            },
        ),
        (
            add_book_to_database,
            prepare_post_input,
            fetch_next_entry_router,  # Loop back up
        ),
        (
            finish_batch,
            create_social_media_post_agent,
            post_to_social_media,
            update_database_with_post_info,
            end_node,
        ),
    ],
)
