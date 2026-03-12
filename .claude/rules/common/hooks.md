# Claude Code Hooks (Common)

## Hook Types
- **PreToolUse**: run before a tool executes (can block)
- **PostToolUse**: run after a tool completes (observes result)
- **Stop**: run when a session ends
- **SubagentStop**: run when a subagent completes

## Active Hooks (this config)

### PostToolUse: Python ruff format
- Trigger: Edit or Write on `.py` files
- Action: `~/.claude/hooks/python-ruff-format.js`
- Effect: auto-format + lint-fix Python files after every edit

### Stop: Session logger
- Action: `~/.claude/hooks/session-summary.js`
- Effect: logs session info to `memory/sessions.log`

### PostToolUse: SPARV progress save
- Trigger: Edit|Write|Bash|Read|Glob|Grep when `.sparv/state.yaml` exists
- Effect: saves progress checkpoint for SPARV skill

## Writing Custom Hooks
```json
{
  "matcher": "Edit|Write",
  "hooks": [{
    "type": "command",
    "command": "node ~/.claude/hooks/my-hook.js"
  }]
}
```
- Hooks receive tool data via stdin as JSON
- Exit 0 to allow, non-zero to block (PreToolUse only)
- Always exit cleanly — errors should not block workflow
