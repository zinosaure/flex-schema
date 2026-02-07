import json
import time
from pathlib import Path

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

SEED_USERS = 2000
SEED_CONTACTS = 2000
SEED_PROFILES = 2000
SEED_MESSAGES = 2000
SEED_GROUPS = 2000
SEED_GROUP_MEMBERS = 2000

INPUT_DIR = Path(__file__).resolve().parent / "inputs"


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


def wait_for_mysql(timeout_seconds: int = 60) -> None:
    start = time.time()
    last_error = None

    while True:
        try:
            connection = build_connection()
            connection.close()
            return
        except Exception as exc:
            last_error = exc
            if time.time() - start > timeout_seconds:
                raise RuntimeError(f"MySQL not ready after {timeout_seconds}s: {last_error}")
            time.sleep(2)


def load_seed_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_data.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_contacts_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_contacts.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_profiles_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_profiles.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_messages_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_messages.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_groups_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_groups.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_group_members_data() -> list[dict[str, object]]:
    seed_path = INPUT_DIR / "seed_group_members.json"
    with seed_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_user_ids(connection: pymysql.connections.Connection, table_name: str) -> dict[str, int]:
    sql = f"SELECT `_id`, `email` FROM `{table_name}`"
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return {row["email"]: int(row["_id"]) for row in rows if row.get("email")}


def load_group_ids(connection: pymysql.connections.Connection, table_name: str) -> dict[str, int]:
    sql = f"SELECT `_id`, `name` FROM `{table_name}`"
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()

    return {row["name"]: int(row["_id"]) for row in rows if row.get("name")}


