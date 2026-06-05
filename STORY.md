# From Vanity Press Quotes to Open-Source Pipeline

**A first-time author's two-month attempt to publish a 60,000-word book — and the 15 scripts that came out the other side.**

---

## Where this started

I was looking at quotes from book publishers. I had a finished manuscript and no idea what to do with it.

The first quote was $200. Three cover designs to choose from, layout work included, "publication assistance," ISBN. The website looked clean. The package looked like the answer.

I read the contract on a Tuesday morning. The publisher would own the ISBN. They would receive a percentage of every sale in perpetuity. The cover designs were stock templates — searchable on the open web with someone else's book title on them. The "publication assistance" was a single PDF telling me how to log into KDP myself. I closed the tab.

The second option was Reedsy. Professional freelance editors, real cover designers, proper formatting. The quotes for my book — editing, cover, interior layout, EPUB conversion — came back around eight thousand dollars. For a first book, with no audience and no advance, that was not happening.

The third option was a long evening on r/selfpublishing reading horror stories. Vanity presses that quietly registered books to themselves. Editors who took payment and disappeared. Covers that came back looking nothing like the brief. Authors who published, sold thirty copies, and could never recover their files.

Somewhere around midnight I decided I would publish it myself. I had a technical background. I could read documentation. The KDP help pages were free. How hard could it actually be?

The answer turned out to be: hard in fifteen specific ways nobody writes about until you hit them. This repository is what came out of working through all fifteen.

---

## The book

