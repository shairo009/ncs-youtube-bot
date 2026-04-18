import asyncio
from playwright.async_api import async_playwright
import os
import sys

async def record_html_bg(duration_sec, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        os.remove(output_path)
        
    import time
    html_path = f"file://{os.path.abspath('temp_ui.html')}?v={int(time.time())}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # We enforce strict 1080x1920 output dimension for shorts
        context = await browser.new_context(
            viewport={"width": 1080, "height": 1920},
            record_video_dir=os.path.dirname(output_path),
            record_video_size={"width": 1080, "height": 1920}
        )
        page = await context.new_page()
        
        print(f"🎬 Playwright: Recording UI for {duration_sec}s...")
        await page.goto(html_path)
        
        await asyncio.sleep(duration_sec + 0.5) # Slight buffer
        
        video_path = await page.video.path()
        await context.close()
        await browser.close()
        
        os.rename(video_path, output_path)
        print(f"✅ Playwright: WebM saved -> {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python html_recorder.py <duration> <output_path>")
        sys.exit(1)
    
    dur = float(sys.argv[1])
    out = sys.argv[2]
    asyncio.run(record_html_bg(dur, out))
