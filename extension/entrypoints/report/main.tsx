import React from "react";
import ReactDOM from "react-dom/client";
import { loadState } from "../../lib/storage";
import App from "./App";
import "../../assets/tailwind.css";

loadState().then((s) => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      {s.result ? <App result={s.result} /> : <p className="p-8">아직 분석한 결과가 없어요. 사이드 패널에서 결과 파일을 올려 주세요.</p>}
    </React.StrictMode>,
  );
});
