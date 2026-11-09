# Neo4j Database Schema

## Nodes

### `Book`

| Property | Type | Description |
| :--- | :--- | :--- |
| `title` | String | Book title; used to merge book nodes |
| `hardcover_book_link` | String | Hardcover book URL |
| `page_count` | Integer | Page count |
| `audio_seconds` | Integer | Audiobook runtime in seconds |
| `description` | String | Book description |
| `image_url` | String | Cover image URL |

### `Author`

| Property | Type | Description |
| :--- | :--- | :--- |
| `name` | String | Author name |

### `Goodreads_Update` (Hardcover activity)

| Property | Type | Description |
| :--- | :--- | :--- |
| `update_id` | String | Hardcover activity ID |
| `date` | DateTime | Activity timestamp |
| `post_type` | String | Hardcover activity event |
| `content` | String | JSON-serialized activity data |
| `image_url` | String | Book cover image URL |
| `hardcover_book_id` | Integer | Hardcover book ID |

### `Social_Post`

| Property | Type | Description |
| :--- | :--- | :--- |
| `content` | String | Final formatted text sent to platforms |
| `posted_at` | DateTime | Database persistence timestamp |

## Relationships

| From | Relationship | To | Description |
| :--- | :--- | :--- | :--- |
| `Author` | `WROTE` | `Book` | Connects a book to its authors |
| `Goodreads_Update` | `IS_ABOUT` | `Book` | Connects an activity to a matching book, when found |
| `Goodreads_Update` | `PROCESSED_BY` | `Social_Post` | Connects each activity in the batch to its generated post |

Activity IDs identify individual Hardcover updates. A uniqueness constraint is
recommended:

```cypher
CREATE CONSTRAINT update_id_uniq IF NOT EXISTS
FOR (u:Goodreads_Update) REQUIRE u.update_id IS UNIQUE;
```
