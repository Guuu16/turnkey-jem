# Full-Stack Variant PDP

A small, production-minded product detail page with a server-authoritative API.
One product, two option dimensions, seven SKUs (including an unavailable
combination and a sold-out one), and a cart that cannot oversell the last unit.

- **Backend:** Python 3.11+, FastAPI, SQLite (standard-library `sqlite3`).
- **Frontend:** Next.js (App Router), React, TypeScript, hand-written CSS.
- **Storage:** SQLite file, seeded on start-up so the app is usable immediately.

---

## 1. Run it

### Backend (port 8000)

```powershell
cd app/backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS Terminal:

```bash
cd app/backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The database is created at `app/backend/data/shop.db` and seeded on first start.
Delete that file to reset stock and cart state.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_DB_PATH` | `backend/data/shop.db` | SQLite file location |
| `APP_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed browser origins |

Interactive OpenAPI docs: <http://127.0.0.1:8000/docs>. They describe the
schema; this README explains the behaviour and the examples.

### Frontend (port 3000, Windows and macOS; Node.js 20.9+)

```bash
cd app/frontend
npm install
npm run dev
```

Open <http://127.0.0.1:3000>.

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Where Next.js forwards `/api/*` |
| `API_BASE_URL` | `http://127.0.0.1:8000` | Backend URL used during server rendering |

The browser only ever calls same-origin `/api/*`; `next.config.ts` rewrites those
requests to FastAPI. That removes CORS from the browser path while the backend
still sends CORS headers for direct API use.

### Tests and checks

Run from the repository root:

```powershell
Push-Location app/backend
.\.venv\Scripts\python.exe -m pytest -q            # 33 passed
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m ruff format --check app tests
Pop-Location

Push-Location app/frontend
npm test                                            # 15 passed
npm run typecheck
npm run build
Pop-Location
```

macOS Terminal:

```bash
cd app/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check app tests
.venv/bin/python -m ruff format --check app tests
cd ../frontend
npm test
npm run typecheck
npm run build
```

---

## 2. Architecture

```text
Browser
  │  GET /  (HTML, server-rendered product)
  │  GET /api/products/{id}  POST /api/cart/items  GET /api/cart
  ▼
Next.js server (port 3000)  ── rewrite /api/* ──▶  FastAPI (port 8000)
                                                     │
                                                     ▼
                                              SQLite (WAL, one writer)
                                              products / options / skus
                                              carts / cart_items
                                              idempotency_keys
```

- The **server** owns price and stock. The client sends only `sku_id` and
  `quantity`; there is no price or stock accepted from the browser.
- The product page is a React Server Component: the first paint already has
  price, options and stock, so there is no price flicker.
- `ProductShell` provides a client-side product retry path when server
  rendering cannot reach FastAPI.
- `ProductDetailView` owns option resolution, quantity, add-to-cart feedback,
  and product refreshes after stock-changing actions.
- `lib/variants.ts` contains the pure SKU-resolution rules so they can be
  tested without rendering React.

---

## 3. Demo catalogue

One product: **Aurora Field Jacket** (`prod_aurora_field_jacket`), described by
`Colour` × `Size`.

| SKU | Colour | Size | Price | Stock | Notes |
| --- | --- | --- | --- | --- | --- |
| `sku_aurora_sand_s` | Sand | S | $129.00 | 4 | |
| `sku_aurora_sand_m` | Sand | M | $129.00 | 6 | |
| `sku_aurora_sand_l` | Sand | L | $129.00 | 1 | low stock, used by the race demo/test |
| `sku_aurora_olive_m` | Olive | M | $134.00 | 3 | |
| `sku_aurora_olive_l` | Olive | L | $134.00 | 2 | |
| `sku_aurora_ink_s` | Ink | S | $139.00 | 0 | **out of stock** |
| `sku_aurora_ink_m` | Ink | M | $139.00 | 5 | |

**Unavailable combinations:** Olive / S and Ink / L have no SKU at all. The UI
disables those values, so a customer can never select a combination that cannot
be bought. Sold-out combinations (Ink / S) stay selectable so the price and the
"Out of stock" state are visible.

