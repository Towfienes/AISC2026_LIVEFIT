"use client";

/**
 * "/host" — BLINDED host screen (rule L6).
 *
 * The page only touches useHost(), whose return type (HostState) is the
 * blinding boundary: product name, price, stock, total elapsed time. Nothing
 * else is imported here — no desk hook, no blocks, no chart. `degraded`,
 * `sessionNotFound`, `offAir`, `concurrentLive` và `sampleData` là trạng thái
 * PHIÊN/ĐƯỜNG TRUYỀN/NHÃN, không phải dữ liệu thí nghiệm.
 *
 * Gói D + kiểm toán 17/09: `/host?session=<id>` mở ĐÚNG phiên đó (ưu tiên
 * tuyệt đối; phiên chưa/không còn live thì nói thế, không chiếu hàng ghim cũ);
 * `/host` trơn thì giữ phiên live đang chiếu, bỏ phiên mẫu khi có phiên thật,
 * và chỉ chọn lại khi phiên đang chiếu hết live (xem pickHostSession). Tham số đọc bằng
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
  const { host, connection, degraded, sessionNotFound, offAir, concurrentLive, sampleData } =
    useHost(searchParams.get("session"));
  return (
    <HostView
      host={host}
      connection={connection}
      degraded={degraded}
      sessionNotFound={sessionNotFound}
      offAir={offAir}
      concurrentLive={concurrentLive}
      sampleData={sampleData}
    />
  );
}
