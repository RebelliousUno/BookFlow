from typing import Any

from pydantic import BaseModel, Field


class ImageInfo(BaseModel):
    url: str | None = None


class Author(BaseModel):
    name: str
    slug: str


class Contribution(BaseModel):
    contribution: str | None = None
    author: Author


class SeriesInfo(BaseModel):
    name: str
    books_count: int = Field(..., alias="books_count")


class BookSeriesItem(BaseModel):
    position: float | None = None
    series: SeriesInfo


class Book(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    description: str | None = None
    release_date: str | None = Field(None, alias="release_date")
    pages: int | None = None
    audio_seconds: int | None = Field(None, alias="audio_seconds")
    rating: float | None = None
    ratings_count: int | None = Field(None, alias="ratings_count")
    image: ImageInfo | None = None
    contributions: list[Contribution] = Field(default_factory=list)
    cached_tags: dict[str, Any] | None = Field(
        default_factory=dict, alias="cached_tags"
    )
    book_series: list[BookSeriesItem] = Field(default_factory=list, alias="book_series")


class ActivityItem(BaseModel):
    id: int
    event: str
    data: dict[str, Any]  # Retains raw userBook progress/edition metadata
    book_id: int | None = Field(None, alias="book_id")
    created_at: str = Field(..., alias="created_at")
    book: Book | None = None


class HardcoverActivityResponse(BaseModel):
    activities: list[ActivityItem] = Field(default_factory=list)