Stock is *sellable* stock. Adding to the cart reserves units immediately, so the
number the page shows already excludes what is sitting in carts.

---

## 4. API contract

### Conventions

| Item | Rule |
| --- | --- |
| Base URL | `http://127.0.0.1:8000` |
| Content type | `application/json; charset=utf-8` |
| Money | Integer minor units (`price_cents`, `subtotal_cents`), never floats |
| IDs | ASCII tokens, e.g. `sku_aurora_sand_m` |
| Correlation | Every response carries `X-Request-Id`; error bodies repeat it as `request_id` |
| Errors | `{"error": {"code", "message", "details"}, "request_id"}` |
| Cart | One server-side demo cart, `cart_demo` (there is no authentication) |

### `GET /api/products/{product_id}`

Returns the product, its option dimensions and every purchasable SKU.

**200 OK**

```json
{
  "product": {
    "id": "prod_aurora_field_jacket",
    "name": "Aurora Field Jacket",
    "description": "A weatherproof shell for shoulder-season days. Fully seam-sealed, with a two-way zip, a packable hood and four utility pockets.",
    "currency": "USD",
    "image_url": "/images/aurora-field-jacket.svg",
    "price_min_cents": 12900,
    "price_max_cents": 13900
  },
  "options": [
    {
      "id": "colour",
      "name": "Colour",
      "values": [
        { "id": "colour_sand", "label": "Sand", "swatch": "#c9b79a" },
        { "id": "colour_olive", "label": "Olive", "swatch": "#6b7a54" },
        { "id": "colour_ink", "label": "Ink", "swatch": "#2b2f3a" }
      ]
    },
    {
      "id": "size",
      "name": "Size",
      "values": [
        { "id": "size_s", "label": "S", "swatch": null },
        { "id": "size_m", "label": "M", "swatch": null },
        { "id": "size_l", "label": "L", "swatch": null }
      ]
    }
  ],
  "skus": [
    {
      "id": "sku_aurora_ink_s",
      "code": "AUR-INK-S",
      "price_cents": 13900,
      "stock": 0,
      "stock_status": "out_of_stock",
      "purchasable": false,
      "image_url": "/images/aurora-ink.svg",
      "options": { "colour": "colour_ink", "size": "size_s" }
    }
  ]
}
```

(`skus` is trimmed above for readability; the real response contains all seven.)

`stock_status` is `in_stock` (3+), `low_stock` (1–2) or `out_of_stock` (0).
`purchasable` is `stock > 0`. `options` maps *dimension id → option-value id*, so
the client can match a selection to a SKU without parsing labels.

**404 Not Found**

```json
{
  "error": {
    "code": "product_not_found",
    "message": "Product 'does-not-exist' does not exist.",
    "details": { "product_id": "does-not-exist" }
  },
  "request_id": "req_0f1b2c3d4e5f6a7b"
}
```

### `POST /api/cart/items`

Adds a SKU to the cart and reserves stock. **Requires `Idempotency-Key`.**

**Request**

```http
POST /api/cart/items
Content-Type: application/json
Idempotency-Key: demo-66852c9d

{"sku_id": "sku_aurora_sand_m", "quantity": 2}
```

| Field | Type | Rules |
| --- | --- | --- |
| `sku_id` | string | Must exist and be active; `1–64` chars of `[A-Za-z0-9_-]` |
| `quantity` | integer | `>= 1`; the selected SKU's current stock is checked atomically on the server |
| `Idempotency-Key` header | string | Required, `1–128` printable ASCII characters |

Unknown fields are rejected (`extra="forbid"`), which is what makes
`{"price_cents": 1}` a validation error rather than a price override.

**201 Created**

```json
{
  "cart": {
    "id": "cart_demo",
    "currency": "USD",
    "items": [
      {
        "sku_id": "sku_aurora_sand_m",
        "quantity": 2,
        "unit_price_cents": 12900,
        "line_total_cents": 25800,
        "sku": {
          "id": "sku_aurora_sand_m",
          "code": "AUR-SAND-M",
          "price_cents": 12900,
          "stock": 4,
          "stock_status": "in_stock",
          "image_url": "/images/aurora-sand.svg",
          "options": { "colour": "colour_sand", "size": "size_m" },
          "option_labels": { "Colour": "Sand", "Size": "M" }
        }
      }
    ],
    "item_count": 1,
    "total_quantity": 2,
    "subtotal_cents": 25800
  },
  "item": {
    "sku_id": "sku_aurora_sand_m",
    "quantity": 2,
    "unit_price_cents": 12900,
    "line_total_cents": 25800,
    "sku": { "...": "same shape as above" }
  },
  "replayed": false
}
```

