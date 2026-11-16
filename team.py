#!/usr/bin/env python3
"""Build a whole team of Hermes Bots in one go: a lead plus specialists that report to it.

usage: team.py spec.json   (or: team.py - < spec.json)

Spec:
{
  "team": "Content",                       # optional label, used in the lead's brief
  "lead": {...create_agent fields...},     # optional: the chief of staff, built first
  "lead_name": "ceo",                      # or point at an existing Bot instead of building one
  "members": [ {...create_agent fields...}, ... ],
  "hermes_root": "...", "settings": {...}
}

Members are built one at a time. A member that fails is rolled back on its own; the rest of the team
stands. The lead learns who joined (roster in its memory) so it can delegate straight away.
"""
import json
import sys
from pathlib import Path

if __package__:  # Hermes imports this as a package; the CLI entry points run it as a script
    from . import forge
else:
    import forge

MAX_MEMBERS = 6


def _build(member: dict, base: dict, reports_to: str = "") -> dict:
    spec = {**member, "hermes_root": base["hermes_root"], "settings": base["settings"],
            "base_profile": base["base_profile"]}
    if reports_to and not spec.get("reports_to"):
        spec["reports_to"] = reports_to
    return forge.forge(spec)


def _tell_lead(root: Path, lead_id: str, team: str, roster: list):
    """Append the roster to the lead's memory so it knows who to delegate to."""
    mem = (root if lead_id == "default" else root / "profiles" / lead_id) / "memories" / "MEMORY.md"
    if not mem.parent.is_dir():
        return
    lines = [f"- @{m['name']} ({m['display_name']}): {m['description']}" for m in roster]
    entry = (f"I lead the {team} team. My team and what each one does:\n" + "\n".join(lines)
             + "\nI delegate to them by name instead of doing their work myself.")
    existing = mem.read_text(encoding="utf-8").rstrip() if mem.exists() else ""
    mem.write_text((existing + "\n§\n" if existing else "") + entry + "\n", encoding="utf-8")


def build_team(s: dict) -> dict:
    standardize_names = s.get("standardize_names", True)
    if not isinstance(standardize_names, bool):
        return {"ok": False, "error": "standardize_names must be a boolean"}
    team = s.get("team")
    if standardize_names and (not isinstance(team, str) or not team.strip() or not forge.slug(team.strip())):
        return {"ok": False, "error": "a non-empty safe team label is required when standardizing names"}
    root = Path(s.get("hermes_root") or forge.default_root())
    try:
        base_profile = s["base_profile"]
        forge.resolve_base_profile(root, base_profile)
    except (KeyError, ValueError) as exc:
        return {"ok": False, "error": str(exc) if isinstance(exc, ValueError) else "team needs an explicit base_profile"}
    base = {"hermes_root": str(root), "settings": s.get("settings") or {},
            "base_profile": base_profile}
    members = [m for m in (s.get("members") or []) if isinstance(m, dict)][:MAX_MEMBERS]
    if not members:
        return {"ok": False, "error": "a team needs at least one member (list them in `members`)"}
    new_profiles = ([s["lead"]] if isinstance(s.get("lead"), dict) else []) + members
    for profile in new_profiles:
        problem = forge.sandbox_choice_error(profile)
        if problem:
            return {"ok": False, "error": problem}

    team = team.strip() if isinstance(team, str) and team.strip() else "the"
    lead_spec = s.get("lead") if s.get("lead") else None
    if standardize_names:
        team_component = forge.proper_case(team)
        standardized = []
        taken_displays = set(forge.existing_bot_names(root))
        if lead_spec:
            lead_name = forge.proper_case(str(lead_spec.get("display_name", "")))
            lead_display = None
            for name_len in range(len(lead_name), 0, -1):
                max_prefix_len = min(len(team_component), forge.MAX_DISPLAY_NAME - len("Team ") - name_len - 1)
                for prefix_len in range(max_prefix_len, 0, -1):
                    candidate = f"Team {team_component[:prefix_len]} {lead_name[:name_len]}"
                    if candidate.lower() not in taken_displays:
                        lead_display = candidate
                        break
                if lead_display:
                    break
            if not lead_display:
                return {"ok": False, "error": f"no unique standardized display name fits for team lead '{lead_name}'"}
            taken_displays.add(lead_display.lower())
            lead_spec = {**lead_spec, "display_name": lead_display,
                         "_team_identity": forge._TEAM_IDENTITY_TOKEN}
        for member in members:
            member_name = forge.proper_case(str(member.get("display_name", "")))
            if len(member_name) > forge.MAX_DISPLAY_NAME - len("Team ") - 2:
                return {"ok": False, "error": f"team member name '{member_name}' exceeds the "
                        f"{forge.MAX_DISPLAY_NAME - len('Team ') - 2}-character limit for standardized names"}
            display_name = None
            for name_len in range(len(member_name), 0, -1):
                max_prefix_len = min(len(team_component), forge.MAX_DISPLAY_NAME - len("Team ") - name_len - 1)
                for prefix_len in range(max_prefix_len, 0, -1):
                    candidate = f"Team {team_component[:prefix_len]} {member_name[:name_len]}"
                    if candidate.lower() not in taken_displays:
                        display_name = candidate
                        break
                if display_name:
                    break
            if display_name is None:
                return {"ok": False, "error": f"no unique standardized display name fits for team member '{member_name}'"}
            taken_displays.add(display_name.lower())
            standardized.append({**member, "display_name": display_name,
                                 "_team_identity": forge._TEAM_IDENTITY_TOKEN})
        members = standardized
    else:
        if lead_spec:
            lead_spec = {k: v for k, v in lead_spec.items() if k != "_team_identity"}
        members = [{k: v for k, v in member.items() if k != "_team_identity"} for member in members]
    built, failed = [], []

    # 1. the lead — either a new Bot or one that already exists
    lead = None
    if lead_spec:
        result = _build(lead_spec, base)
        if not result.get("ok"):
            return {"ok": False, "error": f"the team lead could not be built: {result.get('error')}",
                    "rolled_back": result.get("rolled_back", False)}
        lead = result
        built.append(result)
    elif s.get("lead_name"):
        wanted = str(s["lead_name"]).strip().lstrip("@").lower()
        if wanted == "default" or (root / "profiles" / wanted / "config.yaml").exists():
            lead = {"name": wanted, "display_name": wanted}
        else:
            return {"ok": False, "error": f"no Bot named '{wanted}' to lead the team (see list_agents)"}

    # 2. the specialists
    for member in members:
        result = _build(member, base, reports_to=(lead or {}).get("name", ""))
        (built if result.get("ok") else failed).append(result)

    roster = [m for m in built if m.get("ok") and m["name"] != (lead or {}).get("name")]
    if lead and roster:
        try:
            _tell_lead(root, lead["name"], team, roster)
        except OSError:
            pass

    made = [{k: m.get(k) for k in ("name", "display_name", "model", "routines", "warning", "gateway", "connect_next")
             if m.get(k)} for m in built if m.get("ok")]
    out = {"ok": bool(made), "team": s.get("team") or None,
           "lead": (lead or {}).get("name"), "members": made,
           "failed": [{"name": f.get("name"), "error": f.get("error")} for f in failed],
           "note": "report created members, failures, and each member's warning and gateway readiness"}
    if not made:
        out["error"] = "no Bot in the team could be built"
    return out


def main():
    raw = sys.stdin.read() if len(sys.argv) < 2 or sys.argv[1] == "-" else Path(sys.argv[1]).read_text(encoding="utf-8")
    result = build_team(json.loads(raw))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
