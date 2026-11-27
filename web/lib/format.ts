// Numbers and dates go through strata-react's `format` (Intl, non-breaking units, an en dash for a
// value that is not known, byte units in both bases, durations, readings with a unit, chart ticks).
// Only what is specific to this page stays here: the server's 0-100 percentages and /proc's kibibytes.
import { createFormat } from "strata-react";

export const format = createFormat("en-GB");

/** The server's percentages run 0-100 (CPU can pass 100 on several cores); `format.percent` takes a ratio. */
export const percent = (v: number) => format.percent(v / 100);

/** /proc reports kibibytes; `format.bytes` takes bytes, and RAM is counted in powers of 1024 (GiB). */
export const kb = (v: number) => format.bytes(v * 1024, { binary: true });
