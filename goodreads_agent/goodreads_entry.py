from pydantic import BaseModel, Field


class BookPayload(BaseModel):
    isbn: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    goodreads_url: str | None = None
    google_books_link: str | None = None
    page_count: int | None = None
    synopsis: str | None = None
    image_url: str | None = None


class GoodreadsUpdatePayload(BaseModel):
    update_id: str
    date: str | None = None  # Or datetime if parsed
    post_type: str = "general"
    content: str = ""  # Default to empty string, never None
    image_url: str | None = None
    goodreads_link: str | None = None
    raw_overflow: str | None = None


class ParsedGoodreadsEntry(BaseModel):
    update: GoodreadsUpdatePayload
    book: BookPayload
