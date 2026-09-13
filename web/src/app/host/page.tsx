"use client";

/**
 * "/host" — BLINDED host screen (rule L6).
 *
 * The page only touches useHost(), whose return type (HostState) is the
 * blinding boundary: product name, price, stock, total elapsed time. Nothing
 * else is imported here — no desk hook, no blocks, no chart. `degraded` là
 * trạng thái ĐƯỜNG TRUYỀN (mấy lần cập nhật liên tiếp hỏng), không phải dữ
 * liệu thí nghiệm.
 */

import HostView from "@/components/HostView";
import { useHost } from "@/lib/useHost";

export default function HostPage() {
  const { host, connection, degraded } = useHost();
  return <HostView host={host} connection={connection} degraded={degraded} />;
}
