# Central Redis — Marketing Site Stitch Prompts

Public site for **redis.mohammadramiz.in**. Production launch, not a waitlist.
Visual language matches the dashboard exactly, so the site and the product feel
like one thing.

**How to use:** paste **Section 0 (Design System)** first, then one section
prompt per generation, re-pasting the design system above each. Stitch does not
carry style reliably between separate generations — the repetition is what keeps
them consistent.

**A note on claims.** Every number in these prompts is real: the limits, the
data types, the endpoint names, the stack. Don't let Stitch invent customer
counts, "10,000+ developers", uptime percentages, or benchmark figures — you
have no customers to cite yet and a fabricated stat is the fastest way to lose
a developer audience. If Stitch adds one, delete it.

---

## 0. Design System (paste at the top of EVERY prompt)

```
Design system for the marketing site of "Central Redis" — a hosted multi-tenant
Redis API. The audience is developers. Confident, precise, not salesy.

COLORS
- Brand red: #DC382D  (Redis red — primary buttons, logo mark, key accents,
  chart fills. Decisive but not everywhere.)
- Brand hover: #B92E24
- Brand tint: #FDF0EF
- Ink / heading: #16110F  (warm near-black, never pure black)
- Body text: #6B605C
- Muted text: #9A908B
- Page background: #FBF9F8  (warm off-white)
- Section background alt: #FFFFFF
- Card surface: #FFFFFF
- Border: #E8E2DF     Border strong: #D4CBC7
- Dark surface (hero code, footer): #1C1614 with #F5EFEC text
- Success #1B8A5A · Warning #C77A11 · Danger #C0271C · Info #2563A8

TYPOGRAPHY
- UI/display font: Inter. Headings tight (-0.03em), weight 600-700.
- Monospace: JetBrains Mono — for ALL code, endpoints, keys, numbers in tables,
  and small technical labels.
- Scale: hero 56px/700, section heading 36px/600, card title 18px/600,
  body 16px/400, small 14px, label 12px/500 uppercase 0.06em tracking,
  mono 13px.
- Body copy max-width 62 characters. Never full-bleed paragraphs.

SHAPE & DEPTH
- Radius: 12px cards and images, 8px inputs, 6px buttons, 4px badges.
- Shadows subtle: 0 1px 2px rgba(22,17,15,0.06); one elevated shadow for
  floating product screenshots: 0 24px 64px rgba(22,17,15,0.12).
- 1px borders do the structural work, not heavy shadows.

RHYTHM
- Section padding 96px vertical on desktop, 56px on mobile.
- Content max-width 1120px, centered, 24px gutters.
- Alternate section backgrounds between #FBF9F8 and #FFFFFF for separation —
  no dividers, no gradients between sections.

COMPONENTS
- Primary button: solid #DC382D, white text, 44px tall, 6px radius, no gradient.
- Secondary button: white, 1px #D4CBC7 border.
- Ghost button: text only with a small arrow.
- Eyebrow label above every section heading: 12px uppercase, letter-spaced,
  in #DC382D.
- Code blocks: #1C1614 background, JetBrains Mono 13px, syntax colored —
  #F0857D commands, #8FD19E strings, #E8B33A keywords, #9A908B comments and
  punctuation. A small "Copy" button top-right.
- Feature cards: white, 1px border, 24px padding, an 22px outlined icon in
  #DC382D, a bold title, two lines of body copy. No drop shadows on hover,
  just a border color change to #D4CBC7.

TONE
Plain, specific, technical. Short sentences. Concrete nouns. No "revolutionize",
no "seamless", no "unleash". Never invent statistics, customer counts, or uptime
figures. Prefer a real endpoint over an adjective.
```

---

## 1. Navigation + Hero

