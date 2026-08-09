# Central — Stitch Design Prompts

Dashboard-only. Redis-branded. No billing screens.

**How to use this file:** Stitch works best one screen at a time, not one giant prompt. Paste **Section 0 (Design System)** first and let it generate the base — then for each screen, paste the Design System block again followed by that screen's prompt. Repeating the system block every time is what keeps the screens visually consistent; Stitch does not carry style memory reliably between separate generations.

Product name placeholder throughout is **Central**. Find-and-replace if you pick something else.

---

## 0. Design System (paste this at the top of EVERY screen prompt)

```
Design system for a developer tool called "Central" — a hosted multi-tenant
Redis service. Bold, Redis-branded, high contrast, confident.

COLORS
- Primary / brand red: #DC382D  (Redis red — used for primary buttons, active
  nav state, logo mark, key accents. Use it decisively but not everywhere.)
- Primary hover: #B92E24
- Primary subtle background: #FDF0EF (light mode) / rgba(220,56,45,0.12) (dark)
- Ink / text primary: #16110F  (warm near-black, not pure black)
- Text secondary: #6B605C
- Text muted: #9A908B
- Surface / page background: #FBF9F8 (warm off-white)
- Card surface: #FFFFFF
- Border: #E8E2DF
- Border strong: #D4CBC7
- Success: #1B8A5A   Warning: #C77A11   Danger: #C0271C   Info: #2563A8
- Code block background: #1C1614 (dark warm charcoal) with #F5EFEC text

TYPOGRAPHY
- UI font: Inter. Headings tight (-0.02em letter spacing), weight 600–700.
- Monospace font: JetBrains Mono — used for ALL of: API keys, Redis keys,
  values, endpoints, code samples, IDs, numbers in tables.
- Scale: page title 28px/600, section heading 18px/600, body 14px/400,
  label 12px/500 uppercase with 0.06em tracking, mono 13px.

SHAPE & DEPTH
- Border radius: 8px cards and inputs, 6px buttons, 4px badges and chips.
- Shadows are subtle: 0 1px 2px rgba(22,17,15,0.06). No heavy drop shadows.
- 1px borders do most of the structural work, not shadows.
- Generous padding: 24px card padding, 32px page gutters.

COMPONENTS
- Buttons: primary = solid #DC382D with white text. Secondary = white with
  #D4CBC7 border. Danger = white with #C0271C border and red text; solid red
  only inside confirmation dialogs. Ghost = text only.
- Inputs: 40px tall, 1px #D4CBC7 border, white fill, focus ring is a 3px
  #DC382D glow at 20% opacity.
- Badges: small, 4px radius, tinted background with darker text of same hue.
- Tables: no vertical rules, 1px horizontal dividers, sticky header row with
  uppercase 12px labels, hover row highlight #FBF9F8, 44px row height.
- Copy-to-clipboard: a small ghost icon button that sits at the right edge of
  any monospace value. This appears constantly — treat it as a core component.
- Empty states: centered, an outlined icon, one bold line, one muted line,
  one primary button.

LAYOUT
- Persistent left sidebar, 240px, white with a 1px right border.
  Top: logo (a red hexagonal Redis-like mark + "Central" wordmark).
  Below: a project switcher — the current project name in monospace with a
  chevron. Then nav items with 18px outlined icons: Overview, Data Browser,
  API Console, API Keys, Usage, Settings.
  Bottom: user avatar, email, and a settings gear.
- Top bar, 56px: current page title on the left; on the right a "Docs" ghost
  link and the project's base URL shown in monospace with a copy button.
- Content area max-width 1200px, centered, 32px gutters.

TONE
Precise and technical. Labels are lowercase-technical where they name real
API concepts (x-api-key, TTL, project_id). Never cute. No emoji in the UI.
```

---

## 1. Sign Up

