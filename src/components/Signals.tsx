import { useEffect, useState } from "react";
import type { SignalFile } from "../types/signal";

export default function Signals() {
  const [data, setData] = useState<SignalFile | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/signal.json", { cache: "no-store" })
      .then(r => r.json())
      .then(setData)
      .catch(e => setErr(String(e)));
  }, []);

  if (err) return <div className="p-4 rounded-xl bg-red-100">Erreur: {err}</div>;
  if (!data) return <div className="p-4">Chargement…</div>;

  return (
    <div className="p-6 space-y-4">
      <div className={`p-3 rounded-xl ${data.status === 'ok' ? 'bg-green-100' : 'bg-yellow-100'}`}>
        Dernière génération: <b>{new Date(data.generatedAt).toLocaleString()}</b> — statut: <b>{data.status}</b>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th>Symbole</th><th>Signal</th><th>Confiance</th><th>Prix</th><th>Raison</th>
          </tr>
        </thead>
        <tbody>
          {data.entries.sort((a,b) => (a.signal==='BUY'? -1:1) - (b.signal==='BUY'? -1:1)).map(e => (
            <tr key={e.id} className="border-t">
              <td className="py-2 font-medium">{e.symbol}</td>
              <td>{e.signal}</td>
              <td>{Math.round(e.confidence*100)}%</td>
              <td>{e.price?.toLocaleString(undefined,{maximumFractionDigits:6})}</td>
              <td title={e.reason}>{e.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
