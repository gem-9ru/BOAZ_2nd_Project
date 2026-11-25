import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// 서버(FastAPI)가 /analysis 아래로 띄운다. 개발 중에는 서버 주소를 8000으로 넘긴다.
export default defineConfig({
  base: "/analysis/",
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "^/(analysis/example|simulate|plan|assistant|settings)": "http://localhost:8000",
      // 파일 올리기(POST /analysis)만 서버로. 같은 주소의 GET은 이 개발 서버가 페이지를 띄운다.
      "^/analysis$": { target: "http://localhost:8000", bypass: (req) => (req.method === "POST" ? undefined : req.url) },
    },
  },
  test: { environment: "jsdom", setupFiles: ["tests/setup.ts"] },
});
