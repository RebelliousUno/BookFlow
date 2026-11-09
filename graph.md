```mermaid
graph TD
    START([START]) --> fetch_rss_all --> fetch_next_entry
    
    fetch_next_entry -- "Has Entry" --> is_new_update_router
    fetch_next_entry -- "Queue Empty / Exhausted" --> finish_batch
    
    is_new_update_router -- "NOT_NEW (Watermark Hit)" --> finish_batch
    is_new_update_router -- "IS_NEW" --> is_new_book_router
    
    is_new_book_router -- "IS_NEW_BOOK" --> get_book_info_from_google_books --> add_book_to_database --> extract_book_info
    is_new_book_router -- "IS_EXISTING_BOOK" --> extract_book_info
    
    extract_book_info --> prepare_image_url --> accumulate_post_input --> fetch_next_entry
    
    finish_batch --> check_is_cold_start{GOODREADS_BACKFILL?}
    check_is_cold_start -- "Yes (Silent Seed)" --> silent_seed_database --> end_node([end_node])
    check_is_cold_start -- "No (Live Run)" --> create_social_media_post --> update_database_with_post_info --> end_node([end_node])