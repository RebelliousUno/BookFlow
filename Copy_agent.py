import json
import re
import asyncio
from google.adk import Workflow, Event
from dotenv import load_dotenv
import os
import feedparser
from bs4 import BeautifulSoup
from google.adk.agents import LlmAgent
from goodreads_agent.database import add_book, check_if_book_exists, check_if_goodreadsentry_exists, get_book_by_title
from goodreads_agent.goodreads_entry import BookPayload, GoodreadsUpdatePayload, ParsedGoodreadsEntry
from goodreads_agent.google_books import get_volume_by_id, get_volumes_list, select_best_volume
from goodreads_agent.google_books_model import VolumeInfo

load_dotenv()

# Helper to safely extract incoming payload dictionary from ADK events or raw data
def _payload(input_data):
    if hasattr(input_data, "output"):
        out = input_data.output
        return dict(out) if isinstance(out, dict) else {}
    return dict(input_data) if isinstance(input_data, dict) else {}

# --- FIXED STUBS WITH DATA PROPAGATION ---

# def parse_goodreads_entry(entry: dict) -> ParsedGoodreadsEntry:
#     summary_html = entry.get("summary", "") or entry.get("description", "")
#     soup = BeautifulSoup(summary_html, "html.parser")
    
#     # Extract cover image
#     img_tag = soup.find("img")
#     image_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else None
    
#     # Extract book title & Goodreads URL from .bookTitle anchor
#     book_link_tag = soup.find("a", class_="bookTitle")
#     raw_title = book_link_tag.get_text(strip=True) if book_link_tag else entry.get("title", "Unknown Title")
#     goodreads_url = book_link_tag["href"] if book_link_tag and book_link_tag.has_attr("href") else None
    
#     # Strip parenthetical series tag e.g. " (Dungeon Crawler Carl, #6)" -> clean title
#     clean_title = re.sub(r'\s*\([^)]*\)', '', raw_title).strip()
#     book_title = clean_title if clean_title else raw_title
    
#     # Extract author name
#     author_tag = soup.find("a", class_="authorName")
#     author_name = author_tag.get_text(strip=True) if author_tag else None
#     authors_list = [author_name] if author_name else []
    
#     # Extract clean text notes/review body
#     text_content = soup.get_text(separator=" ", strip=True)
    
#     # Infer post type
#     title_str = entry.get("title", "").lower()
#     if "started reading" in title_str:
#         post_type = "started reading"
#     elif "added" in title_str:
#         post_type = "added to library/shelf"
#     elif "is currently reading" in title_str:
#         post_type = "progress update"
#     else:
#         post_type = "update"

#     raw_overflow = json.dumps({
#         "raw_title": entry.get("title"),
#         "raw_book_title_html": raw_title,
#         "raw_summary_snippet": summary_html[:200],
#     })

#     return ParsedGoodreadsEntry(
#         update=GoodreadsUpdatePayload(
#             update_id=entry.get("id", ""),
#             date=entry.get("published"),
#             post_type=post_type,
#             content=text_content,
#             image_url=image_url,
#             goodreads_link=entry.get("link"),
#             raw_overflow=raw_overflow,
#         ),
#         book=BookPayload(
#             title=book_title,
#             authors=authors_list,
#             goodreads_url=goodreads_url,
#             image_url=image_url,
#         )
#     )
# 
# def read_rss_feed(node_input):
#     # print("read_rss_feed received:", node_input)
#     rss_url = os.getenv("RSS_FEED_URL", "")
#     feed = feedparser.parse(rss_url)
#     parsed_entries = [parse_goodreads_entry(entry) for entry in feed.entries]
#     return Event(state={"parsed_entries": parsed_entries})


parser_agent = LlmAgent(
    name="goodreads_parser_agent",
    model="gemini-2.5-flash",
    instruction="""Parse the provided Goodreads RSS entry text.
Strip parenthetical series information from the book title (e.g. "(Dungeon Crawler Carl, #6)" -> "The Eye of the Bedlam Bride").
post_type must be one of: "started reading", "added to library/shelf", "progress update", "update".""",
    output_schema=ParsedGoodreadsEntry,
    temperature=0.1
)
def read_rss_feed(input_data):
    # Safely unpack the current graph state
    d = input_data.output if hasattr(input_data, "output") else dict(input_data)
    
    rss_url = os.getenv("RSS_FEED_URL", "")
    feed = feedparser.parse(rss_url)
    
    # Strip away the heavy feedparser objects and keep only the raw strings 
    # to ensure clean JSON serialization in the ADK state graph
    raw_entries = []
    for entry in feed.entries:
        raw_entries.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "summary": entry.get("summary", "") or entry.get("description", "")
        })
        
    print(f"[RSS] Queued {len(raw_entries)} raw entries for parsing.")
    
    # Push the raw queue into state. The fetch_next_entry_router will 
    # check this queue to decide whether to continue or finish_batch.
    return Event(output={
        **d, 
        "raw_entries": raw_entries
    })

