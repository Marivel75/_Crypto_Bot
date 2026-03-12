#!/usr/bin/env node
/**
 * Stop hook: Log session summary to projects memory
 * Triggered when a Claude Code session ends
 */

const fs = require("fs");
const path = require("path");

const MEMORY_DIR = "/home/jules/.claude/projects/-home-jules/memory";
const SESSIONS_LOG = path.join(MEMORY_DIR, "sessions.log");

function getTimestamp() {
  return new Date().toISOString().replace("T", " ").slice(0, 16);
}

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });

process.stdin.on("end", () => {
  try {
    const data = JSON.parse(input || "{}");
    const cwd = data?.cwd || process.cwd();
    const sessionId = data?.session_id || "unknown";

    // Detect vertical from cwd
    let vertical = "general";
    if (cwd.includes("crypto") || cwd.includes("cryptobot")) vertical = "crypto";
    else if (cwd.includes("mpb") || cwd.includes("monpetitbet")) vertical = "mpb";
    else if (cwd.includes("oracle") || cwd.includes("fusion")) vertical = "oracle";
    else if (cwd.includes("game") || cwd.includes("horoscope")) vertical = "content";
    else if (cwd.includes("n8n") || cwd.includes("agence")) vertical = "agency";

    const entry = `[${getTimestamp()}] session=${sessionId} vertical=${vertical} cwd=${cwd}\n`;

    fs.mkdirSync(MEMORY_DIR, { recursive: true });
    fs.appendFileSync(SESSIONS_LOG, entry);
  } catch {
    // Silently ignore
  }
  process.exit(0);
});