The response header `Idempotent-Replay: false` accompanies the first write;
`true` marks a replayed response.

**Response status codes**

| Status | When | `code` |
| --- | --- | --- |
| `201` | Added (or idempotent replay of the add) | – |
| `400` | `Idempotency-Key` missing, empty, too long or non-ASCII | `idempotency_key_missing`, `idempotency_key_invalid` |
| `404` | Unknown or inactive SKU | `sku_not_found` |
| `409` | Not enough stock, or the key was reused for a different body | `insufficient_stock`, `idempotency_key_conflict` |
| `422` | Body failed validation (quantity, unknown fields, bad JSON) | `request_validation_error` |
| `500` | Unexpected failure | `internal_error` |

**409 insufficient stock**

```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "There is not enough stock left for this SKU.",
    "details": { "sku_id": "sku_aurora_ink_s", "requested": 1, "available": 0 }
  },
  "request_id": "req_e8c5a391ce787a10"
}
```

**409 idempotency conflict**

```json
{
  "error": {
    "code": "idempotency_key_conflict",
    "message": "This Idempotency-Key was already used for a different request.",
    "details": { "idempotency_key": "demo-conflict-eb315f" }
  },
  "request_id": "req_47861de6e7ead637"
}
```

**400 missing key**

```json
{
  "error": {
    "code": "idempotency_key_missing",
    "message": "The Idempotency-Key header is required for this endpoint.",
    "details": { "header": "Idempotency-Key" }
  },
  "request_id": "req_18d5916a1d241a2f"
}
```

**422 validation**

```json
{
  "error": {
    "code": "request_validation_error",
    "message": "The request body or query parameters are invalid.",
    "details": {
      "errors": [
        { "location": ["body", "quantity"], "message": "Input should be greater than or equal to 1", "type": "greater_than_equal" }
      ]
    }
  },
  "request_id": "req_1c414380e62b5317"
}
```

### `GET /api/cart`

**200 OK**

```json
{
  "id": "cart_demo",
  "currency": "USD",
  "items": [
    {
      "sku_id": "sku_aurora_sand_m",
      "quantity": 3,
      "unit_price_cents": 12900,
      "line_total_cents": 38700,
      "sku": {
        "id": "sku_aurora_sand_m",
        "code": "AUR-SAND-M",
        "price_cents": 12900,
        "stock": 3,
        "stock_status": "in_stock",
        "image_url": "/images/aurora-sand.svg",
        "options": { "colour": "colour_sand", "size": "size_m" },
        "option_labels": { "Colour": "Sand", "Size": "M" }
      }
    }
  ],
  "item_count": 1,
  "total_quantity": 3,
  "subtotal_cents": 38700
}
```

`item_count` is the number of lines; `total_quantity` is the sum of quantities.
`unit_price_cents` is the price captured when the line was created, so a later
catalogue price change cannot silently re-price a bag.

### `GET /api/health`

```json
{ "status": "ok" }
```

### Error codes

| `code` | Status | Meaning |
| --- | --- | --- |
| `product_not_found` | 404 | Product id does not exist |
| `sku_not_found` | 404 | SKU does not exist or is inactive |
| `insufficient_stock` | 409 | Requested quantity exceeds available stock |
| `idempotency_key_missing` | 400 | Header absent or empty |
| `idempotency_key_invalid` | 400 | Header longer than 128 chars or not printable ASCII |
| `idempotency_key_conflict` | 409 | Key reused with a different request body |
| `request_validation_error` | 422 | Pydantic validation failed |
| `not_found` | 404 | Unknown route |
| `method_not_allowed` | 405 | Wrong HTTP method |
| `internal_error` | 500 | Unhandled exception; details are never leaked |