```
[PASTE DESIGN SYSTEM]

Screen: Sign up.

Split layout, full viewport height.

LEFT PANEL (45% width, background #1C1614 dark charcoal): centered content.
The red hexagonal Central logo mark at top. Headline in white, 32px:
"Redis for every project you ship." Subline in #9A908B: "One API key. One
base URL. Isolated namespaces. No connection strings to manage." Below that,
a terminal-style code block on a slightly lighter charcoal surface showing:

  curl -X POST https://api.central.dev/my_app/set/session \
    -H "x-api-key: sk_live_8Kd..." \
    -d '{"value": {"user": 42}, "ttl": 3600}'

with syntax coloring — red for the method, muted grey for flags, off-white
for URLs and strings.

RIGHT PANEL (55%, background #FBF9F8): a centered 380px-wide form card.
Title "Create your account" 28px/600. Fields: Email, Password (with a
show/hide eye toggle and a thin 3-segment strength meter below it). A
full-width primary red "Create account" button. Below it a horizontal rule
with "or" centered, then two secondary buttons with logos: "Continue with
GitHub" and "Continue with Google". Footer text: "Already have an account?
Sign in" with the link in red.

Small muted line at the very bottom: "Free while in beta. No credit card."
```

---

## 2. Sign In

```
[PASTE DESIGN SYSTEM]

Screen: Sign in.

Same split layout as the sign-up screen — identical dark left panel with the
logo, headline, and code block. Right panel holds a centered 380px form card:
title "Sign in to Central", Email field, Password field with show/hide toggle,
a right-aligned "Forgot password?" ghost link directly under the password
field, then a full-width primary red "Sign in" button. Horizontal rule with
"or", then "Continue with GitHub" and "Continue with Google" secondary
buttons. Footer: "New to Central? Create an account" with the link in red.

Also show an error variant of this same card: a red-tinted alert bar
(#FDF0EF background, #C0271C left border 3px, dark red text) above the email
field reading "Incorrect email or password."
```

---

## 3. Projects — Empty State

```
[PASTE DESIGN SYSTEM]

Screen: Projects list, empty state. Logged-in shell — show the full left
sidebar and top bar from the design system, with "Projects" active in the nav.
The project switcher in the sidebar reads "No project selected" in muted text.

Page header row: title "Projects" 28px/600 on the left, primary red button
"New project" with a plus icon on the right.

Main content is a large centered empty state inside a dashed-border card
(1px dashed #D4CBC7, 12px radius, 80px vertical padding): an outlined
database/stack icon in red at 48px, then bold 18px "No projects yet", then
muted 14px "A project gives you an isolated Redis namespace and its own API
key. Create one to get started." Then a primary red "Create your first
project" button.

Below the empty state card, a horizontal row of three small "quickstart"
cards, each with a small mono label, a one-line description, and a ghost
"Read →" link: "Quickstart" / "Get from zero to your first key in 2 minutes",
"API reference" / "Every endpoint, with curl and JS examples",
"Key namespacing" / "How Central isolates your data per project".
```

---

## 4. Projects — List

```
[PASTE DESIGN SYSTEM]

Screen: Projects list, populated.

Page header: title "Projects", primary red "New project" button on the right.
Below the header a search input with a magnifier icon, placeholder
"Search projects", 320px wide, left-aligned.

Then a grid of project cards, 3 per row, 16px gap. Each card (white, 1px
border, 8px radius, 20px padding) contains:
- Top row: project name in 16px/600 monospace on the left; a status dot
  (green) with the label "active" in 12px on the right.
- The base URL in 12px monospace muted, truncated with a copy icon button:
  api.central.dev/checkout_svc
- A thin divider.
- A 3-column mini stat row, each column a 12px uppercase label above an 18px
  monospace value: KEYS 1,284 · MEMORY 4.2 MB · REQS 24H 18.3k
- Bottom row: relative timestamp "created 12 days ago" in muted 12px on the
  left, and a "⋯" ghost icon button on the right that opens a menu.

Show 6 cards with realistic varied names: checkout_svc, user_sessions,
rate_limiter, feature_flags, analytics_buffer, ml_cache. Vary the numbers
meaningfully — rate_limiter should have a high request count and few keys;
analytics_buffer should have many keys and low requests. Give one project
(ml_cache) an amber status dot with the label "idle".

Also show the open state of the "⋯" menu on one card: a small white dropdown
with items Open, Copy base URL, Rotate API key, a divider, then "Delete
project" in danger red.
```