[YATU: You Are the Upgrade](https://a.co/d/0g0sEWuI) is a 60,000-word work of contemporary spirituality — fourteen illustrations, ninety-five footnotes, a Sanskrit glossary, lineage acknowledgments, the works. It launched on Amazon (paperback and Kindle) and at [yatubook.com](https://yatubook.com) in June 2026.

Every script in this repository solved a problem that came up during that production. None of them existed when I started. By the time the book went live, they were a complete pipeline. I am releasing them because every indie author after me is going to hit the same problems, and the open web does not document most of these issues anywhere I could find.

If the scripts help you publish your book without paying eight thousand dollars or signing away your rights for two hundred, that is the entire point.

---

## What the alternatives actually cost

I want to be specific about pricing because this is the gap that drove me to do this work, and I think it drives a lot of would-be authors away from publishing at all.

| Path | Typical cost | What you give up |
|---|---|---|
| **Reedsy / equivalent full-service freelancer market** | $4,000 – $15,000+ for editing + cover + formatting + EPUB conversion | Nothing — you keep all rights, all royalties, all control. Just expensive. |
| **"Hybrid publishers"** (Sand Hill, Greenleaf, Mascot) | $5,000 – $40,000 | You keep more rights than vanity but still pay heavily for what amounts to coordination |
| **Vanity press** ($200–$2,000 packages, "publication assistance") | $200 – $2,000 up front + royalty cut | Often rights to ISBN, layout files, sometimes the book itself. Read the contract slowly. |
| **Author Solutions–owned imprints** (iUniverse, Xlibris, AuthorHouse, Trafford) | $400 – $15,000 in tiered packages | Industry-wide reputation for upselling, predatory contracts, terrible covers. Look up class action history before paying anyone in this group. |
| **Pure DIY with this toolkit** | $0 for the software + $295 for a Bowker ISBN block (if you want your own) + free KDP enrollment | Time — the time spent reading documentation, hitting walls, and learning what the validators expect |

The thing nobody tells you: KDP publishing is free. Amazon takes a per-book printing fee out of each sale, but listing the book costs zero. The actual gatekeeping is not money — it is knowing which buttons to click in the KDP form, what dimensions to set, what HTML tags work in the description field, and how to format your EPUB so it does not get rejected three times before it goes live.

The middle path between paying a freelancer and giving up on the book entirely is doing it yourself with the right tools. That middle path is what this toolkit unlocks.

---

## The fifteen problems we hit (with the receipts)

These are the actual problems I ran into during my book's production. Each one cost me hours or days. Each one is now solved in a script you can run.

### 1. The cover wrap nobody tells you about

When you upload a paperback to KDP, you cannot just upload "front cover + back cover." You upload **one PDF** that contains front + spine + back as a continuous strip, at exact dimensions calculated from your trim size, your bleed allowance, and your spine width.

For my book (5.5" × 8.5" trim, 223 pages, white paper), the wrap PDF had to be exactly **11.8075" × 8.75"**, with the spine occupying a 0.5575" vertical band in the middle. Off by half a centimeter and KDP rejects.

Most cover designers will hand you front, back, and spine as separate files. Composing them into the wrap PDF at the right dimensions is on you.

`assemble_cover_wrap.py` does this. You hand it three images and a target spine width; it produces the KDP-ready PDF.

### 2. The spine width that changes with every edit

Your page count determines your spine width. Every time you edit the manuscript and the page count shifts, the spine width changes, and the cover wrap has to be regenerated.

For US KDP printing on white paper: spine width = page count × 0.0025 inches. For 223 pages, 0.5575". For 224 pages, 0.5600". For 250 pages, 0.625".

If your cover wrap says 0.5575" and your actual book is 235 pages, KDP catches the mismatch and rejects. You then rebuild and resubmit, losing 24-72 hours.

`recalc_spine.py` calculates this instantly from your final page count. Run it after every manuscript edit that changes pagination.

### 3. The KDP "broken TOC link" rejection

This one took me a full day to diagnose. I uploaded my Kindle EPUB. Twelve hours later KDP came back: *"There is a broken link in your Table of Contents; please check the links, regenerate your file, and re-upload your book."*

The visible Table of Contents page looked fine. Every chapter heading was clickable. I tested the EPUB on three different Kindle readers and the navigation worked.

The actual issue was buried two layers deeper. EPUB files contain **two TOCs**: the visible one readers see, and an invisible `nav.xhtml` + `toc.ncx` that Kindle uses to power its built-in "Go to Table of Contents" menu. Pandoc generated both files pointing to `text/ch001.xhtml#yatu` — a file that the pipeline's split step had deleted. The visible TOC had its own different issue: 241 anchor links to chapter IDs that, after the split, lived in entirely different XHTML files than the TOC page.

I rebuilt both navigation files from scratch using the post-split spine, walked every link in the EPUB to confirm it resolved, and added a `fix_cross_file_anchors` step to the pipeline.

This is now `docx_to_kindle_epub.py`'s stage 14. You will not hit this issue if you use the toolkit, because the toolkit was built by hitting this issue first.

### 4. Spine text too close to the edges (the most recent rejection)

This happened the week of launch. KDP came back with a different cover rejection: *"The text on the spine of your book is too close to the edges, which could cause it to wrap onto the front or back cover during printing. To fix this, please move your spine text inward so there's at least 0.0625 inches (about the width of a penny) of empty space on both sides of the text."*

The book's "YATU" lettering on the spine extended close to the spine edges. KDP's bindery has a small tolerance for where the spine fold lands during printing, and if text runs to the edge it can wrap onto the front or back.

The fix: rebuild the spine PNG with text scaled into a "safe zone" of 0.4325" wide, with 18 pixels (0.0625" at 300 DPI) of solid black margin on each side. The proportions of the letters were preserved; we just gave the bindery the safety zone it needed.

`assemble_cover_wrap.py` will now generate spines with proper margins. If you are supplying your own spine artwork, the script's `--spine-crop-to-center` flag handles it correctly.

### 5. Pandoc loses half your manuscript's formatting

If you Google "convert docx to EPUB," you find Pandoc. Pandoc is a brilliant open-source converter. Pandoc also does a bad job on book manuscripts out of the box.

Things Pandoc dropped from my manuscript:

- Chapter structure (everything became one giant XHTML file)
- Smart quotes in the body (mostly) but mangled them inside HTML attributes (which broke the EPUB)
- Image placement (illustrations got dumped at the wrong place in the flow)
- Callout boxes (tables used as sidebars came out unstyled and wrong)
- Section breaks (`* * *` markers got eaten)
- The title page (got duplicated three times, with parts of the title repeating)
- Page break logic for the dedication
- Back-matter sub-section headers

