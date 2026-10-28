"use client";

import { useEffect, useState } from "react";

import { ProductDetailView } from "@/components/ProductDetail";
import { refreshProduct } from "@/lib/api";
import type { ProductDetail } from "@/lib/types";

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; product: ProductDetail }
  | { phase: "failed" };

export function ProductShell({
  productId,
  initialProduct,
}: {
  productId: string;
  initialProduct: ProductDetail | null;
}) {
  const [state, setState] = useState<LoadState>(() =>
    initialProduct ? { phase: "ready", product: initialProduct } : { phase: "loading" },
  );

  async function loadProduct() {
    setState({ phase: "loading" });
    try {
      const nextProduct = await refreshProduct(productId);
      if (!isProductDetail(nextProduct)) {
        setState({ phase: "failed" });
        return;
      }
      setState({ phase: "ready", product: nextProduct });
    } catch {
      setState({ phase: "failed" });
    }
  }

  useEffect(() => {
    if (!initialProduct) {
      void loadProduct();
    }
  }, [initialProduct, productId]);

  if (state.phase === "loading") {
    return (
      <main className="page" id="main">
        <header className="topbar">
          <a className="brand" href="#main">
            Northwind Supply
          </a>
          <span className="topbar-link topbar-link-muted" aria-hidden="true">
            <span>🛍</span> Bag
            <span className="topbar-count">0</span>
          </span>
        </header>
        <div className="pdp product-loading" role="status" aria-live="polite">
          <section className="gallery" aria-label="Loading product image">
            <div className="gallery-frame skeleton-block skeleton-gallery" />
            <span className="skeleton-line skeleton-caption" />
          </section>
          <section className="details">
            <p className="eyebrow">Loading storefront</p>
            <h1>Fetching the product...</h1>
            <span className="skeleton-line skeleton-title" />
            <span className="skeleton-line skeleton-copy" />
            <span className="skeleton-line skeleton-copy skeleton-copy-short" />
            <div className="skeleton-options" aria-hidden="true">
              <span className="skeleton-pill" />
              <span className="skeleton-pill" />
              <span className="skeleton-pill" />
            </div>
            <span className="skeleton-line skeleton-control" />
          </section>
        </div>
      </main>
    );
  }

  if (state.phase === "failed") {
    return (
      <main className="page" id="main">
        <div className="offline">
          <p className="eyebrow">Storefront offline</p>
          <h1>The product API did not answer</h1>
          <p role="alert">
            Check that the FastAPI service is running, then retry without reloading the page.
          </p>
          <button type="button" className="retry" onClick={() => void loadProduct()}>
            Retry product load
          </button>
        </div>
      </main>
    );
  }

  return <ProductDetailView initialProduct={state.product} />;
}

function isProductDetail(value: unknown): value is ProductDetail {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<ProductDetail>;
  return Boolean(
    candidate.product?.id &&
      candidate.product.name &&
      Array.isArray(candidate.options) &&
      Array.isArray(candidate.skus),
  );
}
