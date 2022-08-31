from typing import Dict
import sqlite3
from redis import Redis
from tqdm import tqdm
import json
from discord import Message

import config
from parrot.redis.avatar_manager import AvatarManager as RedisAvatarManager
from parrot.redis.corpus_manager import CorpusManager as RedisCorpusManager
from parrot.redis.redis_set import RedisSet
from parrot.sqlite.corpus_manager import CorpusManager as SqliteCorpusManager

print("Logging into the Redis database...")
redis = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    password=config.REDIS_PASSWORD,
    decode_responses=True,
)

print("Connecting to the sqlite database...")
con = sqlite3.connect("parrot.sqlite3")
con.isolation_level = None  # autocommit mode


print("Creating tables if they don't exist...")
con.executescript("""
    BEGIN;
    CREATE TABLE IF NOT EXISTS users (
        id                         INTEGER PRIMARY KEY,
        is_registered              INTEGER NOT NULL DEFAULT 0,
        original_avatar_url        TEXT,
        modified_avatar_url        TEXT,
        modified_avatar_message_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS channels (
        id             INTEGER PRIMARY KEY,
        can_speak_here INTEGER NOT NULL DEFAULT 0,
        can_learn_here INTEGER NOT NULL DEFAULT 0,
        webhook_id     INTEGER
    );

    CREATE TABLE IF NOT EXISTS messages (
        id        INTEGER PRIMARY KEY,
        user_id   INTEGER NOT NULL REFERENCES users(id),
        timestamp INTEGER NOT NULL,
        content   TEXT    NOT NULL
    );
    COMMIT;
""")


print("Instantiating data structures...")
redis_corpora = RedisCorpusManager(redis)
sqlite_corpora = SqliteCorpusManager(con)
redis_avatars = RedisAvatarManager(redis)
redis_registered_users = RedisSet(redis, "registered_users")
redis_learning_channels = RedisSet(redis, "learning_channels")
redis_speaking_channels = RedisSet(redis, "speaking_channels")

print("Collecting corpus keys...", end="")
corpus_keys = redis.keys("corpus:*")
print(f" ✅ {len(corpus_keys)} keys")

for user_id in tqdm(redis_registered_users, "User registration"):
    con.execute("INSERT INTO users (id, is_registered) VALUES (?, ?)", (user_id, 1))

for key in tqdm(corpus_keys, "Corpora"):
    user_id = int(key.split(":")[1])
    corpus: Dict[int, str] = redis.hgetall(f"corpus:{user_id}")
    for message_id, content in tqdm(corpus.items(), f"User {user_id}"):
        # Timestamp was not stored in the old database, but I want it in the new
        # one, so I'm just going to put 0 for now.
        con.execute("""
            INSERT INTO messages (id, user_id, timestamp, content)
            VALUES (?, ?, ?, ?)""",
            (message_id, user_id, 0, content)
        )

for i, thing in enumerate(tqdm(redis.hgetall("avatars"), "Avatars")):
    if i % 2 == 0:
        user_id = int(thing)
        continue
    else:
        ledger = json.loads(thing)
    sql = """
        UPDATE users
        SET original_avatar_url = ?,
            modified_avatar_url = ?,
            modified_avatar_message_id = ?
        WHERE id = ?
    """
    con.execute(sql, (
        ledger["original_avatar_url"],
        ledger["modified_avatar_url"],
        ledger["source_message_id"],
        user_id
    ))

for channel_id in tqdm(redis_speaking_channels, "Speaking permissions"):
    con.execute("INSERT INTO channels (id, can_speak_here) VALUES (?, ?)", (channel_id, 1))

for channel_id in tqdm(redis_learning_channels, "Learning permissions"):
    con.execute("INSERT INTO channels (id, can_learn_here) VALUES (?, ?)", (channel_id, 1))

# for channel_id in tqdm(redis_speaking_channels, "Webhooks"):
# webhooks are funny, because parrot doesn't actually store them; it just gets
# each url on the fly by searching through the channel's list of webhooks on
# discord. might be easier to poke at parrot while its live than to bring in all
# the discord bot code here just to get at this data.


con.close()
