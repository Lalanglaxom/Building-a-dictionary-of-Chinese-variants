import asyncio
import os
import re
import sqlite3
from playwright.async_api import async_playwright

# Configuration
DB_NAME = "dictionary.db"
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
# Updated regex to capture filenames and extensions from URLs
FONT_RE = re.compile(r".*\/(?P<filename>[^/]+\.(?:woff2?|ttf|otf))(?:\?.*)?$", re.IGNORECASE)

# Global queue for background downloads
download_queue = asyncio.Queue()

async def download_worker(session):
    """Background worker that processes the download queue."""
    while True:
        url = await download_queue.get()
        match = FONT_RE.search(url)
        if match:
            filename = match.group("filename")
            save_path = os.path.join(FONTS_DIR, filename)

            # Optimization: Only download if file doesn't exist
            if not os.path.exists(save_path):
                try:
                    response = await session.get(url)
                    if response.status == 200:
                        content = await response.body()
                        with open(save_path, "wb") as f:
                            f.write(content)
                        print(f"   ✅ Saved New: {filename}")
                except Exception as e:
                    print(f"   ❌ Error {filename}: {e}")
            else:
                # Optional: print nothing to keep console clean
                pass 
        
        download_queue.task_done()

async def process_database():
    os.makedirs(FONTS_DIR, exist_ok=True)

    if not os.path.exists(DB_NAME):
        print(f"❌ Database not found at {DB_NAME}")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # cur.execute("SELECT detail_url FROM summary ORDER BY rowid DESC")
    # Order by newest first, skip the first 1300, then take everything else
    cur.execute("SELECT detail_url FROM summary ORDER BY rowid DESC LIMIT -1 OFFSET 1300")
    urls = [row[0] for row in cur.fetchall()]
    conn.close()

    print(f"🚀 Processing {len(urls)} pages (Last -> First)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...")
        page = await context.new_page()

        # Start the background download worker
        worker = asyncio.create_task(download_worker(context.request))

        # Intercept and push to queue immediately
        def intercept_response(res):
            if FONT_RE.search(res.url):
                download_queue.put_nowait(res.url)

        page.on("response", intercept_response)

        for i, url in enumerate(urls, 1):
            if i % 10 == 0: print(f"--- Progress: {i}/{len(urls)} pages scanned ---")
            try:
                # wait_until="commit" is the fastest navigation mode
                await page.goto(url, wait_until="commit", timeout=20000)
                # Give the page a tiny bit of time to start font requests
                await asyncio.sleep(0.5) 
            except Exception:
                continue

        # Wait for all queued downloads to finish
        print("Waiting for final downloads to complete...")
        await download_queue.join()
        worker.cancel()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(process_database())