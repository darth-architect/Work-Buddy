import asyncio, httpx, os

urls = {
    'Salesforce': os.getenv('SALESFORCE_MCP_URL'),
    'Okta': os.getenv('OKTA_MCP_URL'),
    'Azure': os.getenv('AZURE_MCP_URL'),
    'JSM': os.getenv('JSM_MCP_URL'),
}

async def check(name, url):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(url, json={})
            print(f'{name}: {url} -> HTTP {resp.status_code}')
    except Exception as e:
        print(f'{name}: {url} -> FAILED: {type(e).__name__}: {e}')

async def main():
    await asyncio.gather(*(check(n, u) for n, u in urls.items()))

asyncio.run(main())
