create_social_media_post_header="""

**Write a short, engaging social media post for X/Bluesky/Mastodon based on this reading activity.**
There may be multiple reading activities in this batch, so combine them into a single post. Each activity is separated by a line break. The post should be concise, natural, and authentic, reflecting my personal reading experience. Avoid generic or overly enthusiastic language. Focus on the specific details of the books and my engagement with them.
<activity>
"""

create_social_media_post_footer=""")
</activity>
**Rules:**
- Return ONLY the final post text.
- Do not return explanations, labels, markdown, quotation marks, URLs, or anything outside the final post.
- Maximum 280 characters.
- Write in the FIRST PERSON and PRESENT TENSE.
- The reading tracker user is me. Never refer to me by name in the third person. Convert all activity into a first-person update.
- Use a natural, grounded, and authentic voice suitable for X/Bluesky/Mastodon.
- **CRITICAL: Avoid repetitive, overly enthusiastic, or generic "cringe" phrases like "loving the vibes", "hooked", "unputdownable", or "mind-blowing". Keep the language conversational but mature and varied.**
- Mention the book title when it can be determined from the feed item.
- Keep the tone friendly, positive, and engaging without forced enthusiasm.
- Never include spoilers, plot details, twists, endings, character reveals, theories, or foreshadowing.
- Never be derogatory, insulting, cynical, dismissive, sarcastic, hostile, or negative about a book, author, series, genre, or other readers.
- If a rating is low, remain respectful and focus on the experience rather than criticism.
- Avoid repeating raw activity wording verbatim.
- Remove all HTML, XML, RSS metadata, reading tracker IDs, and raw markup.
- Do not invent facts about the book, author, story, characters, or content.
- Include 2-4 sensible hashtags at the end of the post. Use PascalCase for all multi-word hashtags to improve accessibility (e.g., #Books, #BookCommunity).
- For the primary book hashtag, use the PascalCase series name if the book belongs to a known series (e.g., #StormlightArchive, #DungeonCrawlerCarl). If it is a standalone book, use the PascalCase book title (e.g., #WindAndTruth, #TheGlass). Strip all punctuation (like apostrophes) from hashtags.
- Do not include my handle unless it fits naturally.
- Vary the wording and structure so posts feel unique and human. Never use the exact same sentence structure across multiple updates.

**Activity guidance:**

**If I add a book to my Want To Read shelf:**
- Mention that I've added the book to my reading list or TBR.
- Express curiosity or interest without over-hyping it.
*Examples:*
Just added The Dungeon Anarchist's Cookbook to my reading list. The TBR pile keeps growing. #DungeonCrawlerCarl #Books #Hardcover
Wind and Truth is heading straight onto my reading list. Looking forward to seeing where this one goes. #StormlightArchive #Books #TBR

**If the update indicates I added the book to the "currently-reading" shelf (and has no page/percentage):**
- Treat this as STARTING the book.
- Mention that I am beginning the read.
- Keep it simple and grounded.
*Examples:*
Starting The Dungeon Anarchist's Cookbook today. Time to dive into the next one. #DungeonCrawlerCarl #Books 
I've just started Wind and Truth. Let's see what this journey has in store. #StormlightArchive #Books

**If the update contains a page number, chapter, or percentage:**
- Treat this strictly as an IN-PROGRESS update. NEVER use the words "starting", "started", or "just began".
- Accurately reflect the depth of the reading phase based on the number (e.g., 5% is early on, 50% is the midway point, page 500+ is deep into the story, 90% is the final stretch).
- Use your existing knowledge of the book to subtly nod to the general themes, tone, or phase of the story happening around that point in the book (e.g., hinting at rising tension or entering the third act). **However, you MUST strictly avoid hallucinating plotlines, inventing specific events, or posting spoilers.**
- Extract any custom commentary or personal notes I included in the update and weave that specific thought naturally into the post. Do not invent commentary.
- Focus on momentum and engagement, strictly avoiding clichés.
*Examples:*
I'm on page 551 of The Dungeon Anarchist's Cookbook. Deep into the crawl now and the stakes are definitely shifting; it's keeping my attention nicely. #DungeonCrawlerCarl #Books 
I'm 36% of the way through The Glass. Book 1 of 3 is done, the pacing works well, and I'm curious to see how the next act plays out. #TheGlass #Books 

**If I finish a book and rate it:**
- Mention the rating.
- Give a brief, spoiler-free reaction that reflects the score cleanly.
- Focus on the overall reading experience.
*5 stars:* Finished Wind and Truth and gave it 5 stars. A genuinely great read from start to finish. #StormlightArchive #Books #Hardcover
*4 stars:* Finished The Glass and gave it 4 stars. Really enjoyed my time with this one. #TheGlass #Books
*3 stars:* Finished The Dungeon Anarchist's Cookbook and gave it 3 stars. A solid read with plenty to appreciate. #DungeonCrawlerCarl #Books #Hardcover
*2 stars:* Finished The Glass and gave it 2 stars. Not quite what I expected, but glad I read it. #TheGlass #Books
*1 star:* Finished The Dungeon Anarchist's Cookbook and gave it 1 star. Wasn't the right fit for me, but always good to try something new. #DungeonCrawlerCarl #Books

"""