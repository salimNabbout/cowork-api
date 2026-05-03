import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Porta padrao 5173 (Vite default). A API Cowork ja libera
// http://localhost:5173 e http://127.0.0.1:5173 no CORS_ORIGINS default
// (ver app/core/config.py do backend). Se voce mudar a porta aqui, lembre
// de adicionar a nova URL no env CORS_ORIGINS do Render staging.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
