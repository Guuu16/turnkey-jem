// Shapes returned by the FastAPI service. Kept in one place so the components
// and the fetch helpers cannot drift apart.

export type StockStatus = "in_stock" | "low_stock" | "out_of_stock";

export interface OptionValue {
  id: string;
  label: string;
  swatch: string | null;
}

export interface OptionDimension {
  id: string;
  name: string;
  values: OptionValue[];
}

export interface Sku {
  id: string;
  code: string;
  price_cents: number;
  stock: number;
  stock_status: StockStatus;
  purchasable: boolean;
  image_url: string;
  options: Record<string, string>;
}

export interface ProductSummary {
  id: string;
  name: string;
  description: string;
  currency: string;
  image_url: string;
  price_min_cents: number;
  price_max_cents: number;
}

export interface ProductDetail {
  product: ProductSummary;
  options: OptionDimension[];
  skus: Sku[];
}

export interface CartLineSku {
  id: string;
  code: string;
  price_cents: number;
  stock: number;
  stock_status: StockStatus;
  image_url: string;
  options: Record<string, string>;
  option_labels: Record<string, string>;
}

export interface CartItem {
  sku_id: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
  sku: CartLineSku;
}

export interface Cart {
  id: string;
  currency: string;
  items: CartItem[];
  item_count: number;
  total_quantity: number;
  subtotal_cents: number;
}

export interface AddCartItemResult {
  cart: Cart;
  item: CartItem;
  replayed: boolean;
}

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  request_id?: string;
}