---

## 5. Create Project — Modal

```
[PASTE DESIGN SYSTEM]

Screen: The projects list, dimmed behind a modal overlay (rgba(22,17,15,0.4)).

Centered modal, 480px wide, white, 12px radius, subtle shadow.
Header: "Create project" 20px/600, with an X close button top right.
Body, 24px padding:
- Field "Project ID" with a monospace input, placeholder "my_project".
  Helper text below in 12px muted: "Lowercase letters, numbers, and
  underscores. Spaces and hyphens are converted automatically. This becomes
  part of your URL and cannot be changed later."
- A live preview strip below the input — a #FBF9F8 filled box with 12px
  monospace text showing: api.central.dev/checkout_svc/get/{key}
  with "checkout_svc" highlighted in red as the user-typed portion.
- Field "API key" with a monospace input pre-filled with a generated key
  (sk_live_ prefix then a long random string), a "Generate" ghost button with
  a refresh icon inside the input's right edge, and a copy icon button.
  Helper text: "Shown once in full. Store it somewhere safe."
- An info callout bar (#F2F6FA background, blue left border 3px) with an
  info icon: "Keys are stored hashed. If you lose this one you'll need to
  rotate it."
Footer, right-aligned, on a #FBF9F8 strip: secondary "Cancel" and primary
red "Create project".
```

---

## 6. Project Overview

```
[PASTE DESIGN SYSTEM]

Screen: Project overview — the landing page after opening a project. Sidebar
project switcher shows "checkout_svc" in monospace; "Overview" is the active
nav item.

Page header: title "checkout_svc" in 28px monospace/600 with a small green
"active" badge beside it. On the right, a secondary "Open in API Console"
button.

ROW 1 — Connection card, full width, white, 1px border. Section heading
"Connection". Two stacked rows, each a 12px uppercase label on the left
(120px column) and a monospace value on the right with a copy button:
  BASE URL   https://api.central.dev/checkout_svc
  API KEY    sk_live_••••••••••••••••••••••••3f9a   [eye toggle] [copy]
Below those, a tabbed code block (dark #1C1614) with tabs: cURL, JavaScript,
Python. The JavaScript tab is active, showing syntax-highlighted code:

  const res = await fetch(
    "https://api.central.dev/checkout_svc/set/cart:42",
    {
      method: "POST",
      headers: {
        "x-api-key": process.env.CENTRAL_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ value: { items: 3 }, ttl: 3600 })
    }
  );

with a copy button floating in the code block's top-right corner.

ROW 2 — Four stat cards in a row. Each: 12px uppercase label, 28px monospace
value, and a small delta chip below (green ↑ or red ↓ with a percentage).
  TOTAL KEYS 1,284 (↑ 4.2%) · MEMORY USED 4.2 MB (↑ 1.1%) ·
  REQUESTS 24H 18,342 (↑ 12.8%) · ERROR RATE 0.03% (↓ 0.01%)

ROW 3 — Two columns, 60/40 split.
LEFT: card titled "Requests" with a segmented control top-right (24h / 7d /
30d, "24h" selected). Inside, a smooth area chart in Redis red with a soft
red gradient fill fading to transparent, x-axis showing hours, y-axis showing
request counts, and a subtle dotted horizontal grid.
RIGHT: card titled "Operations" — a horizontal bar list, each row showing an
operation name in monospace on the left, a red bar, and a count on the right:
GET 9,120 · SET 4,880 · HGETALL 1,940 · INCR 1,402 · LRANGE 620 · DELETE 380.

ROW 4 — Card titled "Recent activity" with a "View all" ghost link top-right.
A table with columns TIME, METHOD, ENDPOINT, STATUS, DURATION. Six rows of
realistic data — method as a small colored badge (GET blue-tinted, POST
green-tinted, DELETE red-tinted), endpoint in monospace like
/set/cart:1042, status as 200 in green or 404 in amber, duration like 12ms.
```

