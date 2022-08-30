from typing import List, Union, cast
# from utils.types import CorpusManagerInterface
from discord import Message
# from exceptions import Exception, NotRegisteredError


class CorpusManager:
    def __init__(self, db):
        self.db = db


    def add(self, user_id: int, messages: Union[Message, List[Message]]) -> int:
        """
        Record messages locally.
        @pre: messages should all be from one user.
        @returns: the number of new messages added.
        TODO: If the user's Markov Chain is cached, update it with the new
        information too.
        """
        # self.assert_registered(user)

        if not isinstance(messages, list):
            messages = [messages]

        # TODO: Uncomment when model.update() is implemented
        # model = self.bot.get_model(user.id)

        # Also learn from text inside embeds, if the user is a bot.
        # If it's not from a bot, it's probably just YouTube descriptions and
        # not worth learning from.
        for message in messages:
            if message.author.bot:
                for embed in message.embeds:
                    desc = embed.description
                    if isinstance(desc, str):
                        message.content += "\n" + desc

        self.db.execute("""
            INSERT INTO messages (id, user_id, timestamp, content)
            VALUES (?, ?, ?, ?)""",
            [(message.id, user_id, message.created_at, message.content) for message in messages]
        )

        # Return the number of new messages this added to the database.
        # Not necessarily the number of messages passed in.
        res = self.db.execute("SELECT CHANGES()")
        return res.fetchone()[0]


    def get(self, user_id: int) -> List[str]:
        """ Get a corpus from the local database by user ID. """
        # self.assert_registered(user)
        res = self.db.execute(
            "SELECT content FROM messages WHERE user_id = ?", (user_id,)
        )
        corpus = [row[0] for row in res]
        if len(corpus) == 0:
            raise Exception(f"No data available for user with ID {user_id}.")
        return corpus


    def delete(self, user_id: int) -> None:
        """ Delete a corpus from the local database. """
        self.db.execute(
            "DELETE FROM messages WHERE user_id = ?", (user_id,)
        )
        res = self.db.execute("SELECT CHANGES()")
        num_deleted = res.fetchone()[0]
        if num_deleted == 0:
            raise Exception(f"No data available for user with ID {user_id}.")


    def delete_message(self, message_id: int) -> None:
        """ Delete a message from the local database. """
        self.db.execute(
            "DELETE FROM messages WHERE id = ?", (message_id,)
        )
        res = self.db.execute("SELECT CHANGES()")
        num_deleted = res.fetchone()[0]
        if num_deleted == 0:
            raise Exception(f"Message with ID {message_id} did not exist in the first place.")


    def has(self, user_id: int) -> bool:
        """ Check if the database contains any messages from a user. """
        res = self.db.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)
        )
        return res.fetchone()[0] > 0


    # def assert_registered(self, user: Union[User, Member]) -> None:
    #     if not user.bot and user.id not in self.get_registered_users():
    #         raise NotRegisteredError(f"User {user} is not registered. To register, read the privacy policy with `{self.command_prefix}policy`, then register with `{self.command_prefix}register`.")
