"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CartPanel } from "@/components/CartPanel";
import { addCartItem, ApiClientError, fetchCart, refreshProduct } from "@/lib/api";
import { formatMoney } from "@/lib/money";
import type { Cart, ProductDetail, Sku } from "@/lib/types";
import { findSelectedSku, selectionComplete } from "@/lib/variants";

type Phase = "idle" | "adding" | "added" | "error";

interface Feedback {
  tone: "success" | "error";
  text: string;
}

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function stockCopy(sku: Sku | null, complete: boolean): { tone: string; text: string } {
  if (!complete) {
    return { tone: "incomplete", text: "Choose all options" };
  }
  if (!sku) {
    return { tone: "unavailable", text: "Combination unavailable" };
  }
  if (sku.stock === 0) {
    return { tone: "out", text: "Out of stock" };
  }
  if (sku.stock_status === "low_stock") {
    return { tone: "low", text: `Only ${sku.stock} left` };
  }
  return { tone: "in", text: "In stock" };
}

function describeError(error: ApiClientError): string {
  if (error.code === "insufficient_stock") {
    const available = Number(error.details.available ?? 0);
    return available > 0
      ? `Only ${available} left in stock — reduce the quantity and try again.`
      : "That combination just sold out. Stock has been refreshed.";
  }
  if (error.code === "idempotency_key_conflict") {
    return "This request key was already used for a different add. Please try again.";
  }
  if (error.code === "sku_not_found") {
    return "This variant is no longer available.";
  }
  if (error.code === "request_validation_error") {
    return "That quantity is not valid.";
  }
  return error.message || "Something went wrong. Please try again.";
}