The pipeline now handles all of this. `docx_to_kindle_epub.py` runs Pandoc as stage 1, then ~12 additional transformations to reconstruct the structure Pandoc lost.

### 6. The TOC linkify that wrapped body paragraphs as broken links

This is a subtle one. I wrote a function to make the visible CONTENTS page's chapter entries clickable — wrap each "Chapter 7 The Three Bodies 87" line in an `<a href="#chapter-7">` tag.

The regex was too loose. It matched **any paragraph starting with "Chapter N "** — including body paragraphs that began with phrases like *"Chapter 10 broke you open."*

The result: four paragraphs scattered through the book got rendered as bright blue underlined hyperlinks that, when clicked, did nothing.

The fix: require the matched paragraph to (a) be under 90 characters total and (b) end with a trailing page number. Body sentences that mention earlier chapters are now safe.

### 7. The cross-file anchor rewrite

When you split a monolithic EPUB into per-chapter files, every internal `<a href="#chapter-7">` link breaks — because `#chapter-7` is in a different file now. The fix is to walk every XHTML file, build a map of where every anchor lives, then rewrite all hrefs to be cross-file: `<a href="ch008_part_iii.xhtml#chapter-7">`.

The pipeline does this automatically in `fix_cross_file_anchors`. 241 links in my book; it would have taken weeks to fix by hand.

### 8. Manuscript verification — 10 critical content fixes

Before any of the technical pipeline, the manuscript itself needed several rounds of factual and content verification. I built a verification framework that runs four parallel checks against the manuscript:

- **Content audit** — voice consistency, AI cadence patterns, paragraph density
- **Fact-claim verification** — every cited statistic, every quoted passage, every name and date
- **Cross-surface consistency** — does the book bio match the back cover? Does the dedication match the acknowledgments? Does the trim size match what the cover wrap expects?
- **Legal/IP risk** — quoted material, used images, lineage references, institutional affiliations

The verification report on my book came back with 10 critical issues, including:

