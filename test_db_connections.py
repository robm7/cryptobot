import os
import asyncpg
import redis
from dotenv import load_dotenv

load_dotenv()

async def test_postgresql():
    try:
        conn = await asyncpg.connect(os.getenv('DATABASE_URI'))
        print("✅ PostgreSQL connection successful")
        await conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")

def test_redis():
    try:
        r = redis.Redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT')),
            decode_responses=True
        )
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_postgresql())
    test_redis()