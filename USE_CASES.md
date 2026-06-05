# Use Cases — who this toolkit is for

This repository is a publishing toolkit, not a one-size-fits-all framework. The fifteen scripts came out of one specific book production, but the problems they solve recur across many indie author profiles. If you recognize yourself in one of the use cases below, the toolkit will save you time and money.

---

## 1. For first-time nonfiction authors

You finished writing a book. You have a polished DOCX, maybe a draft cover, and zero idea how to get it from "manuscript on my laptop" to "live on Amazon."

**The wall you're hitting:** Most self-publishing guides assume you'll either pay a freelancer ($5,000–$15,000 at Reedsy) or use the manual KDP web tools (which fail in undocumented ways at each step). Neither feels right for a first book with no audience and no advance.

**Where this toolkit helps:**

- **`docx_to_kindle_epub.py`** converts your manuscript to a KDP-ready Kindle EPUB in a single command. Handles smart quotes, chapter detection, navigation files, cover embedding, and the dozen other transformations Pandoc skips.
- **`assemble_cover_wrap.py`** combines your front cover, back cover, and spine image into the exact PDF KDP requires (front + spine + back as one continuous strip at calculated dimensions).
- **The four KDP validators** (`validate_cover.py`, `validate_paperback.py`, `validate_metadata.py`, `recalc_spine.py`) catch the issues that would otherwise come back as KDP rejection emails — saving you 24–72 hours per rejection cycle.

**Recommended starting points:**

- Read [STORY.md](./STORY.md) first — it walks through the 15 production problems we hit and explains why each script exists.
- Then [docs/overview.md](./docs/overview.md) for the pipeline architecture.
- Then [docs/ebook-pipeline.md](./docs/ebook-pipeline.md) for the EPUB-specific workflow.

**What you still need:** A polished manuscript (this toolkit doesn't write or edit), a cover design (the toolkit assembles but doesn't design — except for back covers via `generate_back_cover.py`), and an ISBN if you want your own (Bowker, $295 for a block of 10).

---

## 2. For spiritual, self-help, or philosophy authors with footnotes and back-matter

Your book has structure most publishing tools don't anticipate: a Glossary of foreign-language terms, an Acknowledgments section, lineage/dedication pages, scriptural citations with chapter/verse numbers, illustrations between chapters, and dozens or hundreds of footnotes.

**The wall you're hitting:** Pandoc handles footnotes well but loses your callout boxes, your dedication page break, your back-matter section breaks, and your chapter illustrations. The EPUB comes out as one flat document with no proper navigation.

**Where this toolkit helps:**

