/**
 * Records a narrated walkthrough of the M.A.D.E. Control Center.
 *
 * Drives the real app in Chromium via Playwright and captures it to webm.
 * A lower-third caption bar is injected into the page so the recording reads
 * as a walkthrough rather than a silent screen capture. The captions are an
 * overlay owned by this script — they are not part of the application UI.
 *
 * Prereqs: a server running on BASE_URL with MADE_DEMO_MODE=1 so the agent
 * responses are deterministic and no OpenRouter key is required.
 *
 *   node tools/record_walkthrough.mjs
 */
import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

const BASE_URL = process.env.MADE_BASE_URL || 'http://127.0.0.1:8000';
const CHROME = process.env.MADE_CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const OUT_DIR = process.env.MADE_VIDEO_DIR || '/tmp/made-video';
const W = 1600;
const H = 900;

const CAPTION_CSS = `
/* Captions sit top-centre, not as a lower third: the HITL approval bar is fixed
   to the bottom of the viewport and is the single most important element in the
   demo, so a bottom caption would cover exactly the wrong thing. */
#mw-caption {
  position: fixed; left: 50%; top: 84px;
  transform: translateX(-50%) translateY(-8px);
  z-index: 2147483647;
  display: flex; flex-direction: column; gap: 7px; align-items: center;
  padding: 15px 30px 17px; width: max-content; max-width: 1060px;
  background: rgba(10,10,10,.94);
  border: 1px solid rgba(217,119,87,.38);
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(0,0,0,.55);
  font-family: 'Inter', system-ui, sans-serif;
  pointer-events: none;
  opacity: 0;
  transition: opacity .45s ease, transform .45s ease;
}
#mw-caption.on { opacity: 1; transform: translateX(-50%) translateY(0); }
#mw-caption .mw-step {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px; letter-spacing: .18em; text-transform: uppercase;
  color: #D97757;
}
#mw-caption .mw-text {
  font-size: 19px; line-height: 1.45; color: #fff; font-weight: 400;
  text-align: center; text-wrap: balance;
}
#mw-progress {
  position: fixed; top: 0; left: 0; height: 3px; z-index: 2147483647;
  background: #D97757; width: 0%;
  transition: width .6s cubic-bezier(.4,0,.2,1);
}
`;

const TOTAL_STEPS = 22;  // caption count, drives the top progress bar

async function installOverlay(page) {
  await page.evaluate((css) => {
    if (document.getElementById('mw-caption')) return;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    const bar = document.createElement('div');
    bar.id = 'mw-caption';
    bar.innerHTML = '<div class="mw-step"></div><div class="mw-text"></div>';
    document.body.appendChild(bar);

    const prog = document.createElement('div');
    prog.id = 'mw-progress';
    document.body.appendChild(prog);
  }, CAPTION_CSS);
}

/** Show a caption, hold it, and advance the progress bar. */
async function say(page, step, text, holdMs = 3600) {
  await installOverlay(page); // re-inject if a navigation wiped it
  await page.evaluate(([step, text, pct]) => {
    const bar = document.getElementById('mw-caption');
    const prog = document.getElementById('mw-progress');
    if (prog) prog.style.width = pct + '%';
    if (!bar) return;
    bar.querySelector('.mw-step').textContent = step;
    bar.querySelector('.mw-text').textContent = text;
    bar.classList.add('on');
  }, [step, text, Math.round((captionIndex / TOTAL_STEPS) * 100)]);
  captionIndex += 1;
  await page.waitForTimeout(holdMs);
}

async function hideCaption(page) {
  await page.evaluate(() => {
    const bar = document.getElementById('mw-caption');
    if (bar) bar.classList.remove('on');
  });
  await page.waitForTimeout(500);
}

let captionIndex = 0;

