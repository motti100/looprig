# Security

Looprig is a single static page. It has no server, no accounts and no analytics.

## How your API key is handled

- You type a key into the page. It is sent only to the AI provider you chose, over HTTPS, when you press Run. It is never placed in a URL, a share link, generated code or a log.
- By default the key is kept for the current browser tab only (session storage) and is forgotten when you close the tab.
- "Remember on this device" is optional. It stores the key unencrypted in this browser's local storage. Anyone with access to your browser profile, or any script on the same site address, can read it. Leave it off on shared computers.
- "Forget my keys" removes every stored key.
- Prefer a key with a spending limit, and rotate any key you have pasted into a chat or a screenshot.

## What the page does and does not load

- No third-party scripts, fonts, trackers or analytics.
- A Content Security Policy blocks scripts from other sites, plain-http requests (except to localhost), forms, `<base>` changes and plugins. Requests to AI providers use HTTPS.
- Everything a model or tool returns is escaped before it is shown.
- Pages an agent writes are shown in a sandboxed frame with no access to this page, its storage or the network. JavaScript an agent runs executes in an isolated worker with no network access. The Playground's "files" are an in-memory folder, not your disk.

## Limits you should know about

- The policy has to allow inline script (the page is one file, and the preview frame needs it), so it limits where requests go and what loads, not inline code.
- A custom or LAN provider reached over plain http (not localhost) is blocked; use HTTPS or localhost.
- If you host on GitHub Pages under `username.github.io`, every project on that address shares one browser storage space. Do not enable "Remember" there if you host other pages.
- A browser extension or malware on your computer can read anything in a page.
- Generated agents are a starting point. Read the code before you give an agent tools that write files, run code or reach the web.

## Sharing and backups

- A **share link** stores the steps of a run inside the link itself (after the `#`, so it is never sent to a server). Anyone with the link can read those steps. Do not share runs that contain private text. Your API key is never part of a link.
- A **backup file** holds your progress and saved settings. It never holds API keys.
- The **tool builder** quest runs your JavaScript in the same sandbox as the Playground: a worker with no network, stopped after 10 seconds.

## Keeping the project safe

- Turn on two-factor authentication for the GitHub account that owns the repository. Whoever controls the repo controls what visitors run.
- Review every change before you publish it.

## Reporting a problem

Open a private security advisory on the GitHub repository (Security tab, then Report a vulnerability), or open an issue for anything that is not sensitive.