def fetch_next_entry(input_data):
    d = _payload(input_data)
    entries = d.get("raw_entries", [])
    
    current_raw = entries.pop(0)
    summary_html = current_raw.get("summary", "") or current_raw.get("description", "")
    
    # Format the payload for the agent
    prompt = f"""
    Title: {current_raw.get("title", "")}
    Link: {current_raw.get("link", "")}
    Published: {current_raw.get("published", "")}
    Summary HTML: {summary_html[:1500]}
    """
    
    return Event(output={
        **d,
        "raw_entries": entries,
        "user_input": prompt
    })


# def fetch_next_entry(parsed_entries: list[ParsedGoodreadsEntry] = None):
#     # Fetch the next entry from the list of parsed entries
#     # print("Parsed entries available:", parsed_entries)
#     if not parsed_entries:
#         return Event(state={"current_entry": None, "parsed_entries": []})
#     current_entry = parsed_entries[0]
#     new_parsed_entries = parsed_entries[1:] if len(parsed_entries) > 1 else []

#     print("Current Entry: ", current_entry)
#     print("New Parsed Entries:", new_parsed_entries)
   
#     return Event(state={"current_entry": current_entry, "parsed_entries": new_parsed_entries})

def is_new_update_router(current_entry: ParsedGoodreadsEntry = None):
    ## Grab the current entry from the state
    ## Check if the entry has already been added to the database

    # print("is_new_update_router received:", current_entry)

    if current_entry is None:
        return Event(route="IS_NOT_NEW_UPDATE")

    already_exists = check_if_goodreadsentry_exists(current_entry.update.update_id)
    if already_exists:
        print(f"Entry {current_entry.update.update_id} already exists in the database.")
    else:
        print(f"Entry {current_entry.update.update_id} is new.")

    return Event(route="IS_NEW_UPDATE" if not already_exists else "IS_NOT_NEW_UPDATE")



def is_new_book_router(current_entry: ParsedGoodreadsEntry = None):
    ## Check if the book associated with the current_entry is already in the database.
    ## If not route to the Google Books fetch path, else route to the existing book path.


    # print("is_new_book_router received:", current_entry)
    book_title = current_entry.book.title if current_entry else None
    if not book_title:
        print("No book title found in current entry.")
        return Event(route="IS_EXISTING_BOOK")  # Default to existing if no title
    book_exists = check_if_book_exists(book_title)

    return Event(route="IS_EXISTING_BOOK" if book_exists else "IS_NEW_BOOK")

def get_book_info_from_google_books(current_entry: ParsedGoodreadsEntry = None):
    # print("get_book_info_from_google_books received:", current_entry)

    volume_list = get_volumes_list(current_entry.book)

    best_volume = select_best_volume(volume_list, current_entry.book.title, current_entry.book.authors) if volume_list.items else None
    detailed_volume_info = get_volume_by_id(best_volume.id) if best_volume else None
    

    # In a real implementation, this would fetch book info from Google Books API
    return Event(state={"book_info": detailed_volume_info.volumeInfo if detailed_volume_info else None})

def add_book_to_database(book_info: VolumeInfo = None):
    print("Add Book TO Database Received", book_info)
    add_book(book_info)
    return Event(output="Book added to database.")

def extract_book_info(book_info: VolumeInfo = None):
    # print("extract_book_info received:", book_info)
    
    # Convergence point for both paths (either fresh DB insert confirmation or existing DB read)
    existing_info = get_book_by_title(book_info.title)  # Placeholder function to fetch book info from DB
    return Event(state={"current_book_info": existing_info if existing_info else book_info})

def prepare_image_url(current_entry: ParsedGoodreadsEntry = None):
    # Prepare the image URL for social media posting, decompressing if necessary.
    # Example goodreads url image_url='https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/books/1765295047l/244813482._SY75_.jpg'
    # print("prepare_image_url received:", current_entry)
    decompressed_image_url = current_entry.update.image_url if current_entry and current_entry.update.image_url else None
    decompressed_image_url = re.sub(r"\._SY\d+_","", decompressed_image_url)
    decompressed_image_url = re.sub(r"\._SX\d+_","", decompressed_image_url)
    new_entry = (
        current_entry.__replace__(
            update=current_entry.update.__replace__(image_url=decompressed_image_url)
        )
        if current_entry
        else None
    )
    return Event(state={"current_entry": new_entry})