export function ProductDetailView({
  initialProduct,
  initialSelection,
}: {
  initialProduct: ProductDetail;
  initialSelection?: Record<string, string>;
}) {
  const [product, setProduct] = useState<ProductDetail>(initialProduct);
  const [selection, setSelection] = useState<Record<string, string>>(initialSelection ?? {});
  const [quantity, setQuantity] = useState(1);
  const [phase, setPhase] = useState<Phase>("idle");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [canRetry, setCanRetry] = useState(false);
  const [cart, setCart] = useState<Cart | null>(null);
  const [cartError, setCartError] = useState<string | null>(null);

  const pendingKey = useRef<string | null>(null);

  const currency = product.product.currency;

  const selectedSku = useMemo(() => findSelectedSku(product, selection), [product, selection]);
  const complete = selectionComplete(product, selection);

  const maxQuantity = selectedSku ? Math.max(1, selectedSku.stock) : 1;
  const controlsLocked = phase === "adding" || canRetry;

  const loadCart = useCallback(async () => {
    try {
      setCart(await fetchCart());
      setCartError(null);
    } catch {
      setCartError("The bag is unavailable right now. Is the API running?");
    }
  }, []);

  const reloadProduct = useCallback(async () => {
    try {
      const latest = await refreshProduct(initialProduct.product.id);
      setProduct(latest);
    } catch {
      // Keep the last known catalogue; the error message already explains the failure.
    }
  }, [initialProduct.product.id]);

  useEffect(() => {
    void loadCart();
  }, [loadCart]);

  useEffect(() => {
    setQuantity((current) => Math.min(Math.max(1, current), maxQuantity));
  }, [maxQuantity]);

  function combinationExists(dimensionId: string, valueId: string): boolean {
    const selectedOtherDimensions = product.options.filter(
      (dimension) => dimension.id !== dimensionId && selection[dimension.id],
    );
    return product.skus.some(
      (sku) =>
        sku.options[dimensionId] === valueId &&
        selectedOtherDimensions.every(
          (dimension) => sku.options[dimension.id] === selection[dimension.id],
        ),
    );
  }

  function selectValue(dimensionId: string, valueId: string) {
    if (controlsLocked) {
      return;
    }
    setSelection((current) => ({ ...current, [dimensionId]: valueId }));
    setQuantity(1);
    setPhase("idle");
    setFeedback(null);
    setCanRetry(false);
    pendingKey.current = null;
  }

  async function handleAddToCart() {
    if (!selectedSku || !selectedSku.purchasable || phase === "adding") {
      return;
    }

    const key = pendingKey.current ?? newIdempotencyKey();
    pendingKey.current = key;

    setPhase("adding");
    setFeedback(null);
    setCanRetry(false);

    try {
      const result = await addCartItem({
        skuId: selectedSku.id,
        quantity,
        idempotencyKey: key,
      });
      // A replayed response is the cart snapshot from the original request.
      // Fetch the current cart so later changes from another tab are not lost.
      const latestCart = result.replayed ? await fetchCart().catch(() => result.cart) : result.cart;
      setCart(latestCart);
      setCartError(null);
      setPhase("added");
      setQuantity(1);
      pendingKey.current = null;
      setFeedback({
        tone: "success",
        text: result.replayed
          ? "That add was already recorded — your bag was not changed twice."
          : `Added ${quantity} × ${selectedSku.code} to your bag.`,
      });
      await reloadProduct();
    } catch (error) {
      setPhase("error");

      if (error instanceof ApiClientError) {
        setFeedback({ tone: "error", text: describeError(error) });
        if (error.status >= 500) {
          setCanRetry(true);
        } else {
          pendingKey.current = null;
        }
        if (error.code === "insufficient_stock") {
          await reloadProduct();
        }
        return;
      }

      // Network failure: the server may or may not have committed, so keep the
      // same key and let the user retry safely.
      setCanRetry(true);
      setFeedback({
        tone: "error",
        text: "We could not reach the store. Retry is safe — the same idempotency key is reused.",
      });
    }
  }

  const stock = stockCopy(selectedSku, complete);
  const optionSummary = product.options
    .map((dimension) => {
      const valueId = selection[dimension.id];
      return dimension.values.find((value) => value.id === valueId)?.label ?? "";
    })
    .filter(Boolean)
    .join(" / ");

  const addLabel =
    phase === "adding"
      ? "Adding…"
      : !complete
        ? "Select options"
      : selectedSku?.purchasable
        ? `Add to bag · ${formatMoney(selectedSku.price_cents * quantity, currency)}`
        : "Sold out";

  return (
    <main className="page" id="main">
      <header className="topbar">
        <a className="brand" href="#main">
          Northwind Supply
        </a>
        <nav aria-label="Store">
          <a className="topbar-link" href="#bag">
            <span aria-hidden="true">🛍</span> Bag
            <span
              className="topbar-count"
              aria-label={`${cart?.total_quantity ?? 0} ${
                cart?.total_quantity === 1 ? "item" : "items"
              }`}
            >
              {cart?.total_quantity ?? 0}
            </span>
          </a>
        </nav>
      </header>

      <div className="pdp">
        <section className="gallery" aria-label="Product images">
          <div className="gallery-frame">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={selectedSku?.image_url ?? product.product.image_url}
              className="gallery-image"
              src={selectedSku?.image_url ?? product.product.image_url}
              alt={`${product.product.name} in ${optionSummary || "the selected options"}`}
              width={800}
              height={900}
            />
          </div>
          <p className="gallery-caption">
            {selectedSku
              ? selectedSku.code
              : complete
                ? "No SKU for this combination"
                : "Select options"}
            <span aria-hidden="true"> · </span>
            {stock.text}
          </p>
        </section>

        <section className="details" aria-labelledby="product-title">
          <p className="eyebrow">Field collection</p>
          <h1 id="product-title">{product.product.name}</h1>
          <p className="lede">{product.product.description}</p>

          <p className="price">
            <span>{selectedSku ? formatMoney(selectedSku.price_cents, currency) : "—"}</span>
            <span className="price-note">incl. tax</span>
          </p>

          <div className="options">
            {product.options.map((dimension) => (
              <fieldset className="option-group" key={dimension.id}>
                <legend>
                  {dimension.name}
                  <span className="legend-value">
                    {dimension.values.find((value) => value.id === selection[dimension.id])?.label ??
                      "Select"}
                  </span>
                </legend>
                <div className="option-values">
                  {dimension.values.map((value) => {
                    const available = combinationExists(dimension.id, value.id);
                    const checked = selection[dimension.id] === value.id;
                    return (
                      <label
                        key={value.id}
                        className={[
                          "option",
                          checked ? "is-selected" : "",
                          !available ? "is-unavailable" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                      >
                        <input
                          type="radio"
                          name={`dimension-${dimension.id}`}
                          value={value.id}
                          checked={checked}
                          disabled={!available || controlsLocked}
                          onChange={() => selectValue(dimension.id, value.id)}
                        />
                        {value.swatch ? (
                          <span
                            className="swatch"
                            style={{ backgroundColor: value.swatch }}
                            aria-hidden="true"
                          />
                        ) : null}
                        <span className="option-label">{value.label}</span>
                        {!available ? <span className="sr-only"> (unavailable)</span> : null}
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            ))}
          </div>

          <p className="option-help">
            Crossed-out options are combinations we do not make. Sold-out combinations stay
            selectable so you can see their price.
          </p>

          <p className={`stock stock-${stock.tone}`} id="stock-status" aria-live="polite">
            <span className="stock-dot" aria-hidden="true" />
            {stock.text}
            {selectedSku?.stock_status === "low_stock" ? (
              <span className="stock-hint"> — order soon</span>
            ) : null}
          </p>

          <div className="buy" aria-busy={phase === "adding"}>
            <div className="qty">
              <span className="qty-label" id="qty-label">
                Quantity
              </span>
              <div className="stepper" role="group" aria-labelledby="qty-label">
                <button
                  type="button"
                  className="stepper-button"
                  onClick={() => setQuantity((current) => Math.max(1, current - 1))}
                  disabled={quantity <= 1 || controlsLocked}
                  aria-label="Decrease quantity"
                >
                  −
                </button>
                <output className="stepper-value" aria-live="polite">
                  {quantity}
                </output>
                <button
                  type="button"
                  className="stepper-button"
                  onClick={() => setQuantity((current) => Math.min(maxQuantity, current + 1))}
                  disabled={quantity >= maxQuantity || controlsLocked}
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>
            </div>

            <button
              type="button"
              className="add-to-cart"
              onClick={() => void handleAddToCart()}
              disabled={!complete || !selectedSku?.purchasable || phase === "adding"}
            >
              {addLabel}
            </button>
          </div>

          <div className="feedback">
            {feedback?.tone === "error" ? (
              <p className="feedback-error" role="alert">
                {feedback.text}
              </p>
            ) : null}
            {feedback?.tone === "success" ? (
              <p className="feedback-success" role="status" aria-live="polite">
                {feedback.text}
              </p>
            ) : null}
            {canRetry ? (
              <button
                type="button"
                className="retry"
                onClick={() => void handleAddToCart()}
                disabled={phase === "adding"}
              >
                Retry with the same key
              </button>
            ) : null}
          </div>

          <dl className="facts">
            <div>
              <dt>Shell</dt>
              <dd>3-layer recycled ripstop, PFC-free finish</dd>
            </div>
            <div>
              <dt>Fit</dt>
              <dd>Regular, hip length. Size up for layering.</dd>
            </div>
            <div>
              <dt>Delivery</dt>
              <dd>Free over $120, dispatched in 1–2 working days</dd>
            </div>
          </dl>

          <CartPanel cart={cart} error={cartError} />
        </section>
      </div>
    </main>
  );
}
