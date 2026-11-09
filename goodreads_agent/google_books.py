import os
from urllib.parse import quote

import requests

from goodreads_agent.goodreads_entry import BookPayload
from goodreads_agent.google_books_model import (
    GoogleBookVolume,
    GoogleBookVolumesList,
)


def get_volume_by_id(volume_id: str) -> GoogleBookVolume:
    if not volume_id:
        raise ValueError("A valid volume_id is required.")

    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    request_url = f"https://www.googleapis.com/books/v1/volumes/{quote(volume_id)}"
    
    if api_key:
        request_url += f"?key={api_key}"

    print("Fetching volume from:", request_url)
    response = requests.get(request_url)
    response.raise_for_status()

    return GoogleBookVolume(**response.json())

def get_volumes_list(book: BookPayload = None) -> GoogleBookVolumesList:

    print("Fetching volumes for book:", book.title if book else None)

    if not book or not book.title:
        raise ValueError("A valid BookPayload with a title is required.")

    query = quote(book.title)
    api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    
    request_url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
    if api_key:
        request_url += f"&key={api_key}"

    print("Fetching from:", request_url)
    response = requests.get(request_url)
    response.raise_for_status()  # Raises HTTPError for 4xx/5xx codes

    return GoogleBookVolumesList(**response.json())

def select_best_volume(volumes_list: GoogleBookVolumesList, target_title: str, target_authors: list) -> GoogleBookVolume:
    target_lower_title = target_title.lower()
    target_lower_authors = [a.lower() for a in target_authors]
    
    best_candidate = None
    best_score = -1

    for item in volumes_list.items[:10]: # Check top 10 max
        vinfo = item.volumeInfo
        cand_title = vinfo.title.lower() if vinfo.title else ""
        cand_authors = [a.lower() for a in vinfo.authors] if vinfo.authors else []
        
        score = 0
        if target_lower_title in cand_title or cand_title in target_lower_title:
            score += 2
        # Check author overlap
        for ca in cand_authors:
            if any(ta in ca or ca in ta for ta in target_lower_authors):
                score += 3
        # Prefer items that actually have ISBNs / page counts
        if vinfo.industryIdentifiers:
            score += 1
            
        if score > best_score:
            best_score = score
            best_candidate = item

    return best_candidate or volumes_list.items[0]