```
[PASTE DESIGN SYSTEM]

Screen: Site header and hero section, desktop.

NAVIGATION — sticky, 68px tall, #FBF9F8 with a 1px bottom border that only
appears once scrolled. Left: a red hexagonal Redis-like logo mark plus the
wordmark "Central Redis" in 16px/600. Center-left, a row of 14px nav links in
body-text color: Features, How it works, Docs, Pricing. Right: a ghost "Sign in"
link and a primary red "Start free" button (36px tall, 6px radius).

HERO — 96px top padding, two columns at 52% / 48%, gap 64px, vertically
centered.

LEFT COLUMN:
- A small status pill: #FDF0EF background, 4px radius, a 6px green dot, then
  12px text "Live in production — free while in beta".
- Headline, 56px/700, tight leading (1.05), max 12 words across two lines:
  "One Redis layer. Every project you ship."
  The second sentence in #DC382D.
- Sub-headline, 18px, #6B605C, max 60 characters per line:
  "Isolated namespaces, per-project API keys, and a REST endpoint for every
  Redis operation. No connection strings. No instance to babysit."
- Button row: primary red "Start free — 1 project" and secondary
  "Read the docs".
- Below the buttons, a row of three tiny reassurance items in 13px muted text
  separated by dots, each with a small check icon:
  "No credit card · Live in under a minute · Your data stays namespaced"

RIGHT COLUMN — a dark code card (#1C1614, 12px radius, the elevated shadow),
with a fake window chrome bar at the top: three small dots on the left and the
text "terminal" in 12px mono muted on the right, plus a Copy button.
Inside, syntax-highlighted:

  curl -X POST https://api.central-redis.dev/checkout_svc/set/cart:42 \
    -H "x-api-key: sk_live_8Kd..." \
    -H "Content-Type: application/json" \
    -d '{"value": {"items": 3}, "ttl": 3600}'

  {"ok": true, "key": "cart:42", "ttl": 3600}

The response line in #8FD19E, visually separated by a blank line, with a small
green "200" badge floating at its left edge.

BELOW THE HERO — a slim full-width strip on white: the 12px uppercase label
"Built on" centered, then a row of five wordmarks in #9A908B at 60% opacity:
FastAPI, Redis, MongoDB Atlas, Python, Render. Text only, no logos.
```

---

## 2. Product Screenshot Showcase

```
[PASTE DESIGN SYSTEM]

Screen: A section showing the real dashboard, on #FFFFFF background.

Centered header block: eyebrow "The dashboard", heading 36px/600
"Everything your keys are doing, in one place.", then one line of 16px body
copy, max 60 characters wide: "Browse data, run requests, rotate keys, and
watch usage — without opening a Redis CLI."

Below it, a large browser mockup, 1040px wide, centered, 12px radius, the
elevated shadow, and a 1px border. The chrome bar is #FBF9F8 with three dots
and a rounded address field showing "central-redis.dev/app/checkout_svc" in
12px mono muted.

Inside the mockup, render a realistic dashboard screenshot: a 240px white left
sidebar with a red hexagonal logo, a project switcher reading "checkout_svc" in
monospace, and nav rows with outlined icons (Overview active in red on a
#FDF0EF background, then Data Browser, API Console, API Keys, Usage, Settings).
The main area shows a page title "checkout_svc" in monospace, a row of four
stat cards (TOTAL KEYS 1,284 · MEMORY 4.2 MB · REQUESTS 24H 18,342 ·
ERROR RATE 0.03%), and beneath them a wide card titled "Requests" containing a
smooth area chart in Redis red with a soft gradient fill fading to transparent.

Below the main mockup, a row of three smaller screenshots (330px each, 8px
radius, 1px border, lighter shadow), each with a 14px/600 caption underneath
and one line of 13px muted text:
1. "Data Browser" / "Filter by pattern, inspect any key, edit JSON in place."
   Image: a two-pane key list with small colored type badges (STR, LST, HSH)
   and a JSON viewer on the right.
2. "API Console" / "Send real requests without leaving the page."
   Image: a method dropdown, an endpoint field, operation chips, and a JSON
   response panel with a green 200 badge.
3. "API Keys" / "Name, rotate, and revoke keys independently."
   Image: a table of masked keys (sk_live_••••••••3f9a) with Rotate and Revoke
   actions.
```

