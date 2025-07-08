# utilities.py
import os
import json
import sys
import logging
from rich import print as rprint
from rich.syntax import Syntax
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def read_config_json():
    config_path = os.getenv("THEAILANGUAGE_CONFIG") or os.path.join(os.path.dirname(__file__), "theailanguage_config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read config file: {e}")
        sys.exit(1)

def print_json_response(response, title: str):
    print(f"\n=== {title} ===")
    try:
        if hasattr(response, "root"):
            data = response.root.model_dump(mode="json", exclude_none=True)
        else:
            data = response.model_dump(mode="json", exclude_none=True)
        syntax = Syntax(json.dumps(data, indent=2, ensure_ascii=False), "json", theme="monokai", line_numbers=False)
        rprint(syntax)
    except Exception as e:
        rprint(f"[red bold]Error printing JSON:[/red bold] {e}")
        rprint(repr(response))