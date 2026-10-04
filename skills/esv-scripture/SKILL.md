---
name: esv-scripture
description: This skill should be used when the user asks to "quote a Bible passage", "give me the scripture text", "show me 1 Samuel 8:1-22", "look up a verse in the ESV", or requests ESV Bible text for a lesson, bulletin, website, or other work. It retrieves text through Crossway's ESV API and checks usage against publisher permissions.
triggers:
  - scripture text
  - Bible passage
  - Bible verse
  - ESV
---

# ESV Scripture Text

Retrieve the English Standard Version through the bundled, dependency-free CLI at `scripts/esv.py`. Do not substitute remembered wording for the API response or represent a different translation as ESV. Do not treat an API response, the short `(ESV)` marker, or the existence of this skill as legal clearance for every use.

## Before requesting text

1. Confirm the requested translation is ESV; if unspecified and material, ask which translation to use. Get a specific book/chapter/verse range; clarify ambiguous references. For requests without a reference, find the reference first rather than retrieving large swaths of text.
2. Check the proposed passage **before calling the API** against [Crossway's permissions](https://www.crossway.org/permissions/) and [ESV API conditions](https://api.esv.org/). Request at most 500 verses and less than half of any book per query (the API describes exceptions for single- and double-chapter books; verify those explicitly). Count overlapping requests and earlier quotations together; never split requests to evade cumulative limits. If the size cannot be verified, ask for a shorter passage or provide a link to [esv.org](https://www.esv.org/) instead.
3. Use the API only for personal or non-commercial purposes consistent with its conditions. Do not disclose, embed, publish, or commit an API key. Obtain a key from [api.esv.org](https://api.esv.org/) and supply it as `ESV_API_KEY` in the process environment using the user's secret manager or an already configured environment; do not put it in the command line, a tracked file, or a response. If unavailable, explain how to configure it and stop rather than inventing text.

## Retrieve and respond

Run from the skill directory (or use its absolute path):

```bash
python3 scripts/esv.py --include-reference '1 Samuel 8:1-22'
```

Use `python3 scripts/esv.py --help` for formatting options. The CLI uses the ESV passage/text API, omits verse numbers and footnotes without altering the words, preserves paragraphs, and requests Crossway's `(ESV)` suffix. Check for a successful response and its `(ESV)` marker; show the reference and only the needed passage. Do not remove the suffix, edit words, translate, or fill in missing text. For verbatim output to a file, redirect stdout; keep scripture output and credentials out of the skill repository. For an unusually long request or a request for a complete book, offer a limited selection or link instead.

## Check the *use*, not just the request

For any public, printed, digital, or audio work, count **all ESV quotations in the entire work**, not just this query: Crossway's current standard-use allowance is at most 500 verses total, not more than one-half of a book, and **less than 25% of the total text of the work**; it excludes commentaries and other biblical reference works. The API has additional limits on display, distribution, local storage (no more than 500 verses or half a book, whichever is less), and request frequency (60/minute, 1,000/hour, 5,000/day). Do not publish ESV quotations in Creative Commons-licensed publications or translate ESV text. If the destination, accumulated verse count, book proportion, or text ratio is unknown, do not assert that publication is permitted: ask for those details or offer a link, summary, or smaller excerpt. For commercial use, over-limit use, commentaries/reference works, or other excluded cases, seek Crossway's written permission/license first.

Retain `(ESV)` with each quotation. For a non-saleable church bulletin or similar medium, Crossway says that suffix suffices. For other print/digital publication, include Crossway's **current full copyright notice** in the title/copyright page or corresponding location, not merely `(ESV)`; get the exact, up-to-date notice from [Crossway's permissions page](https://www.crossway.org/permissions/) before publication. For an API-powered website, follow the API's site-specific rules, including a link to [esv.org](https://www.esv.org/) on each page displaying the text. A private lookup and a publication are different contexts: never claim universal “fair use” or automatic compliance. When permissions are uncertain, use a link rather than reproducing the passage.
