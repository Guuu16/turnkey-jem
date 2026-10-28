import { formatMoney } from "@/lib/money";
import type { Cart } from "@/lib/types";

export function CartPanel({ cart, error }: { cart: Cart | null; error: string | null }) {
  return (
    <section className="bag" id="bag" aria-labelledby="bag-heading">
      <div className="bag-header">
        <h2 id="bag-heading">Your bag</h2>
        {cart ? (
          <p className="bag-count">
            {cart.item_count} {cart.item_count === 1 ? "line" : "lines"} ·{" "}
            {cart.total_quantity} {cart.total_quantity === 1 ? "unit" : "units"}
          </p>
        ) : null}
      </div>

      {error ? (
        <p className="bag-empty" role="status">
          {error}
        </p>
      ) : null}

      {cart === null && !error ? <p className="bag-empty">Loading your bag…</p> : null}

      {cart !== null && cart.items.length === 0 ? (
        <p className="bag-empty">Your bag is empty. Pick a colour and size to start.</p>
      ) : null}

      {cart !== null && cart.items.length > 0 ? (
        <>
          <ul className="bag-lines">
            {cart.items.map((item) => (
              <li key={item.sku_id} className="bag-line">
                <img
                  className="bag-thumb"
                  src={item.sku.image_url}
                  alt={Object.values(item.sku.option_labels).join(" / ")}
                  width={56}
                  height={56}
                />
                <div className="bag-line-body">
                  <p className="bag-line-name">
                    {Object.values(item.sku.option_labels).join(" / ")}
                  </p>
                  <p className="bag-line-meta">
                    {item.quantity} × {formatMoney(item.unit_price_cents, cart.currency)}
                  </p>
                </div>
                <p className="bag-line-total">
                  {formatMoney(item.line_total_cents, cart.currency)}
                </p>
              </li>
            ))}
          </ul>

          <div className="bag-total" aria-live="polite">
            <span>Subtotal</span>
            <strong>{formatMoney(cart.subtotal_cents, cart.currency)}</strong>
          </div>
          <p className="bag-note">Stock is reserved when an item joins your bag.</p>
        </>
      ) : null}
    </section>
  );
}