---

## 5. Guards behind the contract

### Price and stock are server-authoritative

`POST /api/cart/items` accepts only `sku_id` and `quantity`. Price and stock are
read from `skus` inside the same transaction that reserves stock, and the cart
line stores the price the server saw. A client cannot send a price, and
`extra="forbid"` rejects the attempt explicitly instead of ignoring it.

### Preventing oversell

Every add runs in a single `BEGIN IMMEDIATE` transaction:

```sql
BEGIN IMMEDIATE;

-- 1. claim the idempotency key or return the cached response
SELECT request_fingerprint, response_status, response_body
FROM idempotency_keys WHERE key = ?;

-- 2. reserve stock atomically: rowcount 0 means "not enough"
UPDATE skus
   SET stock = stock - :quantity
 WHERE id = :sku_id AND active = 1 AND stock >= :quantity;

-- 3. upsert the cart line
INSERT INTO cart_items (...) VALUES (...)
ON CONFLICT (cart_id, sku_id)
DO UPDATE SET quantity = cart_items.quantity + excluded.quantity;

-- 4. cache the response for this key
INSERT INTO idempotency_keys (...) VALUES (...);
COMMIT;
```

Why this cannot oversell:

1. `BEGIN IMMEDIATE` takes SQLite's write lock before the stock is read, so two
   writers cannot both observe `stock = 1`.
2. The decrement is conditional (`AND stock >= :quantity`). Two racing requests
   for the last unit serialise; the second sees `rowcount == 0` and gets
   `409 insufficient_stock`.
3. SQLite's `CHECK (stock >= 0)` is a second line of defence: an arithmetic bug
   fails the transaction instead of overselling.
4. WAL plus `busy_timeout = 5000` lets a contended writer wait instead of failing
   with "database is locked".

`tests/test_stock_race.py` proves it with real threads: eight buyers fire at a
one-unit SKU and exactly one gets `201`; stock ends at `0`, never negative.

Trade-offs worth naming:

- Stock is **reserved at add-to-cart**, not at checkout. This is the simplest
  model that cannot oversell, but a real shop would add a reservation TTL or a
  cart-expiry sweeper to return abandoned units.
- SQLite serialises writers. That is plenty for this scope and keeps the
  invariant provable; a multi-node deployment would move the same conditional
  `UPDATE ... WHERE stock >= ?` to Postgres and add `SELECT … FOR UPDATE` only
  where a row lock is genuinely needed.
- The demo has one cart (`cart_demo`). Per-user carts would add a cart id to the
  path or a session; the stock invariant does not change.

### Idempotency

`Idempotency-Key` is mandatory on `POST /api/cart/items`.

| Situation | Result |
| --- | --- |
| First request with a key | Normal `201`, response cached in `idempotency_keys` |
| Same key, same body | Cached response replayed, `Idempotent-Replay: true`, no second add |
| Same key, different SKU or quantity | `409 idempotency_key_conflict` |
| Request rejected (validation, stock, conflict) | **Nothing cached and the key is not consumed**, so a corrected retry may reuse it |
| Server restarted | Replay still works: the cache is in SQLite, not memory |

The fingerprint is a SHA-256 of `{operation, cart_id, sku_id, quantity}`, so the
last two rows of the table are consequences of the same rule: a key means "this
exact request", never "this endpoint".

The frontend generates a UUID per add attempt and keeps it when the outcome is
unknown (network failure or 5xx), so pressing "Retry with the same key" cannot
duplicate the line. It clears the key on success and on 4xx.

While that outcome is unknown, option and quantity controls stay locked so a
retry always sends the exact same SKU and quantity. If the server replays a
cached response, the frontend fetches the current cart before updating the
panel, because a cached response can contain an older cart snapshot.

---

## 6. Test coverage

`app/backend/tests` runs against a fresh SQLite file per test.

