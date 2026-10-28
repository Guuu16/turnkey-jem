import { ProductShell } from "@/components/ProductShell";
import { fetchProduct } from "@/lib/api";
import type { ProductDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

const PRODUCT_ID = process.env.PRODUCT_ID ?? "prod_aurora_field_jacket";

export default async function Page() {
  let product: ProductDetail | null = null;

  try {
    product = await fetchProduct(PRODUCT_ID);
  } catch {
    product = null;
  }

  return <ProductShell productId={PRODUCT_ID} initialProduct={product} />;
}
