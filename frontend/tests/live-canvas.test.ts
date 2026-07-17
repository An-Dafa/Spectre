import assert from "node:assert/strict";
import test from "node:test";

import { getPaddedBox } from "../src/lib/liveCanvas.ts";

test("live detection boxes are padded and clamped to the frame", () => {
  assert.deepEqual(
    getPaddedBox({ x1: 10, y1: 20, x2: 110, y2: 120 }, 640, 480, 0.1),
    { x1: 0, y1: 10, x2: 120, y2: 130 },
  );
  assert.deepEqual(
    getPaddedBox({ x1: 600, y1: 430, x2: 650, y2: 490 }, 640, 480, 0.1),
    { x1: 595, y1: 424, x2: 640, y2: 480 },
  );
  assert.equal(getPaddedBox({ x1: 20, y1: 20, x2: 20, y2: 30 }, 640, 480), null);
});
