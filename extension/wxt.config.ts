import { defineConfig } from "wxt";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  vite: () => ({ plugins: [tailwindcss()] }),
  manifest: {
    name: "Ad Assistant",
    description: "처음 하는 메타 광고를 찾기부터 분석까지 도와주는 코치",
    permissions: ["sidePanel", "storage", "tabs"],
    host_permissions: [
      "https://adsmanager.facebook.com/*",
      "https://business.facebook.com/*",
    ],   // 우리 서버는 CORS로 확장을 허용해서 따로 권한이 필요 없다 (스토어 심사에 필요한 권한만)
    action: { default_title: "Ad Assistant 열기" },
    web_accessible_resources: [
      { resources: ["guide/*"], matches: ["https://adsmanager.facebook.com/*", "https://business.facebook.com/*"] },
    ],
  },
});
