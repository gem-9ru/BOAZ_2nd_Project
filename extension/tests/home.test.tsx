// 패널 제목 왼쪽 = 뭉치 집: 평소엔 앉아 있고, 광고 관리자에서 안내 중이면 자리가 빈다.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HomeSeat } from "../entrypoints/sidepanel/ui/HomeSeat";

describe("뭉치 집", () => {
  it("sits at home when nothing is being guided", () => {
    render(<HomeSeat away={false} />);
    expect(screen.getByRole("img", { name: "뭉치 (집에 있어요)" })).toBeTruthy();
  });
  it("the seat is empty while 뭉치 is guiding on Ads Manager", () => {
    render(<HomeSeat away />);
    expect(screen.queryByRole("img", { name: /집에 있어요/ })).toBeNull();
    expect(screen.getByTitle("뭉치가 광고 관리자에서 안내하고 있어요")).toBeTruthy();
  });
});