---

## 7. Data Browser

```
[PASTE DESIGN SYSTEM]

Screen: Data Browser — a two-pane key explorer. "Data Browser" active in nav.

Page header: title "Data Browser". On the right, a secondary "Refresh" button
with a refresh icon and a primary red "New key" button.

Below the header, a toolbar row: a wide search input with a magnifier and
monospace placeholder "Filter keys by pattern — e.g. cart:*" (400px); a
"Type" dropdown filter showing "All types"; and on the far right muted 13px
text "1,284 keys · 4.2 MB".

MAIN AREA — two panes side by side, 380px left pane and the rest right.

LEFT PANE (white card, 1px border, its own scroll): a dense list of keys.
Each row is 44px: a small 3-letter type badge on the left (STR blue-tinted,
LST purple-tinted, HSH amber-tinted, SET green-tinted), then the key name in
13px monospace truncated in the middle, then on the right a tiny TTL chip in
muted 11px monospace (e.g. "58m", "2d", or "∞" for no expiry). Selected row
has a #FDF0EF background and a 2px red left border. Show about 14 rows with
realistic namespaced keys: cart:1042, cart:1043, session:a91f, session:b22c,
ratelimit:ip:8.8.8.8, flags:checkout_v2, queue:emails, user:profile:88,
metrics:daily, lock:payment:1042. Sticky at the bottom of the pane: a "Load
more" ghost button with muted text "Showing 50 of 1,284".

RIGHT PANE (white card): the detail view for the selected key cart:1042.
- Header row: the key name in 16px monospace/600 with a copy button, and on
  the right a row of icon buttons — Edit (pencil), Set TTL (clock),
  Duplicate, and Delete (trash, in danger red).
- A metadata strip: four inline label/value pairs in 12px —
  TYPE string · SIZE 248 B · TTL 58m 12s · CREATED 2h ago.
  The TTL value has a small circular countdown ring next to it in red.
- A tabbed area with tabs "Value" (active), "Raw", "History".
  The Value tab shows a pretty-printed, syntax-highlighted JSON viewer on a
  #FBF9F8 background with collapsible object nodes (small triangles), line
  numbers in a muted gutter, and keys in dark red with strings in green:

    {
      "user_id": 1042,
      "items": [
        { "sku": "TS-BLK-M", "qty": 2, "price": 2400 },
        { "sku": "HD-GRY-L", "qty": 1, "price": 5900 }
      ],
      "currency": "usd",
      "updated_at": "2026-08-09T14:22:01Z"
    }

  A copy button sits in the viewer's top-right.

Also render a second variant of the right pane showing a LIST type key
(queue:emails) — instead of the JSON viewer, an indexed table with columns
INDEX (monospace muted) and VALUE (monospace), 6 rows, plus "LPUSH" and
"RPUSH" ghost buttons in the header and a small trash icon at the end of
each row on hover.
```

---

## 8. Key Editor — Modal

```
[PASTE DESIGN SYSTEM]

Screen: Data Browser dimmed behind a modal overlay.

Centered modal, 560px wide.
Header: "Edit key" with the key name cart:1042 in monospace beside it, and an
X close button.
Body:
- A "Type" segmented control with options String, List, Hash, Set — "String"
  selected, and a muted 12px note beside it: "Type cannot be changed after
  creation."
- Field "Key" — monospace input containing cart:1042, with a muted prefix
  chip inside the input's left edge reading "checkout_svc:" in grey to show
  the automatic namespace.
- Field "Value" — a tall (200px) monospace code editor with line numbers,
  a #FBF9F8 background, and syntax-highlighted JSON. Above its top-right
  corner, two small ghost toggle buttons: "JSON" (active) and "Raw".
  Below the editor, a green check icon with 12px text "Valid JSON".
- Field "TTL" — a number input (120px) followed by a unit dropdown
  (seconds / minutes / hours / days) set to "minutes", and beside them a
  checkbox "No expiry". Helper text: "Leave blank to keep the current TTL."
Footer strip: a ghost "Delete key" button in danger red on the far LEFT,
then right-aligned secondary "Cancel" and primary red "Save changes".
```

