---
name: fabric-teams
description: Design lean Hermes Bot teams with distinct roles.
version: 0.1.0
author: Marcos Lopes (MarcosAlves90), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bots, teams, delegation, roles, profiles]
    related_skills: [fabric]
---

# Fabric Teams

Design the smallest persistent Bot team that can own a durable outcome. This skill covers team composition, role boundaries, creation inputs and readiness reporting; it does not authorize extra profiles or powers.

## When to Use

- The user needs multiple persistent Bot owners with separate responsibilities, state or configuration.
- A durable outcome needs coordinated work and explicit ownership handoffs.
- Don't use a team for a one-off task, a repeatable procedure that fits a skill, or work an existing Bot can own; use delegation, a skill, or that Bot instead.

## Procedure

1. **Define the durable outcome and boundary.** State what the team must deliver, what is out of scope, and why persistent ownership is useful. A request for a "team" does not justify a preset headcount.
2. **Survey before designing.** Call `list_agents`; inspect relevant existing Bots, skills and routines through the available Hermes surfaces. Reuse an existing owner or routine when it covers the need. Existing Bots are not new team members: `create_team` builds only new member profiles. Reuse an existing lead with `lead_name` when appropriate; a lead is optional.
3. **Choose the smallest topology.** Add only roles needed for the durable outcome. Give every role a distinct, non-overlapping owner, concrete output, and handoff recipient/condition. Resolve overlaps by narrowing or reusing a role, not by multiplying profiles. If one new owner suffices, use `create_agent`, not `create_team`. `create_team` requires at least one new member and supports at most six new members; never fill the limit just because it exists.
4. **Get explicit creation inputs.** For `create_team`, require a short top-level team label and one explicitly user-named existing top-level `base_profile`, shared by all newly built profiles; ask if either is missing and never infer it. Separately require an explicit `sandbox` choice for each new profile; ask if any choice is missing. Unless the user explicitly requests a different naming convention, leave `standardize_names` at its default `true`: pass each newly created lead/member's original, unprefixed `display_name`; `create_team` adds `Team <team> ` automatically. Never pre-prefix it. For team `Content`, input `Quill` produces visible name `Team Content Quill` and profile ID `teamcontentquill` (the existing forge slug: lowercase alphanumeric, separators stripped, max 24 characters). For new standardized members, normalized names up to 25 characters remain unchanged; the team label is shortened as needed to preserve the full name within forge's 32-character display-name limit. If a normalized member name exceeds 25 characters, team creation rejects it before provisioning rather than truncating it. Newly created lead naming behavior remains unchanged. For standardized team identities, use the existing slug/ID when unused; if it collides, append the smallest available numeric suffix and trim the slug prefix as needed to stay within 24 lowercase alphanumeric characters. This collision handling does not change custom names, a reused `lead_name` profile, or standalone `create_agent` behavior. Set `standardize_names` to `false` only for an explicitly requested alternative, preserving provided display names and derived IDs. Native profile cloning can duplicate the base profile's Hermes-managed credentials. Warn the user to choose a base whose credentials they intend to inherit; never request, expose, or pass credential values.
5. **Keep each profile lean.** Specify only the minimum toolsets and skill categories needed for its output. Follow the shared `fabric` skill's baseline approval guidance for every new Bot. Add only role-specific approvals, extra models, routines, or other profile powers when authorized; a team request alone is not authorization for these additions.
6. **Create and inspect outcomes.** Use `create_agent` for a single new owner or `create_team` for the justified new member profiles, using the approved shared `base_profile` and each profile's approved sandbox. Check each result independently: report created members, failed members, warnings, and any partial completion without implying rollback. Report gateway status exactly as returned; profile creation alone does not prove the gateway is serving or the Bot is ready.

## Pitfalls

- Do not count an existing Bot as a `create_team` member or enroll arbitrary existing Bots as members. Reuse an existing lead only through `lead_name`.
- A lead is optional; don't create one without a distinct coordination responsibility. Don't create a team when no new member is needed.
- Never guess `base_profile` or `sandbox`, including when a requested backend is unavailable; relay the failure rather than silently switching.
- Cloned credentials are sensitive inherited state. Warn about inheritance, but never ask for credential material or put it in tool arguments or reports.
- Avoid overlapping roles, broad tool grants, speculative routines, and unapproved models or profile powers. Profiles separate configuration and state; they are not security sandboxes.
- Team creation may partially succeed. Do not describe a partial result as all-or-nothing, hide warnings, or claim gateway readiness from `ok: true` alone.

## Verification

Before creation, confirm the durable outcome, existing coverage, minimal topology, distinct owner/output/handoff for every role, one explicit user-named top-level `base_profile`, a short top-level team label, and a separate explicit sandbox choice for each new profile. Confirm standardized names and forge-slug IDs for new lead/member profiles (unless an explicitly requested alternative is used), and that any reused `lead_name` profile remains unchanged.

Afterward, compare the tool results with the proposed topology: account for every intended new member, report every failure and warning, and state gateway status and readiness only to the extent actually verified. If any result is partial or pending, label it plainly and do not claim complete team readiness.
