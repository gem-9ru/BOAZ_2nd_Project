import { defineConfig } from "wxt";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  vite: () => ({ plugins: [tailwindcss()] }),
  manifest: {
    name: "광고 코치",
    description: "처음 하는 메타 광고를 찾기부터 분석까지 도와주는 코치",
    permissions: ["sidePanel", "storage", "tabs"],
    host_permissions: [
      "https://adsmanager.facebook.com/*",
      "https://business.facebook.com/*",
      "http://localhost:8000/*",
    ],
    action: { default_title: "광고 코치 열기" },
    web_accessible_resources: [
      { resources: ["guide/*"], matches: ["https://adsmanager.facebook.com/*", "https://business.facebook.com/*"] },
    ],
  },
});