---

## 9. API Console

```
[PASTE DESIGN SYSTEM]

Screen: API Console — an interactive request builder, like Postman but
minimal and embedded. "API Console" active in nav.

Page header: title "API Console", with muted 13px subtext below it: "Send
real requests against checkout_svc. Requests here count toward your usage."

Layout is two columns, 50/50, with a full-height divider between them.

LEFT COLUMN — the request builder.
- Row 1: a method-and-path bar. A dropdown on the left showing "POST" with a
  green tint (the dropdown lists GET, POST, DELETE), then a monospace input
  taking the remaining width. Inside the input's left edge, a non-editable
  grey prefix chip "/checkout_svc" then the editable portion "/set/cart:1042".
  A primary red "Send" button with a paper-plane icon on the far right.
- Row 2: an operation picker — a horizontal scrolling row of small chips
  grouped under 12px uppercase labels:
    STRINGS: get, set, delete, expire, ttl, incr, mset, mget
    LISTS: lpush, rpush, lrange, lpop, rpop
    HASHES: hset, hget, hgetall, hdel
    UTILITY: keys, flush
  The "set" chip is active — filled red with white text. Others are outlined.
- Row 3: tabs "Body" (active), "Headers", "Params".
  Body tab: a monospace JSON editor, 240px tall, line numbers, showing
    {
      "value": { "items": 3, "total": 8700 },
      "ttl": 3600
    }
  Headers tab preview: a two-column key/value table with one locked row —
  x-api-key with the value shown masked and a lock icon, plus a muted note
  "Injected automatically from this project's key."

RIGHT COLUMN — the response.
- A status bar: a green "200 OK" badge, then muted monospace metrics
  "· 14 ms · 86 B".
- Tabs "Response" (active), "Headers", "cURL".
  Response tab: syntax-highlighted JSON on #FBF9F8 with line numbers:
    {
      "ok": true,
      "key": "cart:1042",
      "ttl": 3600
    }
  A copy button top-right.
  cURL tab preview: a dark code block with the full equivalent curl command,
  the API key masked, and a copy button.
- Below the response, a collapsed section header "History" with a chevron and
  a count badge "12". Expanded, it shows a compact list of past requests —
  each row a method badge, a monospace endpoint, a status code, a duration,
  and a relative timestamp, with a small circular-arrow "replay" icon button
  appearing at the right on hover.
```

---

## 10. API Keys

```
[PASTE DESIGN SYSTEM]

Screen: API Keys. "API Keys" active in nav.

Page header: title "API Keys", muted subtext "Keys grant full read and write
access to checkout_svc. Treat them like passwords." Primary red "Create key"
button on the right.

A table card, full width. Columns: NAME, KEY, CREATED, LAST USED, and a
trailing actions column.
Rows (4 of them):
  "Production" · sk_live_••••••••••••3f9a with an eye toggle and copy button ·
    Jul 22, 2026 · 2 minutes ago
  "Staging" · sk_live_••••••••••••7b21 · Jul 22, 2026 · 4 hours ago
  "Local dev" · sk_live_••••••••••••c04e · Aug 01, 2026 · 3 days ago
  "CI pipeline" · sk_live_••••••••••••91ff · Aug 04, 2026 · never  ← this
    row's "never" is in amber, and the row has a small amber warning icon
    with a tooltip "Unused for 5 days"
Each row's actions column has a "⋯" ghost button. Show one open menu with
items: Rename, Copy, a divider, "Rotate key" and "Revoke key" both in danger
red.

Below the table, a "Danger zone" card — white with a 1px #C0271C border and
a #FDF0EF tinted header strip. Section title "Danger zone" in danger red.
Two rows, each with a bold label and muted description on the left and a
danger-outline button on the right:
  "Flush all data" / "Permanently delete all 1,284 keys in this project.
   The project and its API keys are kept." → button "Flush project"
  "Delete project" / "Permanently delete checkout_svc, all of its data, and
   all of its API keys." → button "Delete project"
```

