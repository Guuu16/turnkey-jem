import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductDetailView } from "./ProductDetail";
import type { ProductDetail } from "@/lib/types";

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
    { id: "colour", name: "Colour", values: [{ id: "sand", label: "Sand", swatch: "#fff" }] },
    { id: "size", name: "Size", values: [{ id: "m", label: "M", swatch: null }] },
  ],
  skus: [
    {
      id: "sand-m",
      code: "SAND-M",
      price_cents: 1000,
      stock: 3,
      stock_status: "in_stock",
      purchasable: true,
      image_url: "/sand.svg",
      options: { colour: "sand", size: "m" },
    },
  ],
};

const emptyCart = {
  id: "cart_demo",
  currency: "USD",
  items: [],
  item_count: 0,
  total_quantity: 0,
  subtotal_cents: 0,
};

const invalidCombinationProduct: ProductDetail = {
  ...product,
  options: [
    {
      id: "colour",
      name: "Colour",
      values: [{ id: "sand", label: "Sand", swatch: "#fff" }],
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
};

const outOfStockProduct: ProductDetail = {
  ...product,
  skus: [
    {
      ...product.skus[0],
      stock: 0,
      stock_status: "out_of_stock",
      purchasable: false,
    },
  ],
};

function addResult() {
  return {
    cart: { ...emptyCart, total_quantity: 1 },
    item: {
      sku_id: "sand-m",
      quantity: 1,
      unit_price_cents: 1000,
      line_total_cents: 1000,
      sku: {
        id: "sand-m",
        code: "SAND-M",
        price_cents: 1000,
        stock: 2,
        stock_status: "low_stock",
        image_url: "/sand.svg",
        options: { colour: "sand", size: "m" },
        option_labels: { Colour: "Sand", Size: "M" },
      },
    },
    replayed: false,
  };
}

describe("ProductDetailView", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/cart")) {
          return new Response(JSON.stringify(emptyCart), { status: 200 });
        }
        if (url.endsWith("/api/products/p1")) {
          return new Response(JSON.stringify(product), { status: 200 });
        }
        if (url.endsWith("/api/cart/items")) {
          return new Response(JSON.stringify(addResult()), { status: 201 });
        }
        return new Response("{}", { status: 404 });
      }),
    );
  });

  it("shows an incomplete-selection state before an SKU is resolved", () => {
    render(<ProductDetailView initialProduct={product} initialSelection={{ colour: "sand" }} />);

    expect(screen.getByText("Choose all options")).toBeTruthy();
    expect(screen.queryByText("No SKU for this combination")).toBeNull();
    expect(screen.getByRole("button", { name: "Select options" })).toBeDisabled();
  });

  it("resolves the SKU and updates the price after selecting the missing option", async () => {
    const user = userEvent.setup();
    render(<ProductDetailView initialProduct={product} initialSelection={{}} />);

    await user.click(screen.getByRole("radio", { name: "Sand" }));
    await user.click(screen.getByRole("radio", { name: "M" }));

    expect(screen.getByText("$10.00")).toBeTruthy();
    expect(screen.queryByText("Choose all options")).toBeNull();
  });

  it("allows quantity to follow stock beyond a fixed ten-item cap", async () => {
    const user = userEvent.setup();
    const largeStockProduct: ProductDetail = {
      ...product,
      skus: product.skus.map((sku) => ({ ...sku, stock: 12 })),
    };
    render(
      <ProductDetailView
        initialProduct={largeStockProduct}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    const increase = screen.getByRole("button", { name: "Increase quantity" });
    for (let index = 0; index < 10; index += 1) {
      await user.click(increase);
    }

    expect(screen.getByText("11", { selector: "output" })).toBeTruthy();
    expect(increase).toBeEnabled();
  });

  it("disables an invalid option combination before it can be selected", () => {
    render(
      <ProductDetailView
        initialProduct={invalidCombinationProduct}
        initialSelection={{ colour: "sand" }}
      />,
    );

    expect(screen.getByRole("radio", { name: /^S.*unavailable/i })).toBeDisabled();
  });

  it("shows an out-of-stock state and disables add to cart", () => {
    render(
      <ProductDetailView
        initialProduct={outOfStockProduct}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    expect(screen.getByText("Out of stock")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sold out" })).toBeDisabled();
  });

  it("announces a successful add and refreshes the selected stock", async () => {
    const user = userEvent.setup();
    render(
      <ProductDetailView
        initialProduct={product}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add to bag · $10.00" }));

    expect(await screen.findByText("Added 1 × SAND-M to your bag.")).toBeTruthy();
    expect(screen.getByText("$10.00")).toBeTruthy();
  });

  it("shows a validation error returned by the API", async () => {
    const user = userEvent.setup();
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/cart")) {
        return new Response(JSON.stringify(emptyCart), { status: 200 });
      }
      if (url.endsWith("/api/products/p1")) {
        return new Response(JSON.stringify(product), { status: 200 });
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "request_validation_error",
            message: "Validation failed.",
            details: {},
          },
          request_id: "req-validation",
        }),
        { status: 422 },
      );
    });
    render(
      <ProductDetailView
        initialProduct={product}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add to bag · $10.00" }));

    expect(await screen.findByText("That quantity is not valid.")).toBeTruthy();
  });

  it("shows an insufficient-stock error and refreshes the product", async () => {
    const user = userEvent.setup();
    let productRequests = 0;
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/cart")) {
        return new Response(JSON.stringify(emptyCart), { status: 200 });
      }
      if (url.endsWith("/api/products/p1")) {
        productRequests += 1;
        return new Response(JSON.stringify(product), { status: 200 });
      }
      return new Response(
        JSON.stringify({
          error: {
            code: "insufficient_stock",
            message: "Not enough stock.",
            details: { available: 1 },
          },
          request_id: "req-stock",
        }),
        { status: 409 },
      );
    });
    render(
      <ProductDetailView
        initialProduct={product}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add to bag · $10.00" }));

    expect(
      await screen.findByText("Only 1 left in stock — reduce the quantity and try again."),
    ).toBeTruthy();
    await waitFor(() => expect(productRequests).toBeGreaterThanOrEqual(1));
  });

  it("shows a server error with a safe same-key retry", async () => {
    const user = userEvent.setup();
    let addRequests = 0;
    const idempotencyKeys: string[] = [];
    vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/cart")) {
        return new Response(JSON.stringify(emptyCart), { status: 200 });
      }
      if (url.endsWith("/api/products/p1")) {
        return new Response(JSON.stringify(product), { status: 200 });
      }
      addRequests += 1;
      const headers = new Headers(init?.headers);
      idempotencyKeys.push(headers.get("Idempotency-Key") ?? "");
      return new Response(
        JSON.stringify({
          error: {
            code: "internal_error",
            message: "The server could not complete the request.",
            details: {},
          },
          request_id: "req-server",
        }),
        { status: 500 },
      );
    });
    render(
      <ProductDetailView
        initialProduct={product}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add to bag · $10.00" }));
    expect(
      await screen.findByText("The server could not complete the request."),
    ).toBeTruthy();
    const retry = screen.getByRole("button", { name: "Retry with the same key" });
    await user.click(retry);

    await waitFor(() => expect(addRequests).toBe(2));
    expect(idempotencyKeys).toHaveLength(2);
    expect(idempotencyKeys[0]).not.toBe("");
    expect(idempotencyKeys[1]).toBe(idempotencyKeys[0]);
  });

  it("sends only one add request during a double click", async () => {
    let resolveAdd!: (response: Response) => void;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/cart")) {
        return new Response(JSON.stringify(emptyCart), { status: 200 });
      }
      if (url.endsWith("/api/products/p1")) {
        return new Response(JSON.stringify(product), { status: 200 });
      }
      if (url.endsWith("/api/cart/items")) {
        return new Promise<Response>((resolve) => {
          resolveAdd = resolve;
        });
      }
      return new Response("{}", { status: 404 });
    });

    const user = userEvent.setup();
    render(
      <ProductDetailView
        initialProduct={product}
        initialSelection={{ colour: "sand", size: "m" }}
      />,
    );

    const addButton = screen.getByRole("button", { name: "Add to bag · $10.00" });
    await user.dblClick(addButton);
    expect(addButton).toBeDisabled();
    expect(addButton.textContent).toContain("Adding");
    const addRequests = fetchMock.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/cart/items"),
    );
    expect(addRequests).toHaveLength(1);

    resolveAdd(new Response(JSON.stringify(addResult()), { status: 201 }));
    await waitFor(() => expect(screen.getByText(/Added 1/)).toBeTruthy());
  });
});
