---
title: Metadata holds every fact the engine reads
description: Documents carry five core fields, and the body is prose the engine never parses.
genre: journal
date: 2026-10-03
kind: decision
about: [why-metadata-first]
tags: [design]
---

Every fact the engine renders, searches, filters or checks moved into metadata: title, description, genre, status, tags, and fields a genre declares only when the engine reads them. The shell now draws each page's header, and what follows from links is generated. The reasons are in [Why metadata comes first](/content/entries/why-metadata-first/).
