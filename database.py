import asyncpg
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

pool: asyncpg.Pool | None = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        min_size=1,
        max_size=5
    )
    async with pool.acquire() as conn:
        await conn.execute(""" 
            CREATE TABLE IF NOT EXISTS habits (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                count INTEGER DEFAULT 0)
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY,
                reminders_enabled BOOLEAN DEFAULT FALSE,
                reminder_time TIME DEFAULT '20:00')
        """)
        await conn.execute("""
            ALTER TABLE habits
            ADD COLUMN IF NOT EXISTS streak INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS last_done DATE
        """)
        await conn.execute("""
            ALTER TABLE user_settings
            ADD COLUMN IF NOT EXISTS reminder_days TEXT DEFAULT 'all'
        """)

async def get_user_habits(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT id, name, count, streak, last_done FROM habits WHERE user_id = $1 ORDER BY id",
            user_id
        )

async def get_stats(user_id: int):
    async with pool.acquire() as conn:
        total = await conn.fetchrow(
            "SELECT COUNT(*) AS habits, COALESCE(SUM(count), 0) AS total_done "
            "FROM habits WHERE user_id = $1",
            user_id)

        best_streak = await conn.fetchrow(
            "SELECT name, streak FROM habits "
            "WHERE user_id = $1 ORDER BY streak DESC LIMIT 1",
            user_id
        )

        top_habits = await conn.fetch(
            "SELECT name, count FROM habits "
            "WHERE user_id = $1 ORDER BY count DESC LIMIT 3",
            user_id
        )

        avg_streak = await conn.fetchval(
            "SELECT COALESCE(AVG(streak), 0) FROM habits WHERE user_id = $1",
            user_id
        )
    return total, best_streak, top_habits, avg_streak

async def get_week_stats(user_id: int):
    async with pool.acquire() as conn:
        week_done = await conn.fetchrow(
            """
            SELECT COUNT(*) AS done
            FROM habits
            WHERE user_id = $1
              AND last_done >= CURRENT_DATE - INTERVAL '7 days'
            """,
            user_id
        )

        top_week = await conn.fetch(
            """
            SELECT name, COUNT(*) AS cnt
            FROM habits
            WHERE user_id = $1
              AND last_done >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY name
            ORDER BY cnt DESC
            LIMIT 3
            """,
            user_id
        )

    return week_done["done"], top_week

async def set_reminder(user_id: int, enabled: bool):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_settings (user_id, reminders_enabled)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET reminders_enabled = $2
            """,
            user_id, enabled
        )

async def set_reminder_with_time(user_id: int, enabled: bool, time: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_settings (user_id, reminders_enabled, reminder_time)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id)
            DO UPDATE SET
                reminders_enabled = $2,
                reminder_time = $3
            """,
            user_id, enabled, time
        )

async def set_reminder_schedule(user_id: int, days: str):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE user_settings
            SET reminder_days = $2
            WHERE user_id = $1
            """,
            user_id, days
        )

async def get_users_with_reminders():
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT user_id, reminder_time, reminder_days
            FROM user_settings
            WHERE reminders_enabled = TRUE
            """
        )

async def get_user_settings(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT reminders_enabled, reminder_time FROM user_settings WHERE user_id = $1",
            user_id
        )