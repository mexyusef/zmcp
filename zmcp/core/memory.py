"""
ZMCP Memory Module

Provides persistent memory storage for the ZMCP application.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global memory store
memory_store: Dict[str, str] = {}

# Path to memory file
MEMORY_FILE = os.path.join(os.path.expanduser("~"), ".zmcp", "memory.json")


def load_memory() -> None:
    """Load memory from file."""
    global memory_store

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

        # Load memory if file exists
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memory_store = json.load(f)
                logger.info(f"Loaded {len(memory_store)} memories from {MEMORY_FILE}")
        else:
            memory_store = {}
            logger.info(f"No memory file found at {MEMORY_FILE}, starting with empty memory")
    except Exception as e:
        logger.error(f"Error loading memory: {e}")
        memory_store = {}


def save_memory() -> None:
    """Save memory to file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)

        # Save memory
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory_store, f, indent=2)
            logger.info(f"Saved {len(memory_store)} memories to {MEMORY_FILE}")
    except Exception as e:
        logger.error(f"Error saving memory: {e}")


def get_memory(key: str) -> Optional[str]:
    """Get memory by key."""
    return memory_store.get(key)


def set_memory(key: str, value: str) -> None:
    """Set memory by key and save to file."""
    memory_store[key] = value
    save_memory()


def delete_memory(key: str) -> bool:
    """Delete memory by key and save to file."""
    if key in memory_store:
        del memory_store[key]
        save_memory()
        return True
    return False


def search_memory(query: str) -> Dict[str, str]:
    """Search memory by query."""
    results = {}
    for key, value in memory_store.items():
        if query.lower() in key.lower() or query.lower() in value.lower():
            results[key] = value
    return results


def clear_memory() -> int:
    """Clear all memories and save to file."""
    count = len(memory_store)
    memory_store.clear()
    save_memory()
    return count


# Load memory on module import
load_memory()