---

## 3. How It Works — Three Steps

```
[PASTE DESIGN SYSTEM]

Screen: A three-step section on #FBF9F8 background.

Centered header: eyebrow "How it works", heading "Three steps. Zero ops.",
one line of body copy: "From signing up to storing your first key is about a
minute."

Three columns, equal width, 32px gap. Each column is NOT a card — it sits
directly on the background, separated by a thin vertical 1px #E8E2DF line
between columns.

Each column contains, stacked:
- A large step number in monospace, 40px, #DC382D at 20% opacity: 01, 02, 03.
- A 20px title in ink.
- Two lines of 15px body copy.
- A small dark code snippet (#1C1614, 8px radius, 12px mono, 14px padding).

STEP 01 — "Create a project"
"Pick an ID. You get an isolated namespace and an API key, shown once."
Snippet: a tiny UI fragment instead of code — a white rounded input containing
"checkout_svc" in monospace with a red "Create" button beside it.

STEP 02 — "Store something"
"Any JSON value, with an optional TTL in seconds."
Snippet:
  curl -X POST $BASE/set/cart:42 \
    -H "x-api-key: $KEY" \
    -d '{"value": {"items": 3}, "ttl": 3600}'

STEP 03 — "Read it back"
"Values round-trip as JSON. Objects come back as objects, not strings."
Snippet:
  curl $BASE/get/cart:42 -H "x-api-key: $KEY"

  {"key":"cart:42","value":{"items":3},"exists":true}
with the response line in green.
```

---

## 4. Features Grid

```
[PASTE DESIGN SYSTEM]

Screen: Feature grid on #FFFFFF.

Centered header: eyebrow "What you get", heading "Built for the way you
actually use Redis.", one line of body copy: "Every Redis primitive you reach
for, exposed over HTTP and scoped to one project."

A 3 x 2 grid of six feature cards, 24px gap. Each card: white, 1px #E8E2DF
border, 12px radius, 26px padding; a 22px outlined icon in #DC382D at the top,
then a 17px/600 title, then two lines of 14px body copy in #6B605C. Some cards
end with a small monospace detail line in #9A908B.

1. Icon: layered database. "Namespaced by default"
   "Every key is stored as project_id:key. Two projects can both use
   session:1 without ever seeing each other."
   Mono line: checkout_svc:session:1

2. Icon: key. "Keys you can rotate"
   "Up to ten named API keys per project. Rotate or revoke one without
   touching the others. Stored hashed — shown once."
   Mono line: sk_live_••••••••3f9a

3. Icon: braces. "Real data types"
   "Strings, lists, hashes, and sets. TTLs, atomic counters, batch reads
   and writes."
   Mono line: GET · SET · LPUSH · HSET · SADD · INCR

4. Icon: chart. "Usage you can see"
   "Request volume, error rate, and p50/p95/p99 latency per project,
   broken down by operation."

5. Icon: search. "A browser for your keys"
   "Filter by glob pattern, inspect any value, edit JSON in place. Cursor
   paginated, so a large keyspace stays responsive."
   Mono line: cart:*

6. Icon: shield. "Isolation that's enforced"
   "A project's key only ever authenticates that project. Wrong project,
   wrong key, revoked key — all rejected at the edge."
   Mono line: 401 Invalid API key
```

---

## 5. Code Samples — Multi-Language