def seed_users(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    User.attach(connection, USERS_TABLE)

    existing = User.count()
    if existing >= target_count:
        User.detach()
        return 0

    seed_data = load_seed_data()
    to_insert = target_count - existing
    inserted = 0

    index = 0
    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        user = User(**item)
        if user.commit():
            inserted += 1
        index += 1

    User.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def seed_contacts(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    user_ids = load_user_ids(connection, USERS_TABLE)
    if not user_ids:
        return 0

    Contact.attach(connection, CONTACTS_TABLE)

    existing = Contact.count()
    if existing >= target_count:
        Contact.detach()
        return 0

    seed_data = load_contacts_data()
    to_insert = target_count - existing
    inserted = 0

    index = 0
    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        user_email = str(item.get("user_email", ""))
        friend_email = str(item.get("friend_email", ""))
        user_id = user_ids.get(user_email)
        friend_id = user_ids.get(friend_email)
        if not user_id or not friend_id:
            index += 1
            continue
        contact = Contact(
            user_id=user_id,
            friend_id=friend_id,
            label=str(item.get("label", "friend")),
            since_year=int(item.get("since_year", 2020)),
            is_favorite=bool(item.get("is_favorite", False)),
        )
        if contact.commit():
            inserted += 1
        index += 1

    Contact.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def seed_profiles(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    user_ids = load_user_ids(connection, USERS_TABLE)
    if not user_ids:
        return 0

    Profile.attach(connection, PROFILES_TABLE)
    existing = Profile.count()
    if existing >= target_count:
        Profile.detach()
        return 0

    seed_data = load_profiles_data()
    to_insert = target_count - existing
    inserted = 0
    index = 0

    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        user_email = str(item.get("user_email", ""))
        user_id = user_ids.get(user_email)
        if not user_id:
            index += 1
            continue
        profile = Profile(
            user_id=user_id,
            phone=str(item.get("phone", "")),
            bio=str(item.get("bio", "")),
            city=str(item.get("city", "")),
            country=str(item.get("country", "")),
            interests=list(item.get("interests", [])),
        )
        if profile.commit():
            inserted += 1
        index += 1

    Profile.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def seed_groups(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    user_ids = load_user_ids(connection, USERS_TABLE)
    if not user_ids:
        return 0

    Group.attach(connection, GROUPS_TABLE)
    existing = Group.count()
    if existing >= target_count:
        Group.detach()
        return 0

    seed_data = load_groups_data()
    to_insert = target_count - existing
    inserted = 0
    index = 0

    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        owner_email = str(item.get("owner_email", ""))
        owner_id = user_ids.get(owner_email)
        if not owner_id:
            index += 1
            continue
        group = Group(
            name=str(item.get("name", "")),
            owner_id=owner_id,
            description=str(item.get("description", "")),
            is_private=bool(item.get("is_private", False)),
            created_at=str(item.get("created_at", "2024-01-01 00:00:00")),
        )
        if group.commit():
            inserted += 1
        index += 1

    Group.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def seed_group_members(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    group_ids = load_group_ids(connection, GROUPS_TABLE)
    user_ids = load_user_ids(connection, USERS_TABLE)
    if not group_ids or not user_ids:
        return 0

    GroupMember.attach(connection, GROUP_MEMBERS_TABLE)
    existing = GroupMember.count()
    if existing >= target_count:
        GroupMember.detach()
        return 0

    seed_data = load_group_members_data()
    to_insert = target_count - existing
    inserted = 0
    index = 0

    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        group_name = str(item.get("group_name", ""))
        user_email = str(item.get("user_email", ""))
        group_id = group_ids.get(group_name)
        user_id = user_ids.get(user_email)
        if not group_id or not user_id:
            index += 1
            continue
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=str(item.get("role", "member")),
            joined_at=str(item.get("joined_at", "2024-01-01 00:00:00")),
        )
        if member.commit():
            inserted += 1
        index += 1

    GroupMember.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def seed_messages(target_count: int) -> int:
    wait_for_mysql()
    connection = build_connection()
    user_ids = load_user_ids(connection, USERS_TABLE)
    if not user_ids:
        return 0

    Message.attach(connection, MESSAGES_TABLE)
    existing = Message.count()
    if existing >= target_count:
        Message.detach()
        return 0

    seed_data = load_messages_data()
    to_insert = target_count - existing
    inserted = 0
    index = 0

    while inserted < to_insert and seed_data:
        item = seed_data[index % len(seed_data)]
        sender_email = str(item.get("sender_email", ""))
        receiver_email = str(item.get("receiver_email", ""))
        sender_id = user_ids.get(sender_email)
        receiver_id = user_ids.get(receiver_email)
        if not sender_id or not receiver_id:
            index += 1
            continue
        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=str(item.get("subject", "")),
            body=str(item.get("body", "")),
            sent_at=str(item.get("sent_at", "2024-01-01 00:00:00")),
            is_read=bool(item.get("is_read", False)),
        )
        if message.commit():
            inserted += 1
        index += 1

    Message.detach()
    try:
        if getattr(connection, "open", False):
            connection.close()
    except Exception:
        pass
    return inserted


def main() -> None:
    target_users = SEED_USERS
    target_contacts = SEED_CONTACTS
    target_profiles = SEED_PROFILES
    target_groups = SEED_GROUPS
    target_group_members = SEED_GROUP_MEMBERS
    target_messages = SEED_MESSAGES

    inserted_users = seed_users(target_users)
    if inserted_users > 0:
        print(f"Seeded {inserted_users} users.")
    else:
        print("Users seed skipped: already has enough data.")

    inserted_profiles = seed_profiles(target_profiles)
    if inserted_profiles > 0:
        print(f"Seeded {inserted_profiles} profiles.")
    else:
        print("Profiles seed skipped: already has enough data.")

    inserted_contacts = seed_contacts(target_contacts)
    if inserted_contacts > 0:
        print(f"Seeded {inserted_contacts} contacts.")
    else:
        print("Contacts seed skipped: already has enough data.")

    inserted_groups = seed_groups(target_groups)
    if inserted_groups > 0:
        print(f"Seeded {inserted_groups} groups.")
    else:
        print("Groups seed skipped: already has enough data.")

    inserted_group_members = seed_group_members(target_group_members)
    if inserted_group_members > 0:
        print(f"Seeded {inserted_group_members} group members.")
    else:
        print("Group members seed skipped: already has enough data.")

    inserted_messages = seed_messages(target_messages)
    if inserted_messages > 0:
        print(f"Seeded {inserted_messages} messages.")
    else:
        print("Messages seed skipped: already has enough data.")


if __name__ == "__main__":
    main()
