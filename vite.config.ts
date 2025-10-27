// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // CoinPaprika en dev: /cp/... => https://api.coinpaprika.com/...
      "/cp": {
        target: "https://api.coinpaprika.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cp/, ""),
        headers: {
          "User-Agent": "WalletRefereeDev/1.0 (+https://github.com/)",
          "Accept": "application/json",
        },
        configure: (proxy) => {
          proxy.on("proxyReq", (req) => {
            req.setHeader("User-Agent", "WalletRefereeDev/1.0 (+https://github.com/)");
            req.setHeader("Accept", "application/json");
          });
        },
      },

      // (Optionnel) CoinGecko si tu veux garder /cg/ pendant la transition
      "/cg": {
        target: "https://api.coingecko.com",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/cg/, ""),
        headers: {
          "User-Agent": "WalletRefereeDev/1.0 (+https://github.com/)",
          "Accept": "application/json",
        },
        configure: (proxy) => {
          proxy.on("proxyReq", (req) => {
            req.setHeader("User-Agent", "WalletRefereeDev/1.0 (+https://github.com/)");
            req.setHeader("Accept", "application/json");
          });
        },
      },
    },
  },
});
