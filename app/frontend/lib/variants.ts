import type { ProductDetail, Sku } from "./types";

export function selectionComplete(
  product: ProductDetail,
  selection: Record<string, string>,
): boolean {
  return (
    product.options.length > 0 &&
    product.options.every((dimension) => Boolean(selection[dimension.id]))
  );
}

export function findSelectedSku(
  product: ProductDetail,
  selection: Record<string, string>,
): Sku | null {
  if (!selectionComplete(product, selection)) {
    return null;
  }

  return (
    product.skus.find((sku) =>
      product.options.every(
        (dimension) => sku.options[dimension.id] === selection[dimension.id],
      ),
    ) ?? null
  );
}

export function resolveInitialSelection(product: ProductDetail): Record<string, string> {
  const start =
    [...product.skus]
      .filter((sku) => sku.purchasable)
      .sort(
        (a, b) =>
          b.stock - a.stock || a.price_cents - b.price_cents || a.code.localeCompare(b.code),
      )[0] ??
    product.skus[0] ??
    null;
  return start ? { ...start.options } : {};
}
