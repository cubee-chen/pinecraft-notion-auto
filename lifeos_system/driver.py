import asyncio

FETCH_INTERVAL = 1 # seconds

async def driver():
    # runs every FETCH_INTERVAL seconds
    print("Hello, World!")

async def main():
    while True:
        await driver()
        await asyncio.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())