```
[PASTE DESIGN SYSTEM]

Screen: A code section with language tabs, on #FBF9F8.

Two columns, 40% / 60%, gap 56px, vertically centered.

LEFT COLUMN:
- Eyebrow "Integration"
- Heading, 36px: "It's just HTTP."
- Body copy, two short paragraphs of 16px:
  "No client library to install, no connection pool to size, no TLS config.
  If your language can make an HTTP request, it can use Central Redis."
  "Values are stored as JSON when they parse as JSON, and as raw strings when
  they don't. Reads reverse it, so what you put in is what you get back."
- A ghost link with an arrow: "Full API reference →"

RIGHT COLUMN — a dark code card (#1C1614, 12px radius, elevated shadow).
Across its top, a tab bar of five monospace tabs, 13px, on a slightly lighter
strip (#241D1A): cURL, JavaScript, Python, Go, Ruby. "JavaScript" is active —
red text with a 2px red underline. A Copy button sits at the far right of the
tab bar.

The JavaScript panel shows, syntax highlighted:

  const BASE = "https://api.central-redis.dev/checkout_svc";
  const headers = {
    "x-api-key": process.env.CENTRAL_KEY,
    "Content-Type": "application/json"
  };

  // write with a one-hour TTL
  await fetch(`${BASE}/set/cart:42`, {
    method: "POST",
    headers,
    body: JSON.stringify({ value: { items: 3 }, ttl: 3600 })
  });

  // read it back
  const res = await fetch(`${BASE}/get/cart:42`, { headers });
  const { value } = await res.json();   // { items: 3 }

Comments in #9A908B, strings in #8FD19E, keywords (const, await, method) in
#E8B33A. The trailing inline comment on the last line is right-aligned and
muted.
```

---

## 6. Live API Playground

```
[PASTE DESIGN SYSTEM]

Screen: An interactive try-it-now section on #FFFFFF.

Centered header: eyebrow "Try it", heading "Run a request right now.", one line
of body copy: "This hits a real sandbox project. No account needed — it resets
every hour."

A single wide card, 900px, centered, white, 1px border, 12px radius, elevated
shadow. Inside, two panes split 50/50 with a 1px vertical divider.

LEFT PANE — the request builder, 24px padding:
- A row of operation chips, wrapping: get, set, delete, ttl, incr, lpush,
  lrange, hset, hgetall. "set" is active — filled #DC382D with white text.
  The rest are outlined pills in monospace 12px.
- A method + path row: a green-tinted "POST" badge, then a monospace field with
  a non-editable grey prefix chip "/sandbox" followed by the editable
  "/set/demo:1".
- A label "Body", then a monospace editor area (#FBF9F8, 1px border, 8px
  radius, 140px tall, line numbers in a muted gutter) containing:
    {
      "value": "hello world",
      "ttl": 300
    }
- A full-width primary red "Send request" button with a paper-plane icon.

RIGHT PANE — the response, 24px padding, #FBF9F8 background:
- A status row: a green "200 OK" badge, then muted monospace "· 11 ms · 64 B".
- A syntax-highlighted JSON block on white with a 1px border:
    {
      "ok": true,
      "key": "demo:1",
      "ttl": 300
    }
- Below it, a small collapsed row: a chevron and the text "See this as cURL"
  in 13px.

Under the card, centered 13px muted text: "Sandbox keys are rate limited and
wiped hourly. Create a project for a namespace that's yours."
```

---

## 7. Pricing

```
[PASTE DESIGN SYSTEM]

Screen: Pricing section on #FBF9F8.

Centered header: eyebrow "Pricing", heading "Free while we grow.", one line of
body copy: "One project per account, generous limits, and no card. Paid tiers
arrive when there's something worth charging for."

Two cards side by side, centered, 380px each, 24px gap, top-aligned.

CARD 1 — "Free", the highlighted one: white, a 2px #DC382D border, 12px radius,
and a small red ribbon tab at the top reading "Available now" in 11px uppercase
white text.
- Plan name "Free" 20px/600.
- Price: "$0" in 44px/700 monospace, with "/month" in 14px muted beside it.
- One line of muted body copy: "Everything you need for a side project or a
  small service."
- A full-width primary red button: "Create your account".
- A thin divider, then a checklist of six rows, each a small red check icon
  followed by 14px text, with the number in monospace:
    1 project
    10,000 keys
    100 MB storage
    1,000,000 requests / month
    10 API keys
    Full dashboard, browser, and console
- A muted 12px footnote: "Limits aren't enforced during beta. You'll get an
  email well before that changes."

CARD 2 — "Need more?": white, 1px #E8E2DF border, visually quieter.
- Plan name "More than one project" 20px/600.
- Instead of a price, the text "Let's talk" in 28px/600 ink.
- Body copy: "Multiple projects, higher limits, or something specific to your
  setup — send a note and we'll sort it out."
- A full-width secondary button: "Email the founder".
- A checklist of three rows with a neutral grey check:
    Multiple projects
    Raised limits
    Direct support
```

