import { describe, expect, it } from "vitest";

import type { ProductDetail } from "./types";
import { findSelectedSku, resolveInitialSelection } from "./variants";

const product: ProductDetail = {
  product: {
    id: "p1",
    name: "Jacket",
    description: "Test jacket",
    currency: "USD",
    image_url: "/jacket.svg",
    price_min_cents: 1000,
    price_max_cents: 1200,
  },
  options: [
    {
      id: "colour",
      name: "Colour",
      values: [
        { id: "sand", label: "Sand", swatch: "#fff" },
        { id: "ink", label: "Ink", swatch: "#000" },
      ],
    },
    {
      id: "size",
      name: "Size",
      values: [
        { id: "s", label: "S", swatch: null },
        { id: "m", label: "M", swatch: null },
      ],
    },
  ],
  skus: [
    {
      id: "sand-s",
      code: "SAND-S",
      price_cents: 1000,
      stock: 1,
      stock_status: "low_stock",
      purchasable: true,
      image_url: "/sand.svg",
      options: { colour: "sand", size: "s" },
    },
    {
      id: "ink-s",
      code: "INK-S",
      price_cents: 1200,
      stock: 0,
      stock_status: "out_of_stock",
      purchasable: false,
      image_url: "/ink.svg",
      options: { colour: "ink", size: "s" },
    },
    {
      id: "ink-m",
      code: "INK-M",
      price_cents: 1100,
      stock: 5,
      stock_status: "in_stock",
      purchasable: true,
      image_url: "/ink.svg",
      options: { colour: "ink", size: "m" },
    },
  ],
};

describe("variant resolution", () => {
  it("returns no SKU until every option is selected", () => {
    expect(findSelectedSku(product, { colour: "sand" })).toBeNull();
    expect(findSelectedSku(product, { size: "s" })).toBeNull();
  });

  it("resolves the SKU from the complete option values", () => {
    expect(findSelectedSku(product, { colour: "ink", size: "m" })?.id).toBe("ink-m");
  });

  it("starts on the best-stocked purchasable SKU", () => {
    expect(resolveInitialSelection(product)).toEqual({ colour: "ink", size: "m" });
  });
});
