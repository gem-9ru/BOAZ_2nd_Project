import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 서버(FastAPI)가 /analysis 아래로 띄운다. 개발 중에는 서버 주소를 8000으로 넘긴다.
export default defineConfig({
  base: "/analysis/",
  plugins: [react(), tailwindcss()],
  server: { proxy: { "^/(analysis/example|simulate|plan)": "http://localhost:8000" } },
  test: { environment: "jsdom", setupFiles: ["tests/setup.ts"] },
});