---

## 8. Founder Note

```
[PASTE DESIGN SYSTEM]

Screen: A personal section on #FFFFFF, deliberately narrow.

Content max-width 720px, centered.

Eyebrow, centered: "Why this exists".

A large pull quote, 26px/500, ink, tight leading, left-aligned within the
narrow column, with a 3px #DC382D vertical rule down its left edge and 24px of
left padding:

"I kept spinning up a Redis instance for every side project. Same config, same
connection string in another .env file, same instance sitting idle at 4am. This
started as a way to stop repeating myself — one namespaced API across
everything I build."

Below the quote, a left-aligned attribution row: a 44px circular avatar with the
initials "MR" in #DC382D on a #FDF0EF background, then two stacked lines —
"Mohammad Ramiz" in 15px/600 and "Builder — Central Redis" in 13px muted.
Beside them, three small ghost icon links: GitHub, LinkedIn, Portfolio.

Below that, separated by 40px, a slim horizontal strip on a #FBF9F8 rounded
panel (12px radius, 20px padding) containing three inline facts, each a 12px
uppercase label above a 15px value:
  RUNNING SINCE — Apr 2026
  BUILT WITH — FastAPI · Redis · MongoDB
  STATUS — Production
```

---

## 9. FAQ

```
[PASTE DESIGN SYSTEM]

Screen: FAQ section on #FBF9F8.

Centered header: eyebrow "Questions", heading "Before you sign up."

A single centered column, 760px wide. Each question is an accordion row:
20px vertical padding, a 1px #E8E2DF bottom border, the question in 16px/600
ink on the left and a small chevron on the right that rotates when open.
The first item is open, its answer shown in 15px #6B605C with 12px top spacing
and a max-width of 62 characters.

Render these eight, with the first expanded:

1. "Is my data isolated from other projects?" — OPEN
   "Yes. Every key is stored internally as project_id:key, and a project's API
   key only ever authenticates that one project. Presenting a valid key for a
   different project returns 401."

2. "What happens if I lose an API key?"
   "Rotate it from the dashboard. The old value stops working immediately and
   you get a new one. Keys are stored hashed, so nobody — including us — can
   read yours back."

3. "Is this a Redis replacement?"
   "No. It's Redis with an HTTP layer and multi-tenancy on top. If you need
   Lua scripting, pub/sub, or streams, use Redis directly. If you need a
   key-value store for a handful of projects, this removes the setup."

4. "How fast is it?"
   "Reads are sub-millisecond in Redis; what you actually measure is network
   latency to the API. Your real p50, p95, and p99 are on the Usage page —
   measured, not promised."

5. "What data types are supported?"
   "Strings, lists, hashes, and sets, plus TTLs and atomic counters. Sorted
   sets and streams aren't exposed yet."

6. "Can I use it from the browser?"
   "You shouldn't. An API key in client-side JavaScript is a public API key.
   Call it from your server."

7. "What happens when I hit a limit?"
   "During beta, nothing — limits are displayed but not enforced, and you'll
   get an email well before that changes."

8. "Can I export or delete everything?"
   "Yes. Flush a project's data or delete the project outright from the
   dashboard, and deleting your account removes every project and key with it."
```

