# Set up folio

Paste everything below this line into your coding agent, in the project where you want a library.

---

Set up folio in this project. folio lets you, the agent, build and keep a knowledge library here: HTML and Markdown documents, each of one genre, linked into one graph and checked by a gate. I will not run folio commands myself. You run them, through the skills folio installs.

1. Install the engine, the Python package `folio-kb`, which provides the `folio` command:
   - If `folio --version` already prints a version, it is installed; go to step 2.
   - Otherwise: `uv tool install folio-kb`, or `pipx install folio-kb`, or `pip install folio-kb` in the project's environment.
   - If none of these works, tell me and stop.
2. Confirm it works: `folio --version`. Tell me the version.
3. Look for the skills in `.agents/skills/` (set-up, configure, write, organise, address, publish, run).
   - If they are present, read `.agents/skills/set-up/SKILL.md` and follow it.
   - If they are not, ask me questions 1 and 2 below first, run `folio init <that folder> --name "<name>" --purpose "<one sentence>"` to install them, then follow the set-up skill. It will see the library `folio init` just made and only needs to finish the charter.
4. Ask me these questions in one message, each with your suggested default, and skip any I have already answered:
   1. What is it called, what is it for, and who reads it?
   2. Where should it live? (for example `docs/` in this project, or the root of a new repository)
   3. Which packs should be on? Run `folio pack list` (it works before a library exists) and give me each one's purpose in one line.
5. Finish with `folio check` passing and the setup committed. Then tell me, in two lines, what I can now ask you for.

From then on, I will just ask in plain words ("add a note on X", "tidy the maps", "go through my comments", "build the site"). Pick the matching skill in `.agents/skills/` and follow it.
