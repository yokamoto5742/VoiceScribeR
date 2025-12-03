import os
from pathlib import Path


def load_env_variables() -> dict:
    base_dir = Path(__file__).parent.parent
    env_path = os.path.join(base_dir, '.env')

    env_vars = {}

    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip('"\'')
    else:
        print("警告: .envファイルが見つかりません。")

    return env_vars