---

## 10. Roadmap

```
[PASTE DESIGN SYSTEM]

Screen: Roadmap section on #FFFFFF.

Centered header: eyebrow "What's next", heading "Shipping in the open.", one
line of body copy: "Here's what exists today and what's being built. No dates —
they'd be fiction."

A horizontal three-column timeline. A single 2px horizontal line runs across
the section at the top of the columns; each column has a marker sitting on that
line. Marker 1 is a filled #DC382D circle with a white check. Marker 2 is a
white circle with a 2px #DC382D border. Marker 3 is a white circle with a 2px
#D4CBC7 border.

Column 1 — "Shipped", marker filled:
A 12px uppercase label in #DC382D reading "Shipped", then a checklist of five
14px rows each with a small red check:
  Accounts, sessions, and roles
  Per-project API keys with rotation
  Data browser with pattern search
  Usage metrics and latency percentiles
  Admin console

Column 2 — "In progress", marker outlined red:
Label in ink. Four rows with small empty circles:
  Client libraries for JS and Python
  Password reset and email verification
  Sorted sets and streams
  Higher limits and paid tiers

Column 3 — "Later", marker outlined grey, entire column at 70% opacity:
Label in muted. Four rows with small empty grey circles:
  Webhooks on key events
  Pub/sub over server-sent events
  Team accounts and shared projects
  Regional deployments
```

---

## 11. Final CTA + Footer

```
[PASTE DESIGN SYSTEM]

Screen: Closing call to action and footer.

CTA BAND — full width, background #1C1614, 88px vertical padding, centered
content, max-width 720px.
- Heading in white, 40px/700: "Stop configuring Redis."
- Sub-line in #9A908B, 17px: "One account, one namespace, one key. Free while
  we're in beta."
- A button row, centered: a primary red "Create your account" and a secondary
  button that is transparent with a 1px #4A403C border and #F5EFEC text,
  reading "Read the docs".
- Below the buttons, 13px #9A908B: "No credit card. Delete everything in one
  click if it isn't for you."

FOOTER — background #16110F, 56px top padding, 32px bottom.
Four columns of links, then a bottom bar.
- Column 1 (wider): the red hexagonal logo mark plus "Central Redis" wordmark in
  white 16px/600, then two lines of 13px #9A908B: "Multi-tenant Redis, exposed
  over HTTP. Built and run by one person."
- Column 2, label "Product": Features, Pricing, Dashboard, Status.
- Column 3, label "Developers": Documentation, API reference, Quickstart,
  Changelog.
- Column 4, label "Elsewhere": GitHub, LinkedIn, Portfolio, Email.
All link text 13px #9A908B; column labels 12px uppercase #F5EFEC.

Bottom bar: a 1px #2A2320 top border, 20px padding, with "© 2026 Central Redis"
on the left in 12px #6B605C and, on the right, a small row containing a green
dot plus the 12px text "All systems operational".
```

---

## 12. Sign Up (bridge into the app)

```
[PASTE DESIGN SYSTEM]

Screen: Sign-up page. This is the seam between the marketing site and the
dashboard, so it must look like both.

Split layout, full viewport height.

LEFT PANEL (45%, background #1C1614): centered content, 48px padding.
The red hexagonal logo mark at 36px. Headline in white, 32px:
"Redis for every project you ship." Sub-line in #9A908B: "One API key. One base
URL. Isolated namespaces. No connection strings to manage."
Below, a dark code block on a slightly lighter surface (#241D1A) showing a
short syntax-highlighted curl POST to /my_app/set/session.
At the bottom of the panel, three small rows each with a red check icon and
13px #9A908B text: "Free while in beta", "Live in under a minute",
"Delete everything in one click".

RIGHT PANEL (55%, background #FBF9F8): a centered 380px form card.
Title "Create your account" 28px/600, sub-line in muted 14px: "Free. No credit
card."
Fields stacked with 14px gaps: Name (marked optional in muted text), Email,
and Password with a show/hide text toggle inside the field's right edge and a
thin three-segment strength meter below it, plus 12px helper text "At least 10
characters."
A full-width primary red "Create account" button.
Footer line, centered, 13px: "Already have an account? Sign in" with the link
in #DC382D.
Below that, 12px muted centered: "By signing up you agree to the terms."
```

