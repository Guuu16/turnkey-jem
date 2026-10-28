import type {
  AddCartItemResult,
  ApiErrorPayload,
  Cart,
  ProductDetail,
} from "./types";

const SERVER_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

/** A structured failure returned by the API, or a network/protocol failure. */
export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown>;
  readonly requestId: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiClientError(
      response.status,
      "invalid_response",
      "The API returned a response that was not valid JSON.",
    );
  }
}

async function handle<T>(response: Response): Promise<T> {
  if (response.ok) {
    return readJson<T>(response);
  }

  let payload: ApiErrorPayload | null = null;
  try {
    payload = (await response.json()) as ApiErrorPayload;
  } catch {
    payload = null;
  }

  if (payload?.error) {
    throw new ApiClientError(
      response.status,
      payload.error.code,
      payload.error.message,
      payload.error.details ?? {},
      payload.request_id ?? response.headers.get("X-Request-Id"),
    );
  }

  throw new ApiClientError(
    response.status,
    "request_failed",
    `The request failed with status ${response.status}.`,
    {},
    response.headers.get("X-Request-Id"),
  );
}

/** Server-side product fetch (used by the React Server Component). */
export async function fetchProduct(productId: string): Promise<ProductDetail> {
  const response = await fetch(`${SERVER_BASE_URL}/api/products/${productId}`, {
    cache: "no-store",
  });
  return handle<ProductDetail>(response);
}

/** Client-side product refresh after a stock change. Goes through the rewrite. */
export async function refreshProduct(productId: string): Promise<ProductDetail> {
  const response = await fetch(`/api/products/${productId}`, { cache: "no-store" });
  return handle<ProductDetail>(response);
}

export async function fetchCart(): Promise<Cart> {
  const response = await fetch("/api/cart", { cache: "no-store" });
  return handle<Cart>(response);
}

export async function addCartItem(input: {
  skuId: string;
  quantity: number;
  idempotencyKey: string;
}): Promise<AddCartItemResult> {
  const response = await fetch("/api/cart/items", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": input.idempotencyKey,
    },
    body: JSON.stringify({ sku_id: input.skuId, quantity: input.quantity }),
  });
  return handle<AddCartItemResult>(response);
}