def prepare_post_input(current_entry: ParsedGoodreadsEntry = None, current_book_info: VolumeInfo = None, batched_prompts: list[str] = []):

    print("prepare_post_input received:", current_entry, current_book_info, batched_prompts)
    # Prepare the input to the prompt
    new_post_details = f"""
        Goodreads post: {current_entry.update.content}
        Book Title: {current_book_info.title}
        Author(s): {current_book_info.authors}
        Page Count: {current_book_info.pageCount}
        Cover Image: {current_entry.update.image_url}

    """
    print(new_post_details)
    new_batch = {*batched_prompts, new_post_details}
    return Event(state={"batched_prompts": new_batch})

def create_social_media_post(node_input):
    print("create_social_media_post received:", node_input)
    d = _payload(node_input)
    print("[STUB] Buffer API posted to X, Bluesky, Mastodon with content:", d.get("post_input"))
    return Event(state={**d, "buffer_status": "posted_all"})

def update_database_with_post_info(node_input):
    print("update_database_with_post_info received:", node_input)
    d = _payload(node_input)
    print("[STUB] Marked Goodreads update processed & saved social record.")
    return Event(state={**d, "workflow_complete": True})

def end_node(node_input):
    print("end_node received:", node_input)
    return Event(state={"status": "Workflow completed successfully."})

def fetch_next_entry_router(parsed_entries: list[ParsedGoodreadsEntry] = None):
    # print("fetch_next_entry_router received:", parsed_entries)
    if parsed_entries:
        return Event(route="HAS_MORE_ENTRIES")
    else:
        return Event(route="NO_MORE_ENTRIES")
# --- WORKFLOW GRAPH ---
def finish_batch():
    return Event(state={"status": "All entries processed."})

root_agent = Workflow(
    name="goodreads_workflow",
    edges=[
        ("START", read_rss_feed, fetch_next_entry_router),
        
        (fetch_next_entry_router, {
            "HAS_MORE_ENTRIES": fetch_next_entry,
            "NO_MORE_ENTRIES": finish_batch
        }),
        
        # === NATIVE INJECTION ===
        # fetch_next_entry provides `user_input` -> parser_agent consumes it and outputs `book` and `update` to state.
        (fetch_next_entry, parser_agent, is_new_update_router),
        # ========================
        
        (is_new_update_router, {
            "IS_NOT_NEW_UPDATE": end_node,
            "IS_NEW_UPDATE": is_new_book_router
        }),
        
        (is_new_book_router, {
            "IS_NEW_BOOK": get_book_info_from_google_books,
            "IS_EXISTING_BOOK": extract_book_info  
        }),
        
        (get_book_info_from_google_books, add_book_to_database, extract_book_info),
        
        (
            extract_book_info, 
            prepare_image_url, 
            prepare_post_input, 
            fetch_next_entry_router # Loops back up
        ),
        (
            finish_batch,
            create_social_media_post, 
            update_database_with_post_info, 
            end_node
        ),
    ]
)

# root_agent = Workflow(
#     name="goodreads_workflow",
#     edges=[
#         # START -> read RSS -> check if update is new
#         ("START", read_rss_feed, fetch_next_entry_router),
#         (fetch_next_entry_router, {"HAS_MORE_ENTRIES": fetch_next_entry,
#                                    "NO_MORE_ENTRIES": finish_batch}),
#         (fetch_next_entry, is_new_update_router),
        
#         # Branch 1: Update status
#         (is_new_update_router, {
#             "IS_NOT_NEW_UPDATE": end_node,
#             "IS_NEW_UPDATE": is_new_book_router
#         }),
        
#         # Branch 2: Book status split
#         (is_new_book_router, {
#             "IS_NEW_BOOK": get_book_info_from_google_books,
#             "IS_EXISTING_BOOK": extract_book_info  # Existing path jumps straight to extract
#         }),
        
#         # New Book Path: Google Books -> Add to DB -> converge at extract_book_info
#         (get_book_info_from_google_books, add_book_to_database, extract_book_info),
        
#         # Shared Pipeline downstream of convergence
#         (
#             extract_book_info, 
#             prepare_image_url, 
#             prepare_post_input, fetch_next_entry_router 
#         ),
#         (
#             finish_batch,
#             create_social_media_post, 
#             update_database_with_post_info, 
#             end_node
#         ),
#     ]
#)