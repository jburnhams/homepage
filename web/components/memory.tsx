import { CompositionBar, Meter } from "strata-react";
import type { Resources } from "@/src/types";
import { format, kb } from "@/lib/format";

// Where the RAM goes: strata-react's CompositionBar (a stacked bar over a table that names every
// part, so colour is never the only cue). "Cached" is reclaimable, which is why "used by programs"
// is the figure to watch, not "free". Swap is a level, not a part of the RAM, so it is a Meter.
export function Memory({ r }: { r: Resources }) {
  const swapUsed = r.swap_total_kb - r.swap_free_kb;
  return (
    <div className="grid gap-4">
      <CompositionBar
        label="Memory by use"
        parts={[
          { key: "used", label: "Used by programs", value: r.mem_used_kb },
          { key: "cached", label: "Cached (files, reclaimable)", value: r.mem_cached_kb },
          { key: "buffers", label: "Buffers (kernel I/O)", value: r.mem_buffers_kb },
        ]}
        total={r.mem_total_kb}
        restLabel="Free"
        formatValue={kb}
        partHeader="Use"
      />
      {r.swap_total_kb > 0 && (
        <Meter
          label="Swap"
          value={swapUsed}
          max={r.swap_total_kb}
          valueText={`${format.share(swapUsed / r.swap_total_kb)} used`}
          detail={`${kb(swapUsed)} of ${kb(r.swap_total_kb)} on disk`}
        />
      )}
    </div>
  );
}
