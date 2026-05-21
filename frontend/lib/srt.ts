export type CaptionCue = {
  start: number;
  end: number;
  text: string;
};

function parseTimestamp(ts: string): number {
  // "HH:MM:SS,mmm"
  const m = ts.trim().match(/(\d+):(\d+):(\d+)[,.](\d+)/);
  if (!m) return 0;
  const h = Number(m[1]);
  const mi = Number(m[2]);
  const s = Number(m[3]);
  const ms = Number(m[4]);
  return h * 3600 + mi * 60 + s + ms / 1000;
}

export function parseSrt(srtText: string): CaptionCue[] {
  const blocks = srtText.replace(/\r/g, "").split("\n\n");
  const cues: CaptionCue[] = [];
  for (const block of blocks) {
    const lines = block.split("\n").filter(Boolean);
    if (lines.length < 2) continue;
    const timing = lines[1].includes("-->") ? lines[1] : lines[0];
    const m = timing.match(/(.+?)\s*-->\s*(.+)/);
    if (!m) continue;
    const start = parseTimestamp(m[1]);
    const end = parseTimestamp(m[2]);
    const textLines = lines.slice(lines[1].includes("-->") ? 2 : 1);
    const text = textLines.join("\n").trim();
    if (!text) continue;
    cues.push({ start, end, text });
  }
  return cues.sort((a, b) => a.start - b.start);
}

export function findActiveCue(cues: CaptionCue[], t: number): CaptionCue | null {
  for (const c of cues) {
    if (t >= c.start && t <= c.end) return c;
  }
  return null;
}
