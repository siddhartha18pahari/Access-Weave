"""Revoke Supabase's public REST API access to the application's tables.

WHY THIS EXISTS
---------------
Supabase exposes every table in the `public` schema through PostgREST, and grants
the `anon` and `authenticated` roles access by default. The `anon` key is designed
to be embedded in frontend code, i.e. it is effectively public.

Django creates its tables in `public`, so without this migration anyone holding
the anon key can read:

  * auth_user          - usernames, emails, and password hashes
  * django_session     - session keys and payloads (session hijacking)
  * core_tasksession   - the private source text a user pasted or photographed
  * core_accessprofile - a user's accessibility preferences

That is a direct contradiction of this project's privacy promises, so the grants
are removed here rather than relying on a dashboard setting that is easy to lose.

AccessWeave talks to Postgres directly as the owner role and never uses PostgREST,
so removing these grants costs the application nothing.

This is written to be safe on non-Postgres backends (SQLite locally) and safe to
re-run: the roles may not exist outside Supabase.
"""
from django.db import migrations


LOCK_DOWN = """
DO $$
BEGIN
    -- Supabase-only roles; skip silently elsewhere (e.g. plain Postgres in CI).
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;
        REVOKE USAGE ON SCHEMA public FROM anon;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM authenticated;
        REVOKE USAGE ON SCHEMA public FROM authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM authenticated;
    END IF;
END
$$;
"""

def lock_down(apps, schema_editor):
    # SQLite (local dev and CI) has no roles or GRANTs — this is Postgres-only.
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(LOCK_DOWN)


def noop(apps, schema_editor):
    """Deliberately not reversed: re-granting public API access to user tables
    would reintroduce the vulnerability."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(lock_down, noop),
    ]
