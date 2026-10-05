---
title: The library shares the repository's skills
description: The skills folio init installs point at the repository's own skills/ folder instead of a copy.
genre: journal
date: 2026-10-04
kind: decision
about: [home]
---

folio init copied the seven skills into .agents/skills/. In folio's own repository that copy would drift from skills/, the source the package ships, so .agents/skills is a link to skills/ and .claude/skills links to it as usual.
