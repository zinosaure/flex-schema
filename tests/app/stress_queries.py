import time

import pymysql

from flexschema import Schema, Flexmodel, field, field_constraint

MYSQL_HOST = "mysql"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DATABASE = "testdb"

USERS_TABLE = "users"
CONTACTS_TABLE = "contacts"
PROFILES_TABLE = "profiles"
MESSAGES_TABLE = "messages"
GROUPS_TABLE = "groups"
GROUP_MEMBERS_TABLE = "group_members"


class User(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        email=field(str, nullable=False),
        age=field(int, default=0),
        is_active=field(bool, default=True),
        tags=field(list, default=[], constraint=field_constraint(item_type=str)),
        city=field(str, default="Unknown"),
        country=field(str, default="Unknown"),
        signup_at=field(str, default="2024-01-01 00:00:00"),
    )


class Contact(Flexmodel):
    schema: Schema = Schema.ident(
        user_id=field(int, nullable=False),
        friend_id=field(int, nullable=False),
        label=field(str, default="friend"),
        since_year=field(int, default=2020),
        is_favorite=field(bool, default=False),
    )


class Profile(Flexmodel):
    schema: Schema = Schema.ident(
        user_id=field(int, nullable=False),
        phone=field(str, default=""),
        bio=field(str, default=""),
        city=field(str, default=""),
        country=field(str, default=""),
        interests=field(list, default=[], constraint=field_constraint(item_type=str)),
    )


class Message(Flexmodel):
    schema: Schema = Schema.ident(
        sender_id=field(int, nullable=False),
        receiver_id=field(int, nullable=False),
        subject=field(str, default=""),
        body=field(str, nullable=False),
        sent_at=field(str, default="2024-01-01 00:00:00"),
        is_read=field(bool, default=False),
    )


class Group(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        owner_id=field(int, nullable=False),
        description=field(str, default=""),
        is_private=field(bool, default=False),
        created_at=field(str, default="2024-01-01 00:00:00"),
    )


class GroupMember(Flexmodel):
    schema: Schema = Schema.ident(
        group_id=field(int, nullable=False),
        user_id=field(int, nullable=False),
        role=field(str, default="member"),
        joined_at=field(str, default="2024-01-01 00:00:00"),
    )


def build_connection() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT,
        autocommit=True,
    )


def attach_models(connection: pymysql.connections.Connection) -> None:
    User.attach(connection, USERS_TABLE)
    Contact.attach(connection, CONTACTS_TABLE)
    Profile.attach(connection, PROFILES_TABLE)
    Message.attach(connection, MESSAGES_TABLE)
    Group.attach(connection, GROUPS_TABLE)
    GroupMember.attach(connection, GROUP_MEMBERS_TABLE)


def log_step(label: str, start: float) -> None:
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.3f}s")


def run_queries() -> None:
    start = time.time()
    connection = build_connection()
    attach_models(connection)
    log_step("attach", start)

    start = time.time()
    active_count = User.select().where(User.select().is_active.is_true()).count()
    log_step(f"active users count={active_count}", start)

    start = time.time()
    user_select = User.select()
    user_select.where(user_select.age > 30)
    user_select.where(user_select.country.is_not_empty())
    user_select.sort(user_select.age.desc())
    _ = user_select.fetch_all(current=2, results_per_page=25)
    log_step("users where/sort/paginate", start)

    start = time.time()
    contact_select = Contact.select()
    contact_select.where(contact_select.label == "friend")
    contact_select.where(contact_select.is_favorite.is_false())
    contact_select.sort(contact_select.since_year.desc())
    _ = contact_select.fetch_all(current=1, results_per_page=50)
    log_step("contacts filter/paginate", start)

    start = time.time()
    profile_select = Profile.select()
    profile_select.where(profile_select.city.is_not_empty())
    _ = profile_select.fetch_all(current=3, results_per_page=30)
    log_step("profiles pagination", start)

    start = time.time()
    message_select = Message.select()
    message_select.where(message_select.is_read.is_false())
    message_select.sort(message_select.sent_at.desc())
    _ = message_select.fetch_all(current=1, results_per_page=50)
    log_step("messages unread", start)

    start = time.time()
    group_select = Group.select()
    group_select.where(group_select.is_private.is_false())
    _ = group_select.fetch_all(current=1, results_per_page=20)
    log_step("groups public", start)

    start = time.time()
    member_select = GroupMember.select()
    member_select.where(member_select.role == "member")
    _ = member_select.fetch_all(current=2, results_per_page=40)
    log_step("group members", start)

    connection.close()


if __name__ == "__main__":
    run_queries()