---

## 11. Destructive Confirmation — Modal

```
[PASTE DESIGN SYSTEM]

Screen: A confirmation modal over a dimmed API Keys page.

Modal, 440px wide, white, 12px radius. The top edge has a 4px solid #C0271C
accent bar.
Body, centered-left aligned:
- A 40px circular #FDF0EF background containing a red outlined warning
  triangle icon.
- Title "Delete checkout_svc?" 20px/600.
- Body text 14px: "This deletes the project, all 1,284 keys, and all 4 API
  keys. Any service still using this key will start receiving 404s
  immediately. This cannot be undone."
- A field labeled "Type the project ID to confirm" with a monospace input
  below it, placeholder text showing "checkout_svc" in very light grey.
Footer: a full-width row with secondary "Cancel" and a solid danger-red
"Delete project" button that is visibly DISABLED (reduced opacity) because
the confirm field is empty.
```

---

## 12. Usage

```
[PASTE DESIGN SYSTEM]

Screen: Usage. "Usage" active in nav.

Page header: title "Usage" with a date-range segmented control on the right
(24h / 7d / 30d, "7d" selected) and a secondary "Export CSV" button.

ROW 1 — a free-tier limits card, full width, white. Section heading "Plan
limits" with a small red-tinted "Beta — free" badge beside it. Three
horizontal progress meters stacked, each with: a 13px label on the left, a
monospace current/limit value on the right, and below them a 6px rounded
track with a red fill.
  Keys        1,284 / 10,000    (13% filled)
  Storage     4.2 MB / 100 MB   (4% filled)
  Requests    142k / 1M per month (14% filled)
Muted footnote: "Limits are generous during beta and are not enforced yet.
We'll email you well before anything changes."

ROW 2 — a large card "Requests over time". A stacked area chart, x-axis
showing 7 days. Three stacked series with a legend above the chart:
reads in Redis red, writes in a deeper maroon, and errors in amber.
Hovering shows a tooltip — render one visible tooltip in the middle of the
chart, a dark #1C1614 rounded box showing a date and three colored rows with
monospace values.

ROW 3 — two cards side by side, 50/50.
LEFT: "Top keys by size" — a table with columns KEY (monospace), TYPE (badge),
SIZE (monospace), and a thin inline red bar behind the size value showing
relative magnitude. Six rows, sizes descending from 412 KB down to 18 KB.
RIGHT: "Latency" — a card with three big stat blocks in a row (p50 8ms,
p95 34ms, p99 112ms, each a 12px uppercase label above a 24px monospace
value) and below them a small sparkline line chart in red.

ROW 4 — a card "Errors" with a table: TIME, ENDPOINT, STATUS, MESSAGE.
Four rows showing realistic failures — 401 "Invalid API key", 404 "Project
not found", 404 "Key not found" — with status codes as amber and red tinted
badges. If there were no errors, show instead a compact empty state with a
green check icon and the line "No errors in the last 7 days."
```

---

## 13. Project Settings

