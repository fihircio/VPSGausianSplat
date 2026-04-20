# Agent Handoff Protocol (v1.0)

As part of the **Scaling VPS Clinical Dashboard** objective, all specialized agents must adhere to the following behavioral standards:

## 1. Research & Planning Phase
- Every task must begin with a thorough research phase using `grep`, `ls`, and `view_file`.
- Agents must present an **Implementation Plan** and wait for explicitly stated USER approval before writing any code.
- If existing files are outside the "Allowed" list but are necessary for a fix, the agent must ask for permission first.

## 2. Behavioral Constraints
- **Preserve Documentation**: Do not remove comments, docstrings, or license headers.
- **Atomic Commits**: If multiple disconnected features are requested, implement them one by one.
- **Safety**: Do not run `rm -rf` or other destructive commands without verification.

## 3. Session Completion
- Every session must end with a `validation_report_agent_N.md` (where N is the agent's assigned number or role).
- The report must include a summary of changes, manual/automated verification results, and any open debt.
