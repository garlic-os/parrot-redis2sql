import config
import logging
import sqlite3
import atexit
from redis import Redis
import parrot

logging.info("Logging into the Redis database...")
redis = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    decode_responses=True,
)

logging.info("Connecting to the sqlite database...")
con = sqlite3.connect(os.path.join("database", "parrot.db"))
con.isolation_level = None  # autocommit mode

redis_corpora = parrot.redis.corpus_manager.CorpusManager(redis)
sqlite_corpora = parrot.sqlite.corpus_manager.CorpusManager(con)

corpus_keys = redis.keys("corpus:*")
for key in corpus_keys:
    user_id = int(key.split(":")[1])
    corpus: List[Message] = redis_corpora.get(user_id)
    sqlite_corpora.add(user_id, sqlite_corpora.get(user_id))



atexit.register(con.close)