---

## 13. Mobile — Hero and Features

```
[PASTE DESIGN SYSTEM]

Screen: Mobile viewport, 390px wide. The top of the marketing page.

HEADER — 60px, #FBF9F8: logo mark and "Central Redis" wordmark on the left, a
hamburger icon on the right. A small primary red "Start free" button sits
between them, compact at 32px tall.

HERO — 40px top padding, 20px side gutters, single column, left-aligned:
- The status pill: #FDF0EF, green dot, 11px text "Live in production".
- Headline 34px/700, tight, three lines: "One Redis layer. Every project you
  ship." with the second sentence in #DC382D.
- Sub-headline 15px #6B605C, four lines.
- A full-width primary red "Start free" button, then a full-width secondary
  "Read the docs" button below it, 10px gap.
- A dark code card, full width, 12px radius, horizontally scrollable, showing
  the curl example with the response line in green. A small fade gradient on
  the right edge hints at the scroll.

FEATURES — on #FFFFFF, 48px vertical padding:
Centered eyebrow and a 26px heading, then feature cards stacked vertically at
full width with 12px gaps. Each card is white with a 1px border, 20px padding,
containing a red 20px outlined icon, a 16px/600 title, and two lines of 14px
body copy.

Also render the open mobile menu as a separate state: a full-screen #FBF9F8
overlay with a close X top right, then large 22px nav links stacked with 24px
gaps — Features, How it works, Docs, Pricing, Sign in — and a full-width
primary red "Start free" button pinned near the bottom.
```

---

## Generation order

1. Hero (#1) — sets the entire visual language
2. Features grid (#4) — establishes card style
3. Product showcase (#2) — the most persuasive section
4. Code samples (#5) and Playground (#6)
5. Pricing (#7), FAQ (#9)
6. How it works (#3), Roadmap (#10), Founder note (#8)
7. CTA + Footer (#11), Sign up (#12), Mobile (#13)

If a section comes back wrong, give Stitch a targeted follow-up — "make the
feature cards denser, 20px padding, and move the mono detail line above the
title" — rather than regenerating from scratch.

---

## What changed from the current site

The live site is a pre-launch waitlist page. These prompts assume production,
which changes several things:

| Current site | These prompts |
|---|---|
| "Request Early Access" → waitlist form | "Start free" → `/signup` |
| "Currently in private use" | "Live in production — free while in beta" |
| No pricing | Free tier with the real limits |
| No product screenshots | Dashboard, browser, and console screenshots |
| No code beyond one hero snippet | Five-language tabs plus a live playground |
| No FAQ | Eight questions, including the honest ones |
| Roadmap: Now / Next / Later | Shipped / In progress / Later, with real items |

Copy that should carry over largely unchanged: the founder quote — it's the
most human thing on the page and it's true.

## Accuracy checklist

Verify these against the app before publishing, since they're load-bearing:

- Free tier: **1 project**, 10,000 keys, 100 MB, 1M requests/month, 10 API keys
- Data types: strings, lists, hashes, sets — **not** sorted sets or streams
- Limits are **displayed but not enforced** (`ENFORCE_LIMITS=false`)
- API keys are stored hashed and shown once; rotation is immediate
- Latency figures come from **histogram buckets**, so a p95 is an upper bound —
  don't print a specific "sub-millisecond" API latency claim anywhere
- The public API domain in every snippet must match your real deployment
  (`redis.mohammadramiz.in` today, not `api.central-redis.dev`)
- "All systems operational" in the footer implies a status page — either build
  one or drop that element
