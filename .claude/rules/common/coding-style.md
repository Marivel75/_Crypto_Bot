# Coding Style (Common)

## Universal Principles
- KISS: simplest solution that works; YAGNI: no speculative features
- Functions: single responsibility, max 50 lines
- Indentation: max 3 levels deep; extract to functions if deeper
- Naming: descriptive over clever; verb_noun for functions, noun for variables

## Structure
- Max 200-400 lines per file; split if larger
- No magic numbers — use named constants
- Comments only when intent is non-obvious; never paraphrase code

## Error Handling
- Fail fast on invalid inputs at system boundaries
- Never swallow exceptions silently
- Log full context server-side; return generic messages to clients

## Code Review Checklist
- [ ] No debug code left in (print, console.log, breakpoints)
- [ ] No hardcoded secrets or credentials
- [ ] All external inputs validated
- [ ] Error cases handled explicitly
