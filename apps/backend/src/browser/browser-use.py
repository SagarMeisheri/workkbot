import asyncio
import os
from browser_use import Agent, BrowserSession, ChatGoogle
from browser_use_sdk.v3 import AsyncBrowserUse
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("BROWSER_USE_API_KEY")


async def main():
    client = AsyncBrowserUse(api_key=api_key)
    try:
        browser = await client.browsers.create(
            proxy_country_code="us",
            timeout=5,
            browser_screen_width=1440,
            browser_screen_height=900,
            allow_resizing=True,
            enable_recording=True,
        )
        try:
            agent = Agent(
                task="get me drishyam 3 movie tikcet prices iwth food options in mulund 2 seat after 7pm",
                llm=ChatGoogle(model="gemini-3.5-flash-lite"),
                browser_session=BrowserSession(cdp_url=browser.cdp_url),
            )
            print(await agent.run())
        finally:
            # Billing runs until the browser stops or its timeout expires.
            await client.browsers.stop(browser.id)

        # recording_url is still None right away — the video is stitched after stop.
        # Poll until recording_url is populated or max attempts reached.
        for _ in range(30):
            done = await client.browsers.get(browser.id)
            if done.recording_url:
                print(done.recording_url)  # signed link, valid one hour
                break
            await asyncio.sleep(2)
        else:
            print("no recording ready for this session")
    finally:
        await client.close()


asyncio.run(main())