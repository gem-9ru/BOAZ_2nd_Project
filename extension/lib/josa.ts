// 받침 따라 조사 고르기: josa("페이지", "이", "가") → "가". 한글이 아니면 둘 다 ("이(가)")
export function josa(word: string, withFinal: string, withoutFinal: string): string {
  const c = (word.trim().slice(-1).charCodeAt(0) || 0) - 0xac00;
  if (c < 0 || c > 11171) return `${withFinal}(${withoutFinal})`;
  return c % 28 ? withFinal : withoutFinal;
}
