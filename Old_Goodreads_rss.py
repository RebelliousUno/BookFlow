
def read_rss_feed():
    rss_url = os.getenv("RSS_FEED_URL", "")
    feed = feedparser.parse(rss_url)
    
    raw_entries = []
    for entry in feed.entries:
        raw_entries.append(ActivityItem(
            title=entry.get("title", ""),
            link=entry.get("link", ""),
            published=entry.get("published", ""),
            summary=entry.get("summary", "") or entry.get("description", "")
        ))
        
    print(f"[RSS] Queued {len(raw_entries)} raw entries for parsing.")
    return Event(state={"raw_entries": raw_entries, "batched_prompts": []})

async def run_parser_node(current_activity: ActivityItem = None):
    if not current_activity:
        return Event(state={"current_entry": None})
    # print(f"[PARSER] Processing entry: {current_entry}")
    summary_html = current_activity.get("summary", "") or current_activity.get("description", "")

    prompt = f"""
    Title: {current_activity.get("title", "")}
    Link: {current_activity.get("link", "")}
    Published: {current_activity.get("published", "")}
    Summary HTML: {summary_html[:1500]}
    """
    response = await client.aio.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
        system_instruction="""Parse the provided Goodreads RSS entry text into structured fields.
Strip parenthetical series information from the book title (e.g. "(Dungeon Crawler Carl, #6)" -> "The Eye of the Bedlam Bride").
post_type must be one of: "started reading", "added to library/shelf", "progress update", "update".

CRITICAL CONTENT SYNTHESIS RULES:
- `content` MUST NEVER BE EMPTY OR "None". Always construct a natural social media update line.
- If a rating/completion exists (e.g. "gave X stars") AND there is a user review/note, COMBINE them into a rich post: "Finished {book_title} — gave it {rating} stars: "{user_review}""
- If rating/completion exists with NO review, output: "Finished {book_title} — gave it {rating} stars"
- If page progress (e.g. "Matthew is on page X"), output: "Got to page {X}"
- If shelf/want-to-read with no text, output: "Want to read {book_title}"
- If it's a standalone note/review with no rating, use the review text cleanly.""",
        response_mime_type="application/json",
        response_schema=ParsedGoodreadsEntry,
        temperature=0.1
    ),
)
    
    parsed = ParsedGoodreadsEntry.model_validate_json(response.text)
    
    # Overwrite the raw dict with the parsed Pydantic model for downstream nodes
    return Event(state={"current_entry": parsed})

def prepare_image_url(cur: ParsedGoodreadsEntry = None):
    image_url = current_entry.update.image_url if current_entry else None
    
    if image_url:
        decompressed = re.sub(r"\._SY\d+_","", image_url)
        decompressed = re.sub(r"\._SX\d+_","", decompressed)
        current_entry.update.image_url = decompressed
        
    # Push updated entry back to state
    return Event(state={"current_entry": current_entry})



def get_book_info_from_google_books(current_activity: ActivityItem = None):
    if not current_activity:
        return Event(state={"book_info": None})
        
    book_payload = current_activity.book
    volume_list = get_volumes_list(book_payload)
    author_name = book_payload.contributions[0].author.name if book_payload.contributions else None
    best_volume = select_best_volume(volume_list, book_payload.title, author_name) if volume_list.items else None
    detailed_volume_info = get_volume_by_id(best_volume.id) if best_volume else None
    
    return Event(state={"book_info": detailed_volume_info.volumeInfo if detailed_volume_info else None})

def extract_book_info(current_activity: ActivityItem = None, book_info: VolumeInfo = None):
    # If book_info is empty (we skipped Google Books), pull from DB
    if not book_info and current_activity:
        book_title = current_activity.book.title
        book_info = get_book_by_title(book_title)
        
    return Event(state={"current_book_info": book_info})


def is_new_update_router(current_activity: ActivityItem = None):
    if not current_activity:
        return Event(route="IS_NOT_NEW_UPDATE")

    update_id = current_activity.id
    already_exists = check_if_goodreadsentry_exists(update_id)
    
    if already_exists:
        print(f"Entry {update_id} already exists in the database.")
    else:
        print(f"Entry {update_id} is new.")

    return Event(route="IS_NOT_NEW_UPDATE" if already_exists else "IS_NEW_UPDATE")