```
[PASTE DESIGN SYSTEM]

Screen: Settings. "Settings" active in nav.

Page header: title "Settings".

A left-side vertical sub-nav (180px) with items General (active), Members,
Notifications — each a 36px row, the active one having a #FDF0EF background
and red text.

To its right, a stack of setting cards, each white with 1px border, 24px
padding, and a footer strip (#FBF9F8, 1px top border, 12px padding) that is
right-aligned and holds a single "Save" button.

CARD 1 "Project details":
  - Field "Display name" — a normal text input containing "Checkout Service".
  - Field "Project ID" — a monospace input containing "checkout_svc" that is
    DISABLED (grey fill, muted text) with a small lock icon inside its right
    edge. Helper: "The project ID is part of your API URL and can't be
    changed. Create a new project if you need a different ID."
  - Field "Description" — a 3-row textarea with placeholder "What is this
    project for?"

CARD 2 "Data retention":
  - Field "Default TTL" — a number input (120px) and a unit dropdown set to
    "hours", with a checkbox below: "Apply to keys created without an
    explicit TTL". Helper: "Existing keys are not affected."
  - A toggle switch row: "Evict least-recently-used keys when full" — the
    toggle is ON and rendered in red. Muted description below it.

CARD 3 "Access":
  - A toggle row "Restrict by IP address" — currently OFF. When off, show a
    muted, visually disabled textarea below it with placeholder
    "203.0.113.0/24, 198.51.100.42" and helper text "One CIDR range or
    address per line."
  - A toggle row "Require HTTPS" — ON and disabled, with a lock icon and
    muted text "Always enabled."
```

---

## 14. Account Settings

```
[PASTE DESIGN SYSTEM]

Screen: Account settings — reached from the user avatar at the bottom of the
sidebar. The sidebar has no nav item highlighted; the top bar title reads
"Account".

Left vertical sub-nav (180px): Profile (active), Security, Sessions.

CARD 1 "Profile": a 64px circular avatar with a red "Change" ghost button
beside it, then fields Name and Email (email input has a green "Verified"
badge inside its right edge). Footer with a "Save" button.

CARD 2 "Password": Current password, New password with a strength meter, and
Confirm new password. Footer with an "Update password" button.

CARD 3 "Two-factor authentication": a row with a bold label, muted
description "Add a second step when signing in", and a red-tinted "Not
enabled" badge on the right, plus a secondary "Enable 2FA" button.

CARD 4 "Active sessions": a table with columns DEVICE, LOCATION, LAST ACTIVE,
and a trailing action. Three rows — one marked with a green "This device"
badge, the others having a ghost "Revoke" button in danger red. Below the
table, a ghost danger link "Sign out of all other sessions".

CARD 5 "Danger zone": white card, 1px #C0271C border, tinted header. One row:
"Delete account" with the muted description "Permanently delete your account,
all projects, and all data." and a danger-outline "Delete account" button.
```

---

## 15. Onboarding / Quickstart

```
[PASTE DESIGN SYSTEM]

Screen: Quickstart — shown right after a user creates their first project.

Centered single column, 720px max width, no left sidebar (this is a focused
full-page flow). At the very top, a slim ghost "Skip to dashboard →" link,
right-aligned.

Title, centered: "checkout_svc is ready" 32px/600, with a green check icon
in a circle above it. Muted subline: "Three steps and you're storing data."

Then a vertical stepper — a thin vertical line running down the left with
numbered 28px circular markers. Step 1's marker is filled red with a white
check; steps 2 and 3 are outlined with grey numbers.

STEP 1 "Save your API key" — completed, its card collapsed to a single line
showing the masked key in monospace with a copy button and a green check.

STEP 2 "Store your first value" — expanded, the active step. Card contains a
tabbed dark code block (cURL / JavaScript / Python) with the cURL tab active:

  curl -X POST https://api.central.dev/checkout_svc/set/hello \
    -H "x-api-key: $CENTRAL_KEY" \
    -H "Content-Type: application/json" \
    -d '{"value": "world", "ttl": 3600}'

with a copy button. Below the code block, a muted 13px line: "Run this in
your terminal — we'll detect it automatically." and beside it a small
red pulsing dot with the text "Waiting for your first request…".

STEP 3 "Read it back" — collapsed and dimmed, showing only its title.

At the bottom, outside the stepper, a row of three small ghost link cards:
"Full API reference →", "Client libraries →", "Key naming patterns →".
```

---

## 16. Mobile — Data Browser

