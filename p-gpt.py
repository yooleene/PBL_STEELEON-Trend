import os
from pathlib import Path

from openai import OpenAI


def load_env(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

api_key = os.getenv("AIGPT_API_KEY")
if not api_key:
    raise RuntimeError("AIGPT_API_KEY is not set in .env")

client = OpenAI(
    api_key=api_key,
    base_url="http://aigpt.posco.net/gpgpta01-gpt/v1"
)

response = client.chat.completions.create(
    model="gpt-5.4",
    messages=[
        {"role": "user", "content": "안녕하세요!"}
    ]
)

print(response.choices[0].message.content)
