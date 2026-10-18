---
title: Comments are committed by the server, as the commenter
description: A comment has no name field, is one commit on the current branch, and is refused rather than taken anonymously.
genre: journal
date: 2026-10-04
kind: decision
about: [getting-started]
tags: [using]
---

The server knows who is writing: the git user locally, and on a deployed server the header a sign-in proxy sets, named in the charter as comments.identity_header. Each new thread or reply is one commit holding only that page's comment file. With folio serve --push the server pulls before and pushes after, and on any failure it rolls back and refuses the comment. An exported site takes no comments. Readers see waiting, resting and closed, a Review page, Keep and Change on flags, and what changed once a thread is addressed. The chapter [Comments on a deployed library](/content/guides/getting-started/05-deployed-comments.html) explains it.
