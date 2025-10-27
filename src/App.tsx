// src/App.tsx
import React, { useEffect, useMemo, useState } from "react";
import { Plus, Trash2, RefreshCw } from "lucide-react";

/* ------------ UI helpers ------------ */
const fmt = (v: number, cur: string) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: cur.toUpperCase() }).format(v);

function DecisionBadge({
  decision,
  percent,
}: {
  decision: "BUY" | "SELL" | "HOLD";
  percent: number;
}) {
  const map = {
    BUY: { bg: "#dcfce7", fg: "#166534", label: "Acheter" },
    SELL: { bg: "#fee2e2", fg: "#991b1b", label: "Vendre" },
    HOLD: { bg: "#e5e7eb", fg: "#374151", label: "Hold" },
  } as const;
  const s = map[decision];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 10px",
        borderRadius: 9999,
        background: s.bg,
        color: s.fg,
        fontWeight: 700,
      }}
    >
      <span aria-hidden style={{ width: 8, height: 8, background: s.fg, borderRadius: 9999 }} />
      {s.label}
      {percent ? ` (${percent}%)` : ""}
    </span>
  );
}

/* ------------ Types ------------ */
type Holding = { id: string; ticker: string; quantity: number; buyPrice: number };
type PriceInfo = { id: string; currentPrice: number; change24h: number };

type SignalsByAsset = {
  meta: { generated_at_utc: string; vs_currency: string };
  signals: {
    [id: string]:
      | {
          symbol: string;
          date: string;
          close: number;
          indicators: {
            rsi14: number | null;
            sma50: number | null;
            sma50_slope: number | null; // %
            macd: { macd: number | null; signal: number | null; hist: number | null; cross: "bull" | "bear" | "none" };
            bb_pctb: number | null;
            bb_width: number | null;
            atr_pct: number | null;
          };
          parts: Record<string, number>;
          score: number;
          decision: "BUY" | "SELL" | "HOLD";
          percent: number;
        }
      | { error: string };
  };
};

const SIGNAL_FILE = "/signals_by_asset.json";

/* ------------ Mapping tickers -> ids (fallback édition rapide) ------------ */
const DEFAULT_ID_MAP: Record<string, string> = {
  BTC: "btc-bitcoin",
  ETH: "eth-ethereum",
  SOL: "solana-solana",
  BNB: "bnb-binance-coin",
  XRP: "xrp-xrp",
  ADA: "ada-cardano",
  AVAX: "avalanche-2", // si tu utilises CoinPaprika: "avax-avalanche"
  DOGE: "doge-dogecoin",
  MATIC: "matic-polygon",
  DOT: "dot-polkadot",
};

