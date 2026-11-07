import type { Resources } from "@/src/types";
import { kb, percent } from "@/lib/format";

// Where the RAM goes, as one bar and the same numbers in words. The bar is the shape; the rows carry
// the meaning, so colour is never the only cue. "Cached" is reclaimable: the kernel hands it back
// when a program asks, which is why "used by programs" is the figure to watch, not "free".
export function MemoryBreakdown({ r }: { r: Resources }) {
  const total = r.mem_total_kb || 1;
  const rows = [
    { key: "used", label: "Used", note: "by programs", kb: r.mem_used_kb, bar: "bg-primary" },
    { key: "cached", label: "Cached", note: "files, reclaimable", kb: r.mem_cached_kb, bar: "bg-primary-6" },
    { key: "buffers", label: "Buffers", note: "kernel I/O", kb: r.mem_buffers_kb, bar: "bg-warning" },
    { key: "free", label: "Free", note: "unused", kb: r.mem_free_kb, bar: "bg-muted" },
  ];
  const swapUsed = r.swap_total_kb - r.swap_free_kb;
  return (
    <div className="grid gap-3">
      <div aria-hidden className="flex h-3 overflow-hidden rounded-control bg-muted">
        {rows.map((x) => (
          <div key={x.key} className={x.bar} style={{ width: `${(100 * x.kb) / total}%` }} />
        ))}
      </div>
      <table className="w-full border-collapse type-body-sm">
        <caption className="sr-only">Memory by use</caption>
        <tbody>
          {rows.map((x) => (
            <tr key={x.key} className="border-t border-border">
              <th scope="row" className="py-1.5 text-left font-normal">
                <span aria-hidden className={`mr-2 inline-block size-2.5 rounded-control border border-border align-middle ${x.bar}`} />
                {x.label} <span className="text-muted-foreground">{x.note}</span>
              </th>
              <td className="py-1.5 text-right tabular-nums">{kb(x.kb)}</td>
              <td className="w-12 py-1.5 text-right tabular-nums text-muted-foreground">{percent((100 * x.kb) / total)}</td>
            </tr>
          ))}
          {r.swap_total_kb > 0 && (
            <tr className="border-t border-border">
              <th scope="row" className="py-1.5 text-left font-normal">
                Swap <span className="text-muted-foreground">on disk</span>
              </th>
              <td className="py-1.5 text-right tabular-nums">{kb(swapUsed)}</td>
              <td className="w-12 py-1.5 text-right tabular-nums text-muted-foreground">
                {percent((100 * swapUsed) / r.swap_total_kb)}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