```
[PASTE DESIGN SYSTEM]

Screen: Mobile viewport, 390px wide. The Data Browser adapted for phone.

Top bar, 56px: a hamburger menu icon on the left, the project name
"checkout_svc" in 15px monospace/600 centered, and a search icon on the
right.

Below it, a horizontal scrolling filter chip row: "All", "String", "List",
"Hash", "Set" — "All" is active, filled red.

Then a stat strip: two inline muted 12px values separated by a dot —
"1,284 keys · 4.2 MB".

The key list fills the rest of the screen — full-width rows, 60px tall,
1px dividers. Each row: a type badge and the key name in 13px monospace on
the first line, then a second line in 11px muted showing the size and TTL
("248 B · expires in 58m"), with a chevron on the far right.

A floating action button, bottom right, 56px circle, solid Redis red with a
white plus icon and a soft shadow.

A bottom tab bar, 64px, white with a 1px top border, four tabs with outlined
icons and 10px labels: Overview, Data (active, icon and label in red),
Console, Usage.

Also render the key detail as a bottom sheet: a rounded-top-corner white
sheet covering 75% of the screen with a grab handle at the top, the key name
in monospace, the metadata strip wrapped onto two lines, the JSON viewer
below, and a sticky footer row with a secondary "Edit" and a danger-outline
"Delete" button.
```

---

## Generation order

Do them in this order — each one gives Stitch more context for the next, and
the early ones lock in the visual language:

1. Project Overview (#6) — the densest screen, sets the whole tone
2. Data Browser (#7) — the second anchor
3. Projects List (#4)
4. API Console (#9)
5. Usage (#12)
6. API Keys (#10)
7. Sign In / Sign Up (#1, #2)
8. Modals (#5, #8, #11)
9. Settings (#13, #14)
10. Onboarding (#15) and Mobile (#16)

If a screen comes back wrong, don't re-roll the whole thing — Stitch responds
better to a targeted follow-up like "make the left key list denser, 40px
rows, and move the TTL chip inline with the key name" than to a full rewrite.

---

## Backend gaps this design implies

The UI above is deliberately ahead of the current backend. Everything below
is drawn by the design but does **not** exist in `main.py` yet. Worth knowing
before you get attached to a screen.

**Exists today and maps cleanly:**
Per-project namespacing, `x-api-key` auth, all string/list/hash operations,
`/keys`, `/flush`, project create and remove via the admin panel, MongoDB-
backed project persistence.

**Does not exist — needs building:**

| UI element | What's missing |
|---|---|
| Sign up / sign in / sessions | There are no user accounts at all. Today there is one global `ADMIN_PASSWORD`. This is the single biggest piece of work — a users table, sessions or JWTs, and a `user_id` foreign key on every project. |
| Projects belonging to a user | `PROJECT_REGISTRY` is global. Every project is visible to whoever loads `/admin`. Ownership has to be added before multi-user is safe. |
| Multiple API keys per project | The model is one key per project. The API Keys screen assumes many, with names and independent revocation. |
| Key rotation | No endpoint. |
| Last-used timestamps | Not tracked. |
| Type badges (STR/LST/HSH) | The API never returns a key's type. Needs `TYPE` exposed, probably folded into `/keys`. |
| Key sizes and memory totals | Needs `MEMORY USAGE` per key and an aggregate. |
| Request counts, latency, error rates, charts | Nothing is instrumented. All of Usage and the Overview charts need a metrics pipeline — at minimum a middleware writing counters into Redis. |
| Request history in the API Console | Not stored. |
| Pattern search and pagination in the browser | `/keys` returns everything at once via `redis.keys()`. Needs `SCAN` with a cursor and a match pattern — which also fixes the blocking problem flagged in the earlier scan. |
| Default TTL, LRU eviction toggle, IP allowlist | No settings layer exists. |
| Set type (SET badge) | Only strings, lists, and hashes are implemented. |
| 2FA, sessions list, account deletion | Follows from having accounts at all. |

**One thing to fix regardless of design:** `GET /admin` currently returns
every project ID and plaintext API key with no server-side auth. Whatever the
new UI looks like, that route needs real authentication before this is
exposed to a user base.
