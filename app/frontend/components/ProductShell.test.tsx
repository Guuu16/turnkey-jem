import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProductShell } from "./ProductShell";

const product = {
  product: {
    id: "p1",
    name: "Jacket",
    description: "Test jacket",
    currency: "USD",
    image_url: "/jacket.svg",
    price_min_cents: 1000,
    price_max_cents: 1000,
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

describe("ProductShell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state while the initial product request is pending", async () => {
    let resolveProduct!: (response: Response) => void;
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveProduct = resolve;
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ProductShell productId="p1" initialProduct={null} />);

    expect(screen.getByText("Fetching the product...")).toBeTruthy();
    expect(screen.getByText("Loading storefront")).toBeTruthy();

    resolveProduct(
      new Response(JSON.stringify(product), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    expect(await screen.findByRole("heading", { name: "Jacket" })).toBeTruthy();
  });

  it("shows a retryable error when the product request fails, then recovers", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(product), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    const user = userEvent.setup();
    render(<ProductShell productId="p1" initialProduct={null} />);

    expect(await screen.findByText("The product API did not answer")).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Retry product load" }));

    expect(await screen.findByRole("heading", { name: "Jacket" })).toBeTruthy();
    const productRequests = fetchMock.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/products/p1"),
    );
    expect(productRequests).toHaveLength(2);
  });
});
