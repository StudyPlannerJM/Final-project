import os
import subprocess
import sys
import time
from typing import List


def _get_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        print(
            f"Invalid integer for {name}: {raw}. "
            f"Using default {default}."
        )
        return default


def _run_with_retries(
    command: List[str], retries: int, delay_seconds: int
) -> None:
    printable_command = " ".join(command)
    for attempt in range(1, retries + 1):
        print(
            "Running command "
            f"(attempt {attempt}/{retries}): {printable_command}"
        )
        result = subprocess.run(command, check=False)
        if result.returncode == 0:
            return

        if attempt < retries:
            print(
                f"Command failed with exit code {result.returncode}. "
                f"Retrying in {delay_seconds} seconds..."
            )
            time.sleep(delay_seconds)

    raise SystemExit(
        f"Command failed after {retries} attempts: {printable_command}"
    )


def _build_gunicorn_command() -> List[str]:
    command: List[str] = [sys.executable, "-m", "gunicorn", "run:app"]

    port = os.environ.get("PORT")
    if port:
        command.extend(["--bind", f"0.0.0.0:{port}"])

    workers = os.environ.get("WEB_CONCURRENCY")
    if workers:
        command.extend(["--workers", workers])

    timeout = os.environ.get("GUNICORN_TIMEOUT")
    if timeout:
        command.extend(["--timeout", timeout])

    return command


def main() -> None:
    migration_retries = _get_int_env("MIGRATION_MAX_RETRIES", 6)
    migration_retry_delay = _get_int_env("MIGRATION_RETRY_SECONDS", 5)

    flask_base = [sys.executable, "-m", "flask", "--app", "run.py"]

    _run_with_retries(
        flask_base + ["db", "upgrade"],
        retries=migration_retries,
        delay_seconds=migration_retry_delay,
    )

    _run_with_retries(
        flask_base + ["verify-schema"],
        retries=1,
        delay_seconds=0,
    )

    seed_default_users = (
        os.environ.get(
            "SEED_DEFAULT_USERS_PRODUCTION",
            "false",
        ).lower() == "true"
    )
    if seed_default_users:
        print("SEED_DEFAULT_USERS_PRODUCTION enabled. Seeding users...")
        _run_with_retries(
            flask_base + ["seed-default-users"],
            retries=1,
            delay_seconds=0,
        )

    validate_only = (
        os.environ.get("STARTUP_VALIDATE_ONLY", "false").lower() == "true"
    )
    if validate_only:
        print("Startup validation complete. Skipping gunicorn launch.")
        return

    gunicorn_command = _build_gunicorn_command()
    print(f"Starting gunicorn: {' '.join(gunicorn_command)}")
    os.execvp(gunicorn_command[0], gunicorn_command)


if __name__ == "__main__":
    main()
