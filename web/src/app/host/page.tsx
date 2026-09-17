"use client";

/**
 * "/host" — BLINDED host screen (rule L6).
 *
 * The page only touches useHost(), whose return type (HostState) is the
 * blinding boundary: product name, price, stock, total elapsed time. Nothing
 * else is imported here — no desk hook, no blocks, no chart. `degraded`,
 * `sessionNotFound` và `sampleData` là trạng thái ĐƯỜNG TRUYỀN/NHÃN, không
 * phải dữ liệu thí nghiệm.
 *
 * Gói D: `/host?session=<id>` mở ĐÚNG phiên đó (ưu tiên tuyệt đối); `/host`
 * trơn thì mỗi lần poll chọn lại phiên đang live — mở màn người dẫn trước khi
 * bấm "Bắt đầu phát sóng" không còn bị khoá vào phiên khác. Tham số đọc bằng
 * `useSearchParams`, nên phần đọc nằm trong ranh giới Suspense (build
 * production của Next 14 bắt buộc).
 */

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import HostView from "@/components/HostView";
import { useHost } from "@/lib/useHost";

export default function HostPage() {
  return (
    <Suspense fallback={<HostView host={null} connection="connecting" />}>
      <HostScreen />
    </Suspense>
  );
}

function HostScreen() {
  const searchParams = useSearchParams();
  const { host, connection, degraded, sessionNotFound, sampleData } = useHost(
    searchParams.get("session"),
  );
  return (
    <HostView
      host={host}
      connection={connection}
      degraded={degraded}
      sessionNotFound={sessionNotFound}
      sampleData={sampleData}
    />
  );
}
