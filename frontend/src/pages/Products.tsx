import { useEffect, useState } from "react";
import { products } from "../api/endpoints";
import { useAuth } from "../hooks/useAuth";
import type { ProductOut } from "../types";
import { money } from "../utils";

export function Products() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [list, setList] = useState<ProductOut[]>([]);
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState("");

  function load() {
    products.list().then(setList).catch(() => undefined);
  }

  useEffect(load, []);

  async function create() {
    if (!name.trim() || !price || !stock) return;
    await products.create(name.trim(), Math.round(Number(price) * 100), Number(stock));
    setName("");
    setPrice("");
    setStock("");
    load();
  }

  return (
    <div className="products-page">
      <header className="page-header">
        <h2>Products</h2>
        <p className="tenue">A small catalog, so a quote can reference real stock and price.</p>
      </header>

      {isAdmin && (
        <section className="support-form product-form">
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Price" type="number" value={price} onChange={(e) => setPrice(e.target.value)} />
          <input placeholder="Stock" type="number" value={stock} onChange={(e) => setStock(e.target.value)} />
          <button onClick={create}>Add product</button>
        </section>
      )}

      <table className="lines-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Price</th>
            <th>Stock</th>
          </tr>
        </thead>
        <tbody>
          {list.map((p) => (
            <tr key={p.id}>
              <td>{p.name}</td>
              <td>{money(p.price_cents)}</td>
              <td>
                {p.stock === 0 ? <span className="tag cold">out of stock</span> : p.stock}
              </td>
            </tr>
          ))}
          {list.length === 0 && (
            <tr>
              <td colSpan={3} className="tenue">
                No products yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
