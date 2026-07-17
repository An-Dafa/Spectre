export type DetectionBox = {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

export function getPaddedBox(
  box: DetectionBox,
  width: number,
  height: number,
  paddingRatio = 0.08,
): DetectionBox | null {
  const boxWidth = Math.max(0, box.x2 - box.x1);
  const boxHeight = Math.max(0, box.y2 - box.y1);
  const x1 = Math.max(0, Math.floor(box.x1 - boxWidth * paddingRatio));
  const y1 = Math.max(0, Math.floor(box.y1 - boxHeight * paddingRatio));
  const x2 = Math.min(width, Math.ceil(box.x2 + boxWidth * paddingRatio));
  const y2 = Math.min(height, Math.ceil(box.y2 + boxHeight * paddingRatio));
  return x2 > x1 && y2 > y1 ? { x1, y1, x2, y2 } : null;
}
