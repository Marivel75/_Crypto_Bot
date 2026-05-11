# Skills LN inventory

> Generated 2026-05-11 — W4 task (session cry-3)

## Statut par skill

| Skill | Présent ? | Namespace / Emplacement | Description (boot context) | Fallback OMC si absent |
|---|---|---|---|---|
| `ln-625-dependencies-auditor` | OUI | `codebase-audit-suite:ln-625-dependencies-auditor` | Checks outdated packages, unused deps, CVE | `security-reviewer` + `document-specialist` (CVE refs) |
| `ln-644-dependency-graph-auditor` | OUI | `codebase-audit-suite:ln-644-dependency-graph-auditor` | Builds dependency graph, detects cycles | `mcp__hex-graph__analyze_architecture` + `mcp__hex-graph__trace_dataflow` |
| `ln-642-layer-boundary-auditor` | OUI | `codebase-audit-suite:ln-642-layer-boundary-auditor` | Checks layer boundary violations | `architect` (audit boundaries) + `code-reviewer` |
| `ln-621-security-auditor` | OUI | `codebase-audit-suite:ln-621-security-auditor` | Checks hardcoded secrets, SQL injection, OWASP | `security-reviewer` (natif OMC) |
| `ln-622-build-auditor` | OUI | `codebase-audit-suite:ln-622-build-auditor` | Checks compiler/linter errors, Dockerfile hygiene | `code-reviewer` + `devops` |
| `ln-761-secret-scanner` | OUI | `project-bootstrap:ln-761-secret-scanner` | Scans codebase for hardcoded secrets | `security-reviewer` (couvre secrets) |

## Sources vérifiées

| Source | Résultat |
|---|---|
| AO plugins (`ao plugin list`) | 0 match — aucun plugin ln-* dans le marketplace AO |
| AO plugin search (`ao plugin search`) | 0 match pour chaque skill + mots-clés "auditor"/"scanner" |
| Claude Code skill registry (boot context) | **6/6 présents** — namespace `codebase-audit-suite` (5) + `project-bootstrap` (1) |
| `~/.claude/` global config (boot context) | Skills listés dans le system-reminder au boot, invocables via `/codebase-audit-suite:<skill>` ou `/project-bootstrap:<skill>` |
| Project `.claude/commands/` | Absent (pas de skills ln-* locaux au projet) |

## Recommandation orchestration

### Tous les skills sont présents — pas besoin de fallback OMC

Les 6 skills `ln-*` ciblés sont disponibles comme skills Claude Code (oh-my-claudecode). Ils sont invocables directement par tout agent Claude Code dans une session.

**Conséquence pour le playbook V1→V2** : les références `ln-*` sont valides et peuvent être conservées telles quelles. Pas de réécriture fallback nécessaire.

### Fallback OMC — conservé à titre de référence

Le mapping fallback ci-dessus reste pertinent pour :
- Les environnements où oh-my-claudecode n'est pas installé
- Les agents AO non-Claude (codex, aider, opencode, kimicode) qui n'ont pas accès aux skills Claude Code
- La dégradation gracieuse si un skill est retiré dans une future version OMC

## Commande de boot (worker-side, à inclure dans prompts Phase 1/Phase 4)

Les skills sont auto-disponibles dans toute session Claude Code avec OMC installé. Pour les invoquer explicitement dans un prompt worker :

```bash
# Phase 1 — Audit dependencies + security
/codebase-audit-suite:ln-625-dependencies-auditor
/codebase-audit-suite:ln-621-security-auditor
/project-bootstrap:ln-761-secret-scanner

# Phase 4 — Architecture + build audit
/codebase-audit-suite:ln-644-dependency-graph-auditor
/codebase-audit-suite:ln-642-layer-boundary-auditor
/codebase-audit-suite:ln-622-build-auditor
```

Pour un worker AO non-Claude, utiliser les fallbacks OMC :

```
# Fallback — agent subagent_type mapping
ln-625 → Agent(subagent_type="security-reviewer") + Agent(subagent_type="document-specialist")
ln-644 → mcp__hex-graph__analyze_architecture + mcp__hex-graph__trace_dataflow
ln-642 → Agent(subagent_type="architect") + Agent(subagent_type="code-reviewer")
ln-621 → Agent(subagent_type="security-reviewer")
ln-622 → Agent(subagent_type="code-reviewer") # + devops context in prompt
ln-761 → Agent(subagent_type="security-reviewer") # secrets scope in prompt
```
