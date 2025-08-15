from cachetools import TTLCache

# cache key -> text (post-clean)
# tune maxsize/ttl as you like
ingest_cache = TTLCache(maxsize=256, ttl=60 * 60)  # 1 hour