- A factual contradiction about my family (the book mentioned twin children in two different contexts; the dates didn't line up)
- The word *Dvapara* was spelled as *Dwapara* (or vice versa) inconsistently across nine occurrences
- A Bhagavad Gita verse (2:47) was paraphrased in a way that didn't match the standard translations
- The Photo Credits page was missing for the lineage masters' photographs
- A passage referencing GPT-4's bar exam result was slightly overconfident — softening was needed
- Several paragraphs read as AI-cadence (symmetric two-clause sentences, aphoristic parallel structures)

Each issue was caught BEFORE the book went to print. The framework is in `book-verification` (a sister skill not in this open-source release, but easily reproducible from the principles in the verification documentation).

### 9. The voice problem — text that sounded AI-generated

This was the longest fight. My drafts kept reading as if they had been polished by an AI — even when I had written them myself.

The patterns that gave it away:

- **Symmetric two-sentence pairs**: *"None of it on the résumé. All of it the actual education."*
- **Aphoristic parallel structure**: *"What looks like destruction is restructuring. What feels like loss is recalibration."*
- **Stacked credibility triplets**: *"Drawing on data from Goldman Sachs, the IMF, and the World Economic Forum…"*
- **Doubled metaphors in one sentence**: *"the map showing you where your reading of it was wrong"* (map + reading mixed)
- **Bureaucratic noun-phrase constructions**: *"a reclamation of X in its original role as Y"*
- **Clever-phrase syndrome**: *"the country of the Gita before it became the country of textbooks"* (sounds poetic, doesn't sound like the actual person)
- **Literary-cold phrasing**: *"a father who did not live to meet the grandchildren"* (technically true, emotionally distant — fails the dinner-table test)
- **Modal verb stiffness**: *"It requires you to…"* where *"It asks you to…"* would land softer

Every one of these is a fingerprint the trained reader will notice. The Amazon reviewer who reads the back cover and thinks "this sounds AI" closes the listing and moves on. The podcast booker who reads the author bio and thinks "this sounds like marketing" doesn't reply to the pitch.

I built a humanize-writing process that catches these patterns and rewrites them. The full diagnostic catalog and the rewrite patterns are documented in the skill folder of my private repo — the public release here only includes the principles, not the full skill (because the skill is voice-specific to my project).

But the receipts I can show: the back cover synopsis went through four rounds. The KDP description went through three rebuilds. The Author Central bio went through five iterations. Each iteration removed AI tells and added specific human voice. If you read [yatubook.com](https://yatubook.com) or the book itself today, you are reading the version that passed.

### 10. The SRF/YSS disclosure that read as legal distancing

The book draws explicitly from a particular wisdom-tradition lineage — the Kriya Yoga lineage of Paramahansa Yogananda, whose teachings are carried by the **Self-Realization Fellowship** (SRF) and the **Yogoda Satsanga Society of India** (YSS).

I had to disclose that I am not officially affiliated with these institutions and do not speak on their behalf. The first version I wrote read:

> "He is not affiliated with, and does not speak for, the Self-Realization Fellowship (SRF) or the Yogoda Satsanga Society of India (YSS)."

This sounded like a lawyer holding the tradition at arm's length. The truth was the opposite — I am a *student* of those teachings, the debt is real and runs through everything I write. The disclosure needed to honor the debt AND the boundary.

The rewrite:

> "He is a student of the Kriya Yoga lineage of Paramahansa Yogananda. His debt to the teachings of the Self-Realization Fellowship (SRF) and the Yogoda Satsanga Society of India (YSS) runs through his work, though he does not speak on their behalf, and what he writes reflects only his own understanding of what he has been given."

Three elements: name the debt, name the boundary, name the limitation of personal understanding. This is the structure to use anytime you have a real relationship to an institution you cannot officially represent.

### 11. The customer-perspective description rewrite

My first version of the KDP book description (the text that appears below the cover on the Amazon page) was structured around the book's argument. Logical for the author, useless for the reader.

The reader scrolling Amazon at 11pm does not know who Sri Yukteswar is. They have not heard *ascending Dwapara*. They cannot pronounce *Paramahansa*. They know what they are FEELING — disposable job, kid up with a chatbot, news that won't stop, the Doomsday Clock at a record close.

The description was rebuilt in v3 to lead with **pain the reader recognizes**, then make the connect-the-dots argument (these pains are one pattern, not five separate stories), then introduce the lineage names as the credibility layer for the 4 million+ *Autobiography of a Yogi* readers worldwide who do know those names and would convert immediately on seeing them.

This is the architecture from the back of Sapiens, adapted for first-time authors with no laurels:

1. **Pain landscape opener** — five concrete current pains, no jargon
2. **Connect-the-dots argument** — what makes this book different from the dozen other AI-spirituality titles
3. **Lineage paragraph** — institutional credibility for the audience that knows the names
4. **Author bridge** — the one credential that distinguishes you (in my case: 5G patent inventor + Kriya lineage)
5. **Production value** — Sapiens uses "27 photographs, 6 maps." Mine: "Thirteen chapters. Four parts. Fourteen illustrations. Ninety-five footnotes."
6. **Inside the book** — bold-header bullets, scannable, each pillar named
7. **About the author** — institutional names disclosed
8. **Where to find more** — the author website

This structure is reusable for any nonfiction book. The exact words are in the `examples/` folder if you want to use the template.

### 12. A+ Content modules and the hidden newline limit

Amazon's A+ Content is the visual section below the standard description on the product page. It does measurable work — documented to lift nonfiction conversion 5–10%. KDP authors get five modules per book.

I designed five modules for YATU. When I started typing the long text module into KDP's editor, I got an error: *"You have exceeded the new line limit."*

Nobody documents this. KDP's Standard Product Description Text module is a WYSIWYG editor with an undocumented cap of roughly 4–8 paragraph breaks total. My text had 20+ paragraph breaks (8 section headers + bullet items, each on its own line). The editor's character count showed I was well under 6,000 — but the newline counter was hidden and I had blown past it.

The fix: compress the same content into 5 paragraphs total (4 paragraph breaks), use inline bold via the toolbar instead of header lines, and run the text through the editor without HTML tags (which the WYSIWYG renders as literal text rather than interpreting).

The toolkit's `docs/customization.md` documents this and similar undocumented limits.

### 13. The cover the publisher would have given me

I want to be honest about one more thing. Some of the $200 vanity-press packages include "professional cover design — choose from three options." When I read about that on Reddit, the consensus was that the three options are typically derived from stock template libraries. Same fonts, same layouts, often the same background image with the book's color shifted.

The cover for YATU went through five rounds of design with a real designer, plus another four rounds of programmatic refinement on the back cover layout via `generate_back_cover.py`. The diya/oil lamp image on the front is custom-licensed art. The back cover incorporates a hook, blurb, three pull quotes, a structured bullet list, an author bio, the ISBN barcode, and a BISAC categorization line — all laid out at typeset-grade precision.

A vanity press would not have produced this. A $5,000 cover designer at Reedsy could have. The free path took me longer but resulted in a cover I own outright, can iterate on, and can extract for marketing materials forever.

### 14. Bowker, BISAC, and the metadata layer

Most indie publishing guides skip the metadata layer because it is unglamorous. It is also where the algorithm lives. Your book's BISAC code, your seven KDP keywords, your description, and your category requests are what determine which Amazon shoppers see your book in 90 days when launch buzz is gone.

I spent days researching this. The choice between BISAC codes — REL080000 (Religion / Mysticism) vs PHI013000 (Philosophy / Mind & Body) vs SEL036000 (Self-Help / Spiritual) — turned out to be the single highest-leverage metadata decision I made. The wrong primary BISAC buries your book in the wrong category forever; the right one lands it in front of the audience that converts.

`validate_metadata.py` checks your metadata JSON against KDP's rules. The strategic discussion of WHICH codes to pick is more book-specific and lives in the documentation, not the script.

### 15. The Author Central bio nobody warns you about

After you publish, you have to set up Amazon Author Central — a separate site from KDP where your author profile, photo, bio, and blog feed live. Author Central shows up next to every book you publish, current and future.

The biography limit, depending on the field you are filling in, can be as tight as **1,000 characters** — not words, characters. That is about 170 words. You have to fit your origin, your credentials, your work, and where to find you in roughly two paragraphs of prose.

I went through five iterations to land a 1,000-character bio that read as a real human and not as a marketing brochure. Then I built a longer version for fields that allow more text. Then a shorter version for podcast intros. The principle is the same: pain-first, lineage-second, where-to-find-me last.

---

## What this saves you in concrete terms

If you publish a book of comparable scope to mine — 60,000 words, custom cover, illustrations, full back-matter, both paperback and Kindle — here is the rough cost comparison:

| Path | Cost | Time |
|---|---|---|
| **Reedsy or full-service freelancer route** | $5,000 – $15,000 | 8 – 16 weeks |
| **Hybrid publisher (Greenleaf, Sand Hill, Mascot)** | $8,000 – $35,000 | 9 – 18 months |
| **Vanity press ($200 package)** | $200 + rights cost | 4 – 8 weeks; you may regret it forever |
| **This toolkit + your own time + ISBN block** | $295 ISBN + free KDP + your hours | 6 – 12 weeks if you are technical; longer otherwise |

The toolkit does not replace good editing, good cover design, or good writing. It replaces the **production layer** — the part where you fight Pandoc, calculate spine widths, debug EPUB navigation, validate cover dimensions, fix KDP rejections, and humanize AI-cadence prose. That is the layer where most authors give up and pay someone else, even though it is the most mechanical and most automatable layer of the whole process.

---

## How to use the toolkit

If you have a polished `.docx` manuscript and a 1600 × 2560 Kindle cover JPG, the fastest path to a Kindle EPUB is:

```bash
pip install pypdf python-docx pillow
sudo apt install pandoc           # or: brew install pandoc

python scripts/book-publishing/docx_to_kindle_epub.py \
  --input manuscript.docx \
  --cover ebook_cover.jpg \
  --output mybook.epub \
  --title "Your Book Title" \
  --subtitle "Your Subtitle" \
  --author "Your Name" \
  --isbn "978-X-XXXXXXX-X-X" \
  --publisher "Your Imprint"
```

That single command runs all 15+ transformations described above — Pandoc conversion, smart quotes, chapter detection, callout styling, page break management, cross-file anchor rewriting, navigation file generation, cover embedding, final packaging. Output is a KDP-ready EPUB.

For the paperback cover wrap, see `docs/print-pipeline.md`. For the validators, `docs/kdp-validators.md`. For customizing the pipeline to your specific book, `docs/customization.md`.

The full pipeline overview is in `docs/overview.md`.

---

## Why I am releasing this

When I started, I read maybe 40 Reddit threads, 30 KDP help pages, 15 Medium posts, and three books about self-publishing. None of them had the actual production scripts. Most of them had general advice ("make sure your cover is the right size!") without telling me which exact PDF dimensions or how to verify them.

The technical work I did to publish YATU generalizes completely. The same pipeline that handled my book's 14 illustrations and 95 footnotes will handle yours. The same EPUB transformer that fixed 241 cross-file anchors in my manuscript will fix them in yours. The same cover wrap assembler that survived KDP's spine-margin rejection will survive yours.

I am releasing it because the alternative is hundreds of indie authors paying $5,000 each to learn what I learned, or worse, signing the $200 contract that takes their book away from them forever.

The MIT license means you can use this commercially. You can fork it. You can rip out parts you don't need and ignore the rest. You can publish your book this week and never tell anyone where the scripts came from. That is fine.

If you do find the toolkit useful and want to share back, the [GitHub issues](https://github.com/) (when the repo goes public) are open. I am not maintaining this as a product — but pull requests that fix real bugs or add useful parameterization for other books are welcome.

---

## The book that produced these scripts

YATU: You Are the Upgrade is a 60,000-word work of contemporary spirituality. It argues that the convergence of AI displacement, geopolitical breakdown, the loneliness epidemic, the collapse of meaning at work, and the spiritual hunger surfacing in the youngest generation are not five separate stories — they are one pattern. The pattern was predicted, with uncomfortable precision, by a tradition that mapped this exact hour two thousand years before the first computer.

If the framing speaks to you:

- [Read the book on Amazon](https://a.co/d/0g0sEWuI) (paperback + Kindle)
- [yatubook.com](https://yatubook.com) — the framework continues there: essays on the Seven Civilizational Organs, the corrected Yuga timeline, and weekly Substack notes
- [@jyolingapp on X](https://x.com/jyolingapp)

If the framing is not your thing, the scripts still work. Use them for whatever book you are trying to publish.

---

## What this toolkit does NOT do

To be honest about scope:

- **It does not write your book for you.** No AI writing here. The manuscript is yours.
- **It does not design your cover.** You still need someone (or yourself) to make a real cover. The `generate_back_cover.py` script can produce a clean back cover from a JSON config, but the front cover is on you.
- **It does not edit your manuscript.** No spell-check beyond what Word gives you. Good editing is still a real human skill and worth paying for if you can afford it.
- **It does not market your book.** Marketing is its own discipline. There are some marketing-adjacent tools (description rebuild guides, A+ Content strategy templates) in the docs, but you still have to do the marketing work.
- **It does not promise your book will sell.** Books selling is its own mystery. The pipeline just removes the production blockers so the book reaches the readers who might want it.

What the toolkit gives you is **the production layer between "finished manuscript" and "live book on Amazon."** That layer is what costs $2,000–$8,000 in the freelancer market, what gets you locked into bad contracts in the vanity-press market, and what stops most indie authors from publishing at all.

---

## Thanks

The toolkit is named after no one. The scripts were written in a 14-day production sprint between mid-May and early June 2026, in collaboration with Claude (Anthropic's AI assistant). Every iteration of every script was driven by an actual problem the production hit. If you find a problem in the scripts, it is because we did not hit your specific edge case during my book's run — file an issue or open a PR.

The book that drove all of this exists because of the lineage of Paramahansa Yogananda and his teacher Sri Yukteswar, carried by the Self-Realization Fellowship and the Yogoda Satsanga Society of India. The toolkit is small. The tradition is not.

If the scripts help your book reach the readers it was written for, that is the entire point.

---

*Last updated June 2026. License: MIT.*
