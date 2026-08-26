# Security Policy

Aerobiz Evals is a public research benchmark for long-horizon strategic
reasoning with LLM agents playing *Aerobiz Supersonic* through the BizHawk
emulator. This document explains how to report a vulnerability, what this
repo's secret-handling policy is, and what running the harness actually does
on your machine.

## Reporting a vulnerability

If you find a security vulnerability in this repository (harness code,
scripts, or configuration), please report it privately rather than opening a
public issue:

- Preferred: open a **GitHub Security Advisory** for this repository
  ("Security" tab → "Report a vulnerability").
- Alternative: open a **private issue** / contact the repository owner
  directly, **@joaovpfarias**.

Please do not disclose the issue publicly (public issue, PR, or discussion)
until it has been triaged. We aim to acknowledge reports promptly and will
work with you on a fix and a reasonable disclosure timeline.

## Secrets policy

- **No credentials are ever committed to this repository.** There is no
  API key, token, password, or credential file checked into git history.
- The harness reads its telemetry token for [Logfire](https://logfire.pydantic.dev)
  from a **local** file, `.logfire/logfire_credentials.json`. This file lives
  only on your machine, is created by the `logfire` CLI/SDK on your own
  setup, and is **ignored by `.gitignore`** — it must never be added to a
  commit.
- Any `.env` file (or `.env.*` variant) is also git-ignored. **Never commit
  a `.env` file.** If your local configuration needs secrets (API base
  URLs, model provider keys, etc.), keep them in an untracked `.env` or in
  your local environment variables.
- If you ever believe a secret was accidentally committed (past or future),
  treat it as compromised, rotate it immediately, and report it using the
  process above so history can be scrubbed if needed.

## No ROM or savestate is included

This repository **does not contain, and will never contain**, a copy of the
*Aerobiz Supersonic* ROM, its BIOS, or any BizHawk savestate/save file.
Running the benchmark requires you to supply your own legally obtained copy
of the game. `.gitignore` actively blocks common ROM and savestate
extensions from being committed. See `roms/README.md` for details on how to
provide your own ROM.

## What this repo does on your machine

So there are no surprises for anyone who clones and runs this: the harness

- **drives a local emulator process** (BizHawk) via IPC — it launches, sends
  input to, and reads emulator memory/screen state from a BizHawk instance
  running on your machine;
- **makes outbound HTTP calls to a model provider/server** to get the
  LLM agent's decisions for each turn of the game; and
- **makes outbound HTTP calls to Logfire** (pydantic.dev) to send run
  telemetry/traces, using the local credentials file described above.

It does not otherwise phone home, does not download or fetch ROM/BIOS files
for you, and does not modify files outside of this project's working
directories (logs, states, IPC scratch files) unless you configure it to do
otherwise.
