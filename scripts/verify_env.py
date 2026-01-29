import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_PATTERN = re.compile(r"\${([A-Z0-9_]+):\?[^}]+}")


def extract_required_vars(compose_text):
    return sorted(set(REQUIRED_PATTERN.findall(compose_text or "")))


def load_env_file(path):
    env = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def main():
    parser = argparse.ArgumentParser(description="Verify required env vars for docker compose stack.")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--compose", default="docker/docker-compose.yml")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        print("Missing .env file. Run: copy .env.example .env", file=sys.stderr)
        return 2

    compose_path = Path(args.compose)
    if not compose_path.exists():
        print(f"Compose file not found: {compose_path}", file=sys.stderr)
        return 2

    compose_text = compose_path.read_text(encoding="utf-8")
    required_vars = extract_required_vars(compose_text)
    env = load_env_file(env_path)

    missing = []
    for var in required_vars:
        value = env.get(var) or os.environ.get(var)
        if value is None or value == "":
            missing.append(var)

    if missing:
        print("Missing required env vars:")
        for var in missing:
            print(f"- {var}")
        return 3

    print("Environment OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