export default function App() {
  /* --- État portefeuille / prix --- */
  const [holdings, setHoldings] = useState<Holding[]>([
    { id: "btc-bitcoin", ticker: "BTC", quantity: 0.1, buyPrice: 30000 },
    { id: "eth-ethereum", ticker: "ETH", quantity: 1, buyPrice: 1800 },
  ]);
  const [prices, setPrices] = useState<Record<string, PriceInfo>>({});
  const [currency, setCurrency] = useState<"usd" | "eur">("usd");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  /* --- Signal quotidien --- */
  const [sig, setSig] = useState<SignalsByAsset | null>(null);
  const [sigErr, setSigErr] = useState<string | null>(null);
  const [sigLoading, setSigLoading] = useState(false);

  /* --- Prix (CoinPaprika ou autre: ici CoinPaprika simple ticker) --- */
  async function fetchPrices() {
    setLoading(true);
    setError(null);
    try {
      // Simple: on appelle /tickers/{id} pour chacun (peu de tokens => OK en V1)
      const next: Record<string, PriceInfo> = {};
      for (const h of holdings) {
        const url = `https://api.coinpaprika.com/v1/tickers/${h.id}`;
        const r = await fetch(url, { headers: { Accept: "application/json" } });
        if (!r.ok) throw new Error(`HTTP ${r.status} for ${h.id}`);
        const j = await r.json();
        const q = (j as any)?.quotes?.[currency.toUpperCase()];
        const p = Number(q?.price);
        const ch = Number(q?.percent_change_24h);
        next[h.id] = {
          id: h.id,
          currentPrice: Number.isFinite(p) ? p : 0,
          change24h: Number.isFinite(ch) ? ch : 0,
        };
      }
      setPrices(next);
    } catch (e: any) {
      setError(e?.message ?? "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  /* --- Charger le fichier de signaux consolidés --- */
  async function fetchSignals() {
    setSigLoading(true);
    setSigErr(null);
    try {
      const r = await fetch(SIGNAL_FILE, { headers: { Accept: "application/json" } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const j = (await r.json()) as SignalsByAsset;
      // Vérification minimale
      if (!j || typeof j !== "object" || !j.signals) {
        throw new Error("Fichier de signaux invalide");
      }
      setSig(j);
    } catch (e: any) {
      setSigErr(e?.message ?? "Erreur signal");
    } finally {
      setSigLoading(false);
    }
  }

  /* --- Chargements initiaux --- */
  useEffect(() => {
    fetchPrices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currency, JSON.stringify(holdings)]);
  useEffect(() => {
    fetchSignals();
  }, []);

  /* --- Dérivés --- */
  const totalValue = useMemo(
    () =>
      holdings.reduce((sum, h) => {
        const p = prices[h.id]?.currentPrice ?? h.buyPrice;
        return sum + p * h.quantity;
      }, 0),
    [holdings, prices]
  );

  /* --- Actions UI --- */
  function addHolding() {
    setHoldings((h) => [...h, { id: "btc-bitcoin", ticker: "BTC", quantity: 0, buyPrice: 0 }]);
  }
  function removeHolding(idx: number) {
    setHoldings((h) => h.filter((_, i) => i !== idx));
  }
  function updateHolding(idx: number, patch: Partial<Holding>) {
    setHoldings((h) => h.map((row, i) => (i === idx ? { ...row, ...patch } : row)));
  }
  function updateTicker(idx: number, ticker: string) {
    const t = ticker.toUpperCase();
    const id = DEFAULT_ID_MAP[t] || holdings[idx].id;
    updateHolding(idx, { ticker: t, id });
  }

  // helper pour lire un signal d’un id
  function signalFor(id: string) {
    return sig?.signals?.[id] ?? null;
  }

  return (
    <div className="container" style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      {/* Header */}
      <header className="card" style={{ background: "#fff", borderRadius: 16, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,.08)" }}>
        <div className="card__title" style={{ fontWeight: 700, fontSize: 20, marginBottom: 6 }}>
          CryptoLongTerm Dashboard
        </div>
        <p style={{ color: "#6b7280", fontSize: 12, marginTop: 0 }}>
          Reco quotidienne (MACD / RSI / SMA50 / Bollinger) + suivi portefeuille (prix CoinPaprika).
        </p>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
          <select value={currency} onChange={(e) => setCurrency(e.target.value as "usd" | "eur")}>
            <option value="usd">USD</option>
            <option value="eur">EUR</option>
          </select>
          <button
            onClick={() => {
              fetchPrices();
              fetchSignals();
            }}
            disabled={loading || sigLoading}
            title="Rafraîchir"
            style={{
              padding: "8px 12px",
              borderRadius: 10,
              background: "#111827",
              color: "#fff",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <RefreshCw size={16} /> {(loading || sigLoading) ? "Chargement..." : "Rafraîchir"}
          </button>
        </div>
      </header>

      {/* Erreurs globales */}
      {error && <div className="alert alert--error" style={{ marginTop: 12, background:"#fef2f2", color:"#b91c1c", border:"1px solid #fecaca", padding:12, borderRadius:10 }}>{error}</div>}
      {sigErr && <div className="alert alert--error" style={{ marginTop: 12, background:"#fef2f2", color:"#b91c1c", border:"1px solid #fecaca", padding:12, borderRadius:10 }}>Signal: {sigErr}</div>}

      {/* Portefeuille (avec signaux par ligne) */}
      <section className="card" style={{ background: "#fff", borderRadius: 16, padding: 0, marginTop: 16, boxShadow: "0 1px 3px rgba(0,0,0,.08)" }}>
        <div style={{ padding: 16, borderBottom: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0, fontWeight: 600 }}>Portefeuille</h2>
          <button onClick={addHolding} style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 12px", background: "#f9fafb", border: "1px solid #d1d5db", borderRadius: 10 }}>
            <Plus size={16} /> Ajouter une ligne
          </button>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", fontSize: 14, borderCollapse: "separate", borderSpacing: 0 }}>
            <thead style={{ background: "#f9fafb" }}>
              <tr>
                <th style={{ textAlign: "left", padding: 12 }}>Ticker</th>
                <th style={{ textAlign: "left", padding: 12 }}>ID (CoinPaprika)</th>
                <th style={{ textAlign: "right", padding: 12 }}>Quantité</th>
                <th style={{ textAlign: "right", padding: 12 }}>Prix d'achat</th>
                <th style={{ textAlign: "right", padding: 12 }}>Prix actuel</th>
                <th style={{ textAlign: "right", padding: 12 }}>Var 24h</th>

                {/* Indicateurs & Reco */}
                <th style={{ textAlign: "right", padding: 12 }}>RSI14</th>
                <th style={{ textAlign: "right", padding: 12 }}>SMA50</th>
                <th style={{ textAlign: "right", padding: 12 }}>%B</th>
                <th style={{ textAlign: "right", padding: 12 }}>MACD hist</th>
                <th style={{ textAlign: "center", padding: 12 }}>Reco</th>

                <th style={{ textAlign: "right", padding: 12 }}>Valeur</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, idx) => {
                const p = prices[h.id];
                const lastPrice = p?.currentPrice ?? h.buyPrice;
                const value = lastPrice * h.quantity;
                const s = signalFor(h.id) as any;

                const rsi = s?.indicators?.rsi14 ?? null;
                const sma50 = s?.indicators?.sma50 ?? null;
                const pctb = s?.indicators?.bb_pctb ?? null;
                const macdh = s?.indicators?.macd?.hist ?? null;

                return (
                  <tr key={`${h.id}-${idx}`} style={{ borderTop: "1px solid #e5e7eb" }}>
                    <td style={{ padding: 12 }}>
                      <input value={h.ticker} onChange={(e) => updateTicker(idx, e.target.value)} style={{ width: 80, padding: 6 }} />
                    </td>
                    <td style={{ padding: 12 }}>
                      <input value={h.id} onChange={(e) => updateHolding(idx, { id: e.target.value })} style={{ width: 220, padding: 6 }} />
                      <div style={{ fontSize: 11, color: "#6b7280" }}>ex: btc-bitcoin, eth-ethereum (CoinPaprika)</div>
                    </td>
                    <td style={{ padding: 12, textAlign: "right" }}>
                      <input
                        type="number"
                        step="any"
                        value={h.quantity}
                        onChange={(e) => updateHolding(idx, { quantity: parseFloat(e.target.value || "0") })}
                        style={{ width: 110, padding: 6, textAlign: "right" }}
                      />
                    </td>
                    <td style={{ padding: 12, textAlign: "right" }}>
                      <input
                        type="number"
                        step="any"
                        value={h.buyPrice}
                        onChange={(e) => updateHolding(idx, { buyPrice: parseFloat(e.target.value || "0") })}
                        style={{ width: 110, padding: 6, textAlign: "right" }}
                      />
                    </td>
                    <td style={{ padding: 12, textAlign: "right", fontWeight: 600 }}>
                      {p ? fmt(p.currentPrice, currency) : "—"}
                    </td>
                    <td
                      style={{
                        padding: 12,
                        textAlign: "right",
                        color: p?.change24h != null ? (p.change24h >= 0 ? "#16a34a" : "#dc2626") : "#111827",
                      }}
                    >
                      {p?.change24h != null ? `${p.change24h.toFixed(2)}%` : "—"}
                    </td>

                    {/* Indicateurs + Reco */}
                    <td style={{ padding: 12, textAlign: "right" }}>{rsi ?? "—"}</td>
                    <td style={{ padding: 12, textAlign: "right" }}>{sma50 ? fmt(sma50, currency) : "—"}</td>
                    <td style={{ padding: 12, textAlign: "right" }}>{pctb ?? "—"}</td>
                    <td style={{ padding: 12, textAlign: "right" }}>{macdh ?? "—"}</td>
                    <td style={{ padding: 12, textAlign: "center" }}>
                      {s && !("error" in s) ? (
                        <DecisionBadge decision={s.decision} percent={s.percent} />
                      ) : (
                        <span style={{ color: "#6b7280", fontSize: 12 }}>—</span>
                      )}
                    </td>

                    <td style={{ padding: 12, textAlign: "right", fontWeight: 600 }}>
                      {fmt(value, currency)}
                    </td>
                    <td style={{ padding: 12, textAlign: "right" }}>
                      <button
                        onClick={() => removeHolding(idx)}
                        style={{ padding: 8, color: "#dc2626", display: "inline-flex", alignItems: "center", gap: 6 }}
                        title="Supprimer la ligne"
                      >
                        <Trash2 size={16} /> Supprimer
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div style={{ padding: 12, borderTop: "1px solid #e5e7eb", textAlign: "right" }}>
          <strong>Total:</strong>{" "}
          {fmt(totalValue, currency)}
        </div>
      </section>
    </div>
  );
}