- **Back-matter page breaks** — pass `--back-matter-marker "Glossary"`, `--back-matter-marker "Acknowledgments"`, etc., and each section gets its own Kindle page.
- **Dedication page break** — pass `--dedication-first-line "For my mother"` (or whatever your dedication's opening phrase is) and the dedication gets its own clean page.
- **Chapter illustration isolation** — illustrations placed before chapter headings in your DOCX automatically get their own dedicated Kindle page (matches the print convention where art has breathing room).
- **Footnote preservation** — Pandoc handles these correctly; the pipeline keeps them clean.
- **Callout box styling** — tables used as sidebars in your DOCX (with heading text like `KEY POINT`, `CALLOUT`, or custom keywords you add) get proper EPUB CSS.

This was the toolkit's primary author archetype during development. The book that drove its creation has 14 illustrations, 95 footnotes, a Sanskrit glossary, four-section back matter including lineage acknowledgments, and a poetic dedication.

**Specific scripts most relevant:**

- `docx_to_kindle_epub.py` — entire EPUB pipeline with all the back-matter handling
- `epub_reviewer.py` — visual preview to catch footnote rendering issues before upload

---

## 3. For authors with illustrations, diagrams, or photographs

You have visual content embedded in your manuscript — chapter-opener illustrations, instructional diagrams, photographs of people or places.

**The wall you're hitting:**

- Pandoc places images in semi-random positions during EPUB conversion (rarely where you want them)
- KDP rejects EPUBs with images larger than 5 MB
- Color images that look fine on screen may not print correctly in black-and-white paperback
- Images with text embedded (captions, labels) may not be readable at the trim size
- Photo Credits pages for licensed/public-domain photographs are required for legal compliance

**Where this toolkit helps:**

- **Chapter illustration isolation** — images placed before `<h2>` chapter headings automatically get their own page (no crowding the chapter opener)
- **Figure wrapping** — orphan `<img>` tags get wrapped in `<figure>` for proper rendering
- **Image dimension validation** in `validate_paperback.py` — catches oversized images before upload
- **Cover wrap assembly** with proper bleed extension — the script handles bleed-edge image extension automatically

**Caveats:**

- The toolkit does NOT compress images. If your DOCX has 50 MB of high-res photographs, your EPUB will be huge. Use a separate image-optimization pass first (Pillow's `image.thumbnail()` or any image-compression tool).
- The toolkit does NOT convert color to grayscale for print. Do that in your image source files before importing to Word.
- Photo Credits pages need to be written manually — the toolkit doesn't generate them, but it preserves them if you include them in your DOCX.

---

## 4. For authors rejected by KDP — debugging the cryptic rejection emails

You uploaded to KDP. Twelve hours later you got an email starting with *"We checked your files and found issues you need to fix..."* The error message is generic. The KDP previewer doesn't show you what's wrong. Reddit threads on the same error are years old and contradictory.

**The most common KDP rejections and where this toolkit fixes them:**

| Rejection text | Real cause | Toolkit fix |
|---|---|---|
| *"There is a broken link in your Table of Contents"* | `nav.xhtml` / `toc.ncx` pointing to deleted files, OR `<a href="#anchor">` links pointing across split chapter files | `docx_to_kindle_epub.py` Stages 13–14: cross-file anchor rewriting + nav rebuild |
| *"Spine text too close to edges"* | Less than 0.0625" clear space on either side of spine text | `assemble_cover_wrap.py` with safe-margin spine image (see [FAQ.md](./FAQ.md)) |
| *"Cover dimensions don't match expected"* | Wrong wrap PDF dimensions for your trim + page count | `recalc_spine.py` + `assemble_cover_wrap.py` rebuild + `validate_cover.py` confirms |
| *"Interior page count doesn't match cover"* | Page count drifted after manuscript edits | `recalc_spine.py` recomputes spine width; rebuild cover |
| *"Fonts not embedded"* | DOCX-to-PDF conversion didn't embed fonts | `verify_print_ready.py` flags this; re-export with "Best for printing" option in Word |
| *"Description contains restricted content"* | Banned phrases (`new release`, `#1 bestseller`, URLs, pricing) in description | `validate_metadata.py` checks against the banned-phrase list |
| *"Trim size doesn't match interior"* | Interior PDF is US Letter or A4 instead of trade trim | `validate_paperback.py` catches this; re-export from Word at trim dimensions |

**Recommended workflow if you're stuck in a rejection loop:**

1. Run the relevant validator before re-uploading: `validate_cover.py`, `validate_paperback.py`, or `validate_metadata.py`
2. Read the validator's specific failure message
3. Fix the underlying issue (not the symptom)
4. Re-upload to KDP

Each rejection cycle costs 24–72 hours. Running the validators locally costs seconds.

---

## 5. For authors comparing publishing service costs

You priced out Reedsy. You found $200 vanity press packages. You read Reddit horror stories. You're trying to decide whether to pay someone or do it yourself.

**The honest cost comparison:**

| Path | Cost | Time | What you give up |
|---|---|---|---|
| Reedsy / equivalent freelancer market | $4,000–$15,000+ | 8–16 weeks | Nothing (you keep all rights, royalties, control) |
| Hybrid publishers (Greenleaf, Sand Hill, Mascot) | $5,000–$40,000 | 9–18 months | Some royalty share, some rights nuances |
| Vanity press ($200 packages) | $200–$2,000 up front + royalty cut | 4–8 weeks | Often ISBN ownership, layout files, sometimes the book itself |
| Author Solutions-owned imprints (iUniverse, Xlibris, AuthorHouse) | $400–$15,000 | varies | Industry-wide reputation for predatory contracts |
| **DIY with this toolkit** | **$0 software** + ~$295 ISBN block + free KDP | **6–12 weeks** if you're technical | Time |

**Where the toolkit fits:** The production layer — taking your finished manuscript and producing the exact files KDP requires (interior PDF, cover wrap PDF, Kindle EPUB), with validation at each stage.

**What you should still pay for:**

- **Good editing.** Substantive developmental editing makes books actually good. The toolkit doesn't edit anything. If you can afford a real editor (Reedsy hosts them; $1,500–$5,000 typical), the book benefits more from that than from any other paid service.
- **Cover design.** A real cover designer charges $500–$3,500. The toolkit assembles covers from your supplied images and can generate a clean back cover from a JSON config, but the front cover is on you. Hire a designer or design it yourself in tools you know.
- **ISBNs (your own).** Bowker block of 10 for $295. Lets you publish wide (KDP + IngramSpark + Draft2Digital + direct sales on your site) without locking the book to one platform.

**What the toolkit lets you skip:**

- Paying a service to "format" your book (~$200–$1,500). The toolkit does this.
- Paying for EPUB conversion (~$200–$500). The toolkit does this.
- Paying for KDP upload assistance (~$100–$500). The toolkit + KDP's own (free) upload form does this.
- Paying for cover wrap assembly (~$100–$300). The toolkit does this.
- Re-uploading repeatedly to KDP after rejections (24–72 hours each, $0 but real time cost). The validators catch issues before upload.

**Bottom line:** The toolkit replaces roughly $2,000–$8,000 of paid production work. It does not replace good editing, good cover design, or good writing.

---

## 6. For authors on a compressed timeline

You have weeks, not months, to publish. A launch date, a speaking event, a deadline.

**The wall you're hitting:** Most self-publishing guides assume 60–90 days. ARC readers need 4–6 weeks. KDP pre-order pages need to be set up 90 days ahead for maximum ranking benefit. Podcast bookings have 30–90 day lead times.

**Where this toolkit helps:**

- **Speed on the production layer.** With this toolkit, the production stage (interior PDF + cover wrap + Kindle EPUB) goes from weeks to hours. You get back the time to spend on the parts that take longer (ARC outreach, podcast pitching, list-building).
- **No rejection cycles.** Each KDP rejection costs 24–72 hours. The validators prevent most rejections.
- **Both formats from one source.** Same DOCX produces paperback PDF AND Kindle EPUB through different pipeline stages. No double work.

**Recommended compressed-timeline workflow (~14 days):**

| Day | Action |
|---|---|
| 1–3 | Final manuscript edits. Run all validators. |
| 4 | Generate Kindle EPUB. Visual review via `epub_reviewer.py`. |
| 5 | Generate paperback interior PDF. Generate cover wrap. Validate both. |
| 6 | Upload to KDP (paperback + Kindle). Set pre-order date if possible. |
| 7–8 | KDP review window. Order a $5 print proof. |
| 9–10 | Proof arrives. Inspect against your final files. Approve. |
| 11–13 | Pre-launch marketing — Substack, Twitter, podcast pitches. |
| 14 | Launch day. |

This compressed timeline is feasible because the toolkit removes most production-layer delays. The compressing factor is your manuscript readiness, not the publishing tools.

---

## 7. For developer-leaning authors who want control

You write code (or did, in a past life). You'd rather configure scripts than wait for a freelancer's revision cycle. You want to know exactly what's happening to your files at each stage and be able to debug when something goes wrong.

**Where this toolkit fits naturally:**

- Every script is readable Python 3.10+ — no framework abstractions, no DSLs
- Every transformation is a function you can read and modify
- The pipeline is explicit (no magic) — `docx_to_kindle_epub.py` documents all 15+ transformations in numbered comments
- CLI flags for the customization points (dedication phrase, back-matter markers, callout keywords)
- The validators give specific failure messages, not generic "something is wrong"
- MIT licensed — fork freely, modify freely, no attribution requirements beyond keeping the license file

**Recommended modifications for your book:**

- Edit the `chapter_patterns` list in `docx_to_kindle_epub.py` if your chapter naming differs from standard conventions
- Edit the `callout_keywords` list if your callouts use different heading text
- Customize the Kindle CSS at the top of `docx_to_kindle_epub.py` for your typography preferences
- Adjust the back cover layout configuration in `generate_back_cover.py` for your design

**Caveats:**

- This is intentionally not a framework. No plugin architecture, no event hooks, no extension points beyond the CLI flags and the editable Python.
- The codebase is ~5,000 lines. Readable in a couple of hours.
- Pull requests welcome (see [CONTRIBUTING.md](./CONTRIBUTING.md)) — but this is a release, not an actively-maintained product.

---

## 8. For authors who got a $200 vanity press quote and feel something is off

You sent a query, got a sales pitch back, and the package looks suspicious. The "publisher" wants to own your ISBN. They take a royalty cut in perpetuity. The "cover design" is described as "three professional templates to choose from." The contract has lock-in clauses about what platforms you can publish on.

**The clearest signs you're looking at vanity press:**

1. They contacted YOU first (real publishers don't pitch unknown authors)
2. They want you to pay them (real publishers pay you)
3. They own the ISBN (you should own the ISBN — Bowker, $295 for 10)
4. They take royalties in perpetuity, even after their services are rendered
5. The "design package" promises templates rather than custom design
6. They lock you to their platform — can't publish elsewhere
7. The contract is long and full of language about "rights granted to publisher"

**What this toolkit gives you instead:**

- You own your ISBN (buy it yourself from Bowker)
- You own all rights to your book forever
- You get 100% of the royalties KDP pays (minus KDP's printing cost per book, which is fair and transparent)
- You can publish on KDP, IngramSpark, your own website, and any other platform simultaneously
- No contracts, no lock-in, no monthly fees

**The trade-off:** You spend more time. You learn KDP's quirks. You handle marketing yourself.

But the trade-off is heavily in your favor compared to handing over $200 plus perpetual royalties for templated work and rights restrictions.

For more on this calculus, see the "Where this started" section in [STORY.md](./STORY.md).

---

## Where to go next

Whichever use case applies to you, the starting point is the same:

1. Read [STORY.md](./STORY.md) for the full context of how the toolkit was built
2. Read [README.md](./README.md) for the technical quickstart
3. Skim [FAQ.md](./FAQ.md) for solutions to specific problems
4. Browse `docs/` for stage-by-stage details on print and ebook pipelines
5. Try the toolkit on your manuscript and see what happens

If you get stuck, file an issue at [github.com/rgupta0419/indie-publishing-pipeline/issues](https://github.com/rgupta0419/indie-publishing-pipeline/issues).

If the toolkit helps you publish your book, no thanks needed — but if you want to share the success, link back to the repo so the next indie author can find it.
