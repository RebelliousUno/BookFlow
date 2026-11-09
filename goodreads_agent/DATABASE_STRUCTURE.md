# Neo4j Database Schema: Goodreads Social Automation

## 1. Node Definitions

### `Book`

| Property | Type | Description | Key / Constraint |
| :--- | :--- | :--- | :--- |
| `isbn` | String | ISBN-13/10 (fallback to `unknown_<goodreads_book_id>` if missing) | **Unique (Primary Key)** |
| `title` | String | Book title | |
| `authors` | List[String] | Author name(s) | Native multi-value list |
| `google_books_link` | String | URL to Google Books entry | |
| `page_count` | Integer | Total page count | |
| `synopsis` | String | Book description/synopsis | |
| `image_url` | String | Cover image URL from Google Books | |

### `Goodreads_Update`

| Property | Type | Description | Key / Constraint |
| :--- | :--- | :--- | :--- |
| `update_id` | String | Unique RSS item ID/guid | **Unique (Primary Key)** |
| `date` | DateTime | Update timestamp | |
| `post_type` | String | e.g., 'started reading', 'review', 'finished reading', 'progress' | |
| `content` | String | Review text, user notes, rating info | |
| `image_url` | String | Image URL extracted from update | |
| `goodreads_link` | String | Direct link to Goodreads post | |
| `raw_overflow` | String (JSON) | Serialized JSON blob for unexpected/future RSS fields | |

### `Social_Post`

| Property | Type | Description | Key / Constraint |
| :--- | :--- | :--- | :--- |
| `buffer_post_id` | String | Buffer broadcast/post ID | **Unique (Primary Key)** |
| `content` | String | Final formatted text sent to platforms | |
| `posted_at` | DateTime | Dispatch timestamp | |
| `image_url` | String | Final image URL used in post | |
| `platforms` | List[String] | Target platforms, e.g., `['x', 'bluesky', 'mastodon']` | |

---

## 2. Relationship Schema

| From | Relationship | To | Description |
| :--- | :--- | :--- | :--- |
| `Goodreads_Update` | `IS_ABOUT` | `Book` | Connects the RSS activity item to the target book |
| `Social_Post` | `IS_ABOUT` | `Book` | Connects the social broadcast directly to the book |
| `Goodreads_Update` | `PROCESSED_BY` | `Social_Post` | Graph-native state tracking (existence = processed) |

---

## 3. Uniqueness Constraints (Neo4j 5+)

Run these in your Cypher shell/driver initialization:

```cypher
CREATE CONSTRAINT book_isbn_uniq IF NOT EXISTS FOR (b:Book) REQUIRE b.isbn IS UNIQUE;
CREATE CONSTRAINT update_id_uniq IF NOT EXISTS FOR (u:Goodreads_Update) REQUIRE u.update_id IS UNIQUE;
CREATE CONSTRAINT social_post_uniq IF NOT EXISTS FOR (p:Social_Post) REQUIRE p.buffer_post_id IS UNIQUE;
