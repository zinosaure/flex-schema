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


def print_table(rows: list[dict[str, object]], columns: list[str]) -> None:
    if not rows:
        print("(no rows)")
        return

    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            value = row.get(col, "")
            widths[col] = max(widths[col], len(str(value)))

    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    print(header)
    print(separator)

    for row in rows:
        line = " | ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns)
        print(line)


def run_queries() -> None:
    start = time.time()
    connection = build_connection()
    attach_models(connection)
    log_step("attach", start)

    start = time.time()
    user_select = User.select()
    user_select.where(user_select.is_active.is_true())
    active_count = user_select.count()
    user_select.discard()
    log_step(f"active users count={active_count}", start)

    start = time.time()
    user_select = User.select()
    user_select.where(user_select.age > 30)
    user_select.where(user_select.country.is_not_empty())
    user_select.sort(user_select.age.desc())
    _ = user_select.fetch_all(current=2, results_per_page=25)
    user_select.discard()
    log_step("users where/sort/paginate", start)

    start = time.time()
    contact_select = Contact.select()
    contact_select.where(contact_select.label == "friend")
    contact_select.where(contact_select.is_favorite.is_false())
    contact_select.sort(contact_select.since_year.desc())
    _ = contact_select.fetch_all(current=1, results_per_page=50)
    contact_select.discard()
    log_step("contacts filter/paginate", start)

    start = time.time()
    profile_select = Profile.select()
    profile_select.where(profile_select.city.is_not_empty())
    _ = profile_select.fetch_all(current=3, results_per_page=30)
    profile_select.discard()
    log_step("profiles pagination", start)

    start = time.time()
    message_select = Message.select()
    message_select.where(message_select.is_read.is_false())
    message_select.sort(message_select.sent_at.desc())
    _ = message_select.fetch_all(current=1, results_per_page=50)
    message_select.discard()
    log_step("messages unread", start)

    start = time.time()
    group_select = Group.select()
    group_select.where(group_select.is_private.is_false())
    _ = group_select.fetch_all(current=1, results_per_page=20)
    group_select.discard()
    log_step("groups public", start)

    start = time.time()
    member_select = GroupMember.select()
    member_select.where(member_select.role == "member")
    _ = member_select.fetch_all(current=2, results_per_page=40)
    member_select.discard()
    log_step("group members", start)

    select = User.select()
    results_per_page = 15
    while True:
        raw = input("Page number (q to quit): ").strip()
        if raw.lower() in {"q", "quit", "exit", ""}:
            break

        try:
            current = int(raw)
        except ValueError:
            print("Please enter a valid page number.")
            continue

        select.discard()
        select.sort(select.age.desc())
        page = select.fetch_all(current=current, results_per_page=results_per_page)
        print(f"Page {current} with {results_per_page} items -> {len(page)} total results")
        rows = [
            {
                "id": item.id,
                "name": item.name,
                "email": item.email,
                "age": item.age,
                "country": item.country,
            }
            for item in page
        ]
        print_table(rows, ["id", "name", "email", "age", "country"])

    connection.close()


if __name__ == "__main__":
    run_queries()
