"""Hive Console — an app-controlled command interface.

This module parses and executes a small, fixed set of safe commands against the
Hive|Mind store. It is NOT a shell. It never spawns processes, never touches the
filesystem directly, and never evaluates arbitrary code. Parsing is done with
``shlex`` purely to split quoted arguments; nothing is executed by the OS.

Commands that look like system/shell invocations (rm, powershell, bash, git,
npm, del, Remove-Item, ...) are rejected with a controlled error.
"""

import shlex
from typing import Any, Callable

from app.store.store import HiveStore

# First-token denylist. The parser is already a strict whitelist, so these can
# never run — this list exists to return a clear, controlled error when a user
# (or an attacker) tries an obvious system command.
UNSAFE_KEYWORDS: frozenset[str] = frozenset(
    {
        "rm", "rmdir", "del", "erase", "remove-item", "ri",
        "powershell", "pwsh", "bash", "sh", "zsh", "cmd", "command", "exec", "eval",
        "git", "npm", "npx", "yarn", "pnpm", "pip", "pip3", "node", "deno",
        "python", "python3", "ruby", "perl", "make",
        "curl", "wget", "scp", "ssh", "ftp", "nc", "telnet",
        "mv", "move", "cp", "copy", "ren", "rename", "ln", "mkdir", "touch",
        "chmod", "chown", "icacls", "attrib",
        "sudo", "su", "runas", "kill", "taskkill", "stop-process",
        "dd", "format", "mkfs", "fdisk", "diskpart", "reg", "regedit",
        "apt", "apt-get", "yum", "dnf", "brew", "choco", "winget", "snap",
        "systemctl", "service", "sc", "shutdown", "reboot", "set-content",
        "out-file", "invoke-expression", "iex", "start-process", "new-item",
    }
)

USAGE = {
    "help": "help",
    "status": "status",
    "list": 'list <type>   (sources|nodes|edges|models|activity)',
    "find": "find <query>",
    "show": "show <id>",
    "tag": "tag <id> <tag>",
    "link": "link <sourceId> <targetId>",
    "add": 'add note "<text>"',
}


class HiveConsole:
    """Executes safe console commands against an injected :class:`HiveStore`."""

    def __init__(self, store: HiveStore) -> None:
        self._store = store

    # ------------------------------------------------------------------ #
    # Public entry point
    # ------------------------------------------------------------------ #
    def execute(self, raw_command: str) -> dict[str, Any]:
        raw = (raw_command or "").strip()
        if not raw:
            return self._error("empty", "Empty command. Type 'help' for available commands.")

        try:
            tokens = shlex.split(raw)
        except ValueError as exc:
            return self._error("malformed", f"Could not parse command: {exc}")
        if not tokens:
            return self._error("empty", "Empty command. Type 'help' for available commands.")

        keyword = tokens[0].lower()

        if keyword in UNSAFE_KEYWORDS:
            return self._error(
                "blocked",
                f"Unsafe command '{tokens[0]}' is not permitted. "
                "The Hive Console does not execute system, shell, git, npm, or filesystem commands.",
            )

        handler: Callable[[list[str]], dict[str, Any]] | None = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "list": self._cmd_list,
            "find": self._cmd_find,
            "show": self._cmd_show,
            "tag": self._cmd_tag,
            "link": self._cmd_link,
            "add": self._cmd_add,
        }.get(keyword)

        if handler is None:
            return self._error(
                "unknown",
                f"Unknown command '{tokens[0]}'. Type 'help' for available commands.",
            )
        return handler(tokens)

    # ------------------------------------------------------------------ #
    # Command handlers
    # ------------------------------------------------------------------ #
    def _cmd_help(self, tokens: list[str]) -> dict[str, Any]:
        return self._ok("help", {"commands": list(USAGE.values())})

    def _cmd_status(self, tokens: list[str]) -> dict[str, Any]:
        status = self._store.system_status().model_dump(mode="json")
        return self._ok("status", {"status": status, "stats": self._store.stats()})

    def _cmd_list(self, tokens: list[str]) -> dict[str, Any]:
        if len(tokens) < 2:
            return self._error("list", f"Usage: {USAGE['list']}")
        record_type = tokens[1]
        try:
            records = self._store.list_records(record_type)
        except ValueError as exc:
            return self._error("list", str(exc))
        items = [r.model_dump(mode="json") for r in records]
        return self._ok("list", {"type": record_type.lower(), "count": len(items), "items": items})

    def _cmd_find(self, tokens: list[str]) -> dict[str, Any]:
        query = " ".join(tokens[1:]).strip()
        if not query:
            return self._error("find", f"Usage: {USAGE['find']}")
        results = self._store.search(query)
        matches = {k: [r.model_dump(mode="json") for r in v] for k, v in results.items()}
        total = sum(len(v) for v in matches.values())
        return self._ok("find", {"query": query, "count": total, "matches": matches})

    def _cmd_show(self, tokens: list[str]) -> dict[str, Any]:
        if len(tokens) < 2:
            return self._error("show", f"Usage: {USAGE['show']}")
        record_id = tokens[1]
        found = self._store.get_record(record_id)
        if found is None:
            return self._error("show", f"Record '{record_id}' not found")
        record_type, record = found
        return self._ok("show", {"type": record_type, "record": record.model_dump(mode="json")})

    def _cmd_tag(self, tokens: list[str]) -> dict[str, Any]:
        if len(tokens) < 3:
            return self._error("tag", f"Usage: {USAGE['tag']}")
        node_id, tag = tokens[1], tokens[2]
        try:
            node = self._store.add_tag(node_id, tag)
        except ValueError as exc:
            return self._error("tag", str(exc))
        return self._ok("tag", {"id": node.id, "tags": node.tags, "message": "Tag added"})

    def _cmd_link(self, tokens: list[str]) -> dict[str, Any]:
        if len(tokens) < 3:
            return self._error("link", f"Usage: {USAGE['link']}")
        source_id, target_id = tokens[1], tokens[2]
        try:
            edge = self._store.link_nodes(source_id, target_id)
        except ValueError as exc:
            return self._error("link", str(exc))
        return self._ok(
            "link",
            {
                "id": edge.id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "relationship": edge.relationship.value,
                "message": "Link created",
            },
        )

    def _cmd_add(self, tokens: list[str]) -> dict[str, Any]:
        if len(tokens) < 2 or tokens[1].lower() != "note":
            return self._error("add", f"Usage: {USAGE['add']}")
        text = " ".join(tokens[2:]).strip()
        if not text:
            return self._error("add note", f"Usage: {USAGE['add']}")
        try:
            node = self._store.create_note(text)
        except ValueError as exc:
            return self._error("add note", str(exc))
        return self._ok("add note", {"type": "note", "id": node.id, "message": "Note created"})

    # ------------------------------------------------------------------ #
    # Result helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _ok(command: str, result: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "command": command, "result": result, "error": None}

    @staticmethod
    def _error(command: str, message: str) -> dict[str, Any]:
        return {"ok": False, "command": command, "result": None, "error": message}
