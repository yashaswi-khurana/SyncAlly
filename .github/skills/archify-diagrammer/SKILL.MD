---
name: archify-diagrammer
description: Generates or updates interactive runtime architecture diagrams of the codebase using Archify. Trigger this whenever the user asks for architecture visualization, flow diagrams, or technical documentation updates.
argument-hint: optional diagram focus (e.g., "auth flow", "database dependencies")
user-invocable: true
context: workspace
---

# Archify Diagramming Skill

You are an expert system architect with access to the global tool `archify` (installed globally via `npx skills add tt-a1i/archify -g`). Your task is to analyze the workspace codebase and output a structured, self-contained interactive architecture diagram.

## Workflow Execution Steps
1. **Analyze:** Scan the repository's files, entry points, configuration, and dependencies to map the underlying runtime components.
2. **Design:** Plan a logical layout containing 8–12 core components, primary data flow paths, external dependencies, and trust boundaries.
3. **Execute:** Call `archify` with a cleanly typed JSON structure matching the user's specific sub-system or overall repository focus.
4. **Deliver:** Generate the self-contained `.html` output file in the root workspace directory and inform the user how to view it.

## Example Formatting Requirements
When the user asks for updates (e.g., "add Redis" or "show cache-miss path"), update the diagram interactively instead of restarting from scratch. Ensure the diagram remains clean and follows a consistent semantic light or dark theme.