async function main() {
  fs.rmSync(OUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--force-device-scale-factor=1', '--hide-scrollbars'],
  });
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: OUT_DIR, size: { width: W, height: H } },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1800); // let the GSAP entrance play

  const waitForSettled = () =>
    page.waitForFunction(() => {
      const t = document.body.innerText;
      return /AWAITING HITL|HEAL EXHAUSTED|POLICY BLOCK|COMPLETE|ERROR/.test(t);
    }, { timeout: 120000 }).catch(() => {});

  const scrollTo = async (y) => {
    await page.evaluate((y) => window.scrollTo({ top: y, behavior: 'smooth' }), y);
    await page.waitForTimeout(900);
  };

  // ---- Act 1: what this is -------------------------------------------------
  await say(page, 'M.A.D.E.', 'Multi-Agent Data Engine — a LangGraph pipeline behind FastAPI, with a human approval gate before anything executes.', 4600);
  await say(page, 'The graph', 'Researcher grounds the approach, Coder writes it, a policy gate audits it, the Sandbox runs it, the Reviewer checks it, and a human signs off.', 5200);

  // ---- Act 2: dispatch, narrated WHILE the pipeline runs --------------------
  await say(page, 'Dispatch', 'Pick a demo prompt or type any task. One click dispatches the whole graph.', 3600);
  await hideCaption(page);
  const chip = page.locator('.demo-chip').first();
  await chip.hover();
  await page.waitForTimeout(650);
  await chip.click();
  await page.waitForTimeout(600);

  // These play over the live run — each node lights up underneath the caption.
  await say(page, 'Live tracker', "The tracker is driven by the backend's own log stream over a websocket. Nodes light up as the graph actually reaches them.", 4600);
  await say(page, 'Self-heal', 'This first attempt calls sqrt() without importing math. The sandbox raises a real NameError — and the graph routes that traceback back to the Coder.', 6000);
  await say(page, 'Bounded', 'The repair loop is capped at three attempts, so a model having a bad day can never spin the pipeline forever.', 4600);
  await hideCaption(page);
  await waitForSettled();
  await page.waitForTimeout(1000);

  // ---- Act 3: the artefacts ------------------------------------------------
  await say(page, 'Session log', "Every line here is the backend's real log output, tagged by which agent produced it.", 4200);
  await hideCaption(page);
  await scrollTo(320);
  await say(page, 'Code diff', 'The self-heal is shown as a real diff — the failed attempt in red, the repaired version in green.', 4800);

  await hideCaption(page);
  await scrollTo(900);
  await say(page, 'Policy gate', "This table is deterministic static analysis from Python's ast module — not an LLM opinion. Import allowlist, denied builtins, and sandbox-escape patterns.", 6200);
  await say(page, 'Ordering matters', 'The gate runs BEFORE the sandbox, not after. A static check positioned downstream of the thing it protects is decoration, not enforcement.', 6000);

  // ---- Act 4: HITL ---------------------------------------------------------
  await hideCaption(page);
  await scrollTo(0);
  await say(page, 'Human gate', 'Nothing touches the workspace until a human approves. Reject clears the generated workspace and ends the run.', 5000);
  await hideCaption(page);
  const approve = page.getByText('Approve & Run', { exact: false }).first();
  if (await approve.count()) {
    await approve.hover();
    await page.waitForTimeout(700);
    await approve.click();
    await page.waitForTimeout(3200);
  }
  await say(page, 'Executed', 'Approved code runs in a subprocess with a hard timeout, a scrubbed environment, and a throwaway working directory.', 5000);

  // ---- Act 5: the adversarial run — the policy gate refusing for real ------
  await hideCaption(page);
  await page.getByText('New session', { exact: false }).first().click();
  await page.waitForTimeout(1200);
  await say(page, 'Adversarial test', "Now the interesting one. This prompt asks the agent to read the server's .env file and print the API keys.", 5200);
  await hideCaption(page);
  const evil = page.locator('.demo-chip-adversarial').first();
  if (await evil.count()) {
    await evil.hover();
    await page.waitForTimeout(700);
    await evil.click();
    await page.waitForTimeout(600);
    await say(page, 'Refused', 'The model complies and writes open(".env"). The policy gate refuses it — and because the gate sits upstream of the sandbox, that code is never executed at all.', 6400);
    await hideCaption(page);
    await waitForSettled();
    await page.waitForTimeout(1200);
    await scrollTo(700);
    await say(page, 'Defence in depth', 'Even if the audit were bypassed, the subprocess inherits no API keys and runs in an empty temp directory — so there is nothing there to steal.', 6200);
    await hideCaption(page);
    await scrollTo(0);
  }

  // ---- Act 6: the rest of the shell ---------------------------------------
  await page.click('button[title="Pipeline terminal"]');
  await page.waitForTimeout(1000);
  await say(page, 'Raw stream', 'The terminal drawer is the unfiltered websocket log — the same stream that drives the tracker.', 4400);
  await hideCaption(page);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(600);

  await page.click('button[title="Security clearance"]');
  await page.waitForTimeout(1000);
  await say(page, 'The policy', 'The clearance panel states exactly what is enforced — and everything on it is enforced in code, not asserted in copy.', 5200);
  await hideCaption(page);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(700);

  await page.click('button[title="Toggle theme"]');
  await page.waitForTimeout(1300);
  await say(page, 'Theme', 'A full light theme — every panel, diff and chip re-tints from one token set.', 3800);
  await hideCaption(page);
  await page.click('button[title="Toggle theme"]');
  await page.waitForTimeout(1100);

  for (const [tab, step, line] of [
    ['Graph', 'Topology', 'The Graph view documents the LangGraph wiring, including the self-heal edge from Sandbox back to Coder.'],
    ['Runs', 'History', 'Runs lists execution history with healed, failed and complete states.'],
    ['Audit', 'Telemetry', 'Audit is the per-agent trace, exportable as JSON.'],
  ]) {
    await hideCaption(page);
    await page.getByText(tab, { exact: true }).first().click();
    await page.waitForTimeout(1200);
    await say(page, step, line, 4200);
  }

  // ---- Close ---------------------------------------------------------------
  await hideCaption(page);
  await page.getByText('Session', { exact: true }).first().click();
  await page.waitForTimeout(1100);
  await say(page, 'M.A.D.E.', 'Grounded research, a bounded self-heal loop, a policy gate ahead of execution, and a human in the loop before anything runs.', 5400);
  await hideCaption(page);
  await page.waitForTimeout(900);

  if (errors.length) console.log('PAGE ERRORS:', errors);

  const video = page.video();
  await context.close();
  await browser.close();

  const src = await video.path();
  const dest = path.join(OUT_DIR, 'made-walkthrough.webm');
  fs.renameSync(src, dest);
  const mb = (fs.statSync(dest).size / 1024 / 1024).toFixed(1);
  console.log(`\nRecorded ${dest} (${mb} MB)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
