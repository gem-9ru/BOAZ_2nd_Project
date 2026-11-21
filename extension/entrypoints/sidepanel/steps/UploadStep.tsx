import { useState } from "react";
import { analyze } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine } from "../ui/Coach";

/** ③ 결과 올리기: 광고 관리자에서 내보낸 CSV 하나. */
export default function UploadStep({ dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      dispatch({ type: "analyzed", result: await analyze(file) });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <Coach>광고 관리자에서 내보낸 결과 파일을 올려 주세요. 무엇이 문제였는지, 무엇을 바꿀지 알려 드릴게요.</Coach>
      <label htmlFor="result-file" className="text-[13px] text-soft">결과 파일 (CSV)</label>
      <input
        id="result-file"
        type="file"
        accept=".csv,text/csv"
        disabled={busy}
        onChange={(e) => void onFile(e.target.files?.[0])}
        className="text-[15px] file:mr-3 file:rounded-xl file:border-0 file:bg-ink file:text-cream file:px-4 file:py-2.5"
      />
      {busy && <p className="text-[13px] text-soft" role="status">결과를 읽는 중이에요…</p>}
      {error && <ErrorLine message={error} />}
      <button type="button" onClick={() => dispatch({ type: "startExport" })} className="text-left text-[13px] underline text-soft">
        결과 파일을 아직 못 받았어요 (내보내는 법 보기)
      </button>
    </section>
  );
}