| File | Covers |
| --- | --- |
| `test_catalog.py` | Product shape, 2 dimensions, 7 SKUs, one sold-out SKU, one unavailable combination, price range, 404 envelope |
| `test_cart.py` | Empty cart, add + totals, stock reservation, line merging, multi-line cart, sold-out, quantity limits, price-injection attempt, unknown SKU, missing/invalid key, rejected add leaves no trace |
| `test_idempotency.py` | Replay, conflict on body change, failed request does not consume the key, replay after restart, distinct keys |
| `test_stock_race.py` | Two buyers for the last unit, eight concurrent buyers, concurrent duplicate keys, stock never negative |
| `test_errors.py` | Unexpected exception returns a sanitised structured 500, 405 envelope |

The race test uses one `TestClient` per thread, each with its own SQLite
connection, and a `Barrier` so the requests contend at the same instant.

`app/frontend` has three Vitest files with 15 tests:

| File | Covers |
| --- | --- |
| `lib/variants.test.ts` | Incomplete selection, complete SKU resolution, deterministic starting selection |
| `components/ProductDetail.test.tsx` | Incomplete UI, live price, stock-based quantity, invalid combinations, sold-out state, success feedback, validation failure, insufficient stock, server error with safe retry, and true double-click protection |
| `components/ProductShell.test.tsx` | Pending product loading state, failed initial request, in-page retry, and recovery without a full reload |

Responsive QA was completed in a real browser at `375×812` and `1280×800`.
At both widths the page has no horizontal overflow or clipping; the mobile
layout is a readable single column and the desktop layout uses the intended
gallery/details two-column arrangement. Evidence:
[375×812 screenshot](frontend/docs/responsive-375x812.png) and
[1280×800 screenshot](frontend/docs/responsive-1280x800.png).

---

## 7. Frontend behaviour

- **Server-rendered first paint**: product, price, options and stock come from
  the API during rendering; the client bundle does not fetch the catalogue just
  to show the page.
- **Option matrix**: selecting a value that makes another dimension impossible
  is prevented because a value is disabled unless a SKU exists for it with the
  current selection. Unavailable combinations are dashed and struck through;
  sold-out combinations stay selectable and show "Out of stock".
- **Incomplete selection**: no SKU is inferred until every option dimension has
  a value; the page shows a clear prompt and cannot add to the cart.
- **Live stock**: after an add the component re-reads `/api/products/{id}`, so
  "Only 1 left" becomes "Out of stock" without a page reload.
- **Quantity range**: the stepper is bounded by `1..selected SKU stock`; there is
  no unrelated fixed ten-item cap.
- **Load recovery**: if server rendering cannot fetch the product, the client
  shows a retry screen and can recover in place after FastAPI returns.
- **Feedback**: `role="status"` for confirmations and `role="alert"` for errors,
  plus a retry button when the request outcome is unknown.
- **Accessibility**: skip link, `fieldset`/`legend` for each dimension, native
  radios (keyboard and screen-reader semantics for free), 44px minimum targets,
  visible focus rings, `aria-live` quantity and status, and a
  `prefers-reduced-motion` guard.

---

## 8. Project layout

```text
app/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py        FastAPI app, routes, error handlers, request id
│   │   ├── services.py    catalogue + cart rules, stock reservation
│   │   ├── db.py          schema, connection pragmas, BEGIN IMMEDIATE helper
│   │   ├── seed.py        demo catalogue (7 SKUs, 2 dimensions)
│   │   ├── schemas.py     Pydantic request/response models
│   │   ├── errors.py      ApiError + stable error codes
│   │   └── config.py      environment-driven settings
│   ├── tests/             pytest suite (33 tests)
│   ├── pyproject.toml     ruff + pytest configuration
│   └── requirements*.txt
└── frontend/
    ├── app/               layout, page (RSC), global CSS
    ├── components/        ProductShell, ProductDetailView, CartPanel, 15 Vitest tests
    ├── docs/              responsive browser screenshots
    ├── lib/               API client, variant rules, types, money formatting
    └── public/images/     SVG product art per colour
```

---

## 9. Assumptions and limitations

- Single demo cart and no authentication: out of scope for this exercise.
- No payment/checkout step; the cart is the end of the flow.
- Stock is reserved at add-to-cart and not released until the database is reset
  (no reservation expiry).
- Idempotency records are kept indefinitely in this demo; production would add a
  retention window (the response is only needed while a client might retry).
- The catalogue is seeded data; there is no admin API.
