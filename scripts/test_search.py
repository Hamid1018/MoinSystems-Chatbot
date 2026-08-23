import sys
import os
import asyncio

# Add the root directory to the python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.search_service import SearchService

async def run_test():
    print("\n--- Testing RAG Vector Search ---")
    
    # You can change this question to anything you want to test!
    user_query = "Can you help me build a custom mobile app for my e-commerce store?"
    
    print(f"\nUser Query: '{user_query}'\n")
    print("Searching database for nearest vectors...")
    
    # Execute the search
    results = await SearchService.search(user_query, limit=3)

    print("\n✅ Found Relevant Context:")
    for i, res in enumerate(results, 1):
        print(f"\n[Result {i} | Category: {res['category']}]")
        print(f"Content: {res['content']}")

if __name__ == "__main__":
    asyncio.run(run_test())