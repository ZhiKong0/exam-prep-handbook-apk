const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

const root = path.resolve(__dirname, "..");
const assetsDir = path.join(root, "app", "src", "main", "assets");
const questionsPath = path.join(assetsDir, "signal_system_questions.json");
const outputDir = path.join(assetsDir, "images", "signal_system", "rendered");
const mathJaxPath = path.join(assetsDir, "mathjax", "tex-svg-full.js");
const bundledNodeModules = path.join(
  process.env.USERPROFILE || process.env.HOME || "",
  ".cache",
  "codex-runtimes",
  "codex-primary-runtime",
  "dependencies",
  "node",
  "node_modules",
);
const bundledPnpm = path.join(bundledNodeModules, ".pnpm");

function requirePackage(name) {
  try {
    return require(name);
  } catch (_) {
    const direct = path.join(bundledNodeModules, name);
    if (fs.existsSync(direct)) {
      try {
        return require(direct);
      } catch (_) {
        // pnpm packages may need their own nested node_modules for dependencies.
      }
    }
    if (fs.existsSync(bundledPnpm)) {
      const found = fs.readdirSync(bundledPnpm)
        .find((entry) => entry === name || entry.startsWith(`${name}@`));
      if (found) {
        return require(path.join(bundledPnpm, found, "node_modules", name));
      }
    }
    throw _;
  }
}

async function importMarked() {
  try {
    return await import("marked");
  } catch (_) {
    const direct = path.join(bundledNodeModules, "marked", "lib", "marked.esm.js");
    if (fs.existsSync(direct)) {
      return await import(pathToFileURL(direct).href);
    }
    const found = fs.readdirSync(bundledPnpm)
      .find((entry) => entry === "marked" || entry.startsWith("marked@"));
    return await import(pathToFileURL(path.join(bundledPnpm, found, "node_modules", "marked", "lib", "marked.esm.js")).href);
  }
}

function chromeExecutablePath() {
  const candidates = [
    path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Google", "Chrome", "Application", "chrome.exe"),
    path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Google", "Chrome", "Application", "chrome.exe"),
    path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Microsoft", "Edge", "Application", "msedge.exe"),
    path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Microsoft", "Edge", "Application", "msedge.exe"),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function slug(label) {
  const match = String(label || "").match(/Q(\d+)/i);
  if (match) return `q${match[1].padStart(2, "0")}`;
  return String(label || "question")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function assetPath(fileName) {
  return `images/signal_system/rendered/${fileName}`;
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatSlashFractions(math) {
  let out = String(math || "");
  out = out.replace(/\((\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)\)/g, "\\frac{$1}{$2}");
  out = out.replace(/(\d+(?:\.\d+)?)\/(\((?:[^()]+|\([^()]*\))*\)|\[[^\]]+\])/g, "\\frac{$1}{$2}");
  out = out.replace(/([A-Za-z]\([^()]+\))\/([A-Za-z]\([^()]+\))/g, "\\frac{$1}{$2}");
  out = out.replace(/([A-Za-z]\([^()]+\))\/(\((?:[^()]+|\([^()]*\))*\)|\[[^\]]+\])/g, "\\frac{$1}{$2}");
  out = out.replace(/(\\frac\{[^{}]+\}\{[^{}]+\})\/(\((?:[^()]+|\([^()]*\))*\)|\[[^\]]+\])/g, "\\frac{$1}{$2}");
  out = out.replace(/((?:j)?\d*\\[A-Za-z]+(?:\{[^}]+\})?)\/(\d+(?:\.\d+)?)/g, "\\frac{$1}{$2}");
  out = out.replace(/([A-Za-z])\/(\d+(?:\.\d+)?)/g, "\\frac{$1}{$2}");
  out = out.replace(/(\d+(?:\.\d+)?)\/(\\sqrt\{[^}]+\}|[A-Za-z](?:_\{?[\w]+\}?)?|\d+(?:\.\d+)?)/g, "\\frac{$1}{$2}");
  out = out.replace(/(?<![A-Za-z\\])(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)(?![\w.])/g, "\\frac{$1}{$2}");
  return out.replace(/\((\\frac\{[^{}]+\}\{[^{}]+\})\)/g, "$1");
}

function normalizeMath(match) {
  if (match.startsWith("$$") && match.endsWith("$$")) {
    return `$$${formatSlashFractions(match.slice(2, -2))}$$`;
  }
  if (match.startsWith("\\[") && match.endsWith("\\]")) {
    return `\\[${formatSlashFractions(match.slice(2, -2))}\\]`;
  }
  if (match.startsWith("\\(") && match.endsWith("\\)")) {
    return `\\(${formatSlashFractions(match.slice(2, -2))}\\)`;
  }
  if (match.startsWith("$") && match.endsWith("$")) {
    return `$${formatSlashFractions(match.slice(1, -1))}$`;
  }
  return match;
}

function protectMath(markdown) {
  const source = String(markdown == null ? "" : markdown);
  const stash = [];
  let protectedText = source;
  const patterns = [
    /\$\$[\s\S]+?\$\$/g,
    /\\\[[\s\S]+?\\\]/g,
    /\\\([\s\S]+?\\\)/g,
    /\$(?:\\.|[^$\n])+\$/g,
  ];
  for (const pattern of patterns) {
    protectedText = protectedText.replace(pattern, (match) => {
      const token = `MATH_TOKEN_${stash.length}_END`;
      stash.push(normalizeMath(match));
      return token;
    });
  }
  return { protectedText, stash };
}

function restoreMath(html, stash) {
  let out = html;
  stash.forEach((math, index) => {
    out = out.replaceAll(`MATH_TOKEN_${index}_END`, escapeHtml(math));
  });
  return out;
}

function normalizeMarkdown(text) {
  return String(text == null ? "" : text)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/`([^`\n]+)`/g, (match, inner) => {
      const value = String(inner || "").trim();
      if (/^[A-Za-z](?:_[A-Za-z0-9]+)?(?:\[[^\]]+\]|\([^)]+\))?$/.test(value)
          || /^[A-Za-z]$/.test(value)) {
        return `$${value}$`;
      }
      return match;
    })
    .replace(/[ \t]+\n/g, "\n")
    .trim();
}

function normalizeEssayMarkdown(text) {
  return normalizeMarkdown(text)
    .replace(/([^\n])（([0-9一二三四五六七八九十]+)）/g, "$1\n\n（$2）")
    .replace(/\n{3,}/g, "\n\n");
}

function stemMarkdown(q) {
  if (q && q.type === "essay") {
    return normalizeEssayMarkdown(q.stem || "");
  }
  return normalizeMarkdown(q ? q.stem || "" : "");
}

function markdownToHtml(marked, markdown) {
  const { protectedText, stash } = protectMath(normalizeMarkdown(markdown));
  const html = marked.parse(protectedText, {
    async: false,
    breaks: true,
    gfm: true,
    mangle: false,
    headerIds: false,
  });
  return restoreMath(html, stash);
}

function answerMarkdown(q) {
  const lines = [];
  if (q.type === "essay") {
    lines.push("# 参考答案", "", normalizeEssayMarkdown(q.answer));
    if (q.quickExplanation) {
      lines.push("", "## 怎么抓这题", "", normalizeEssayMarkdown(q.quickExplanation));
    }
    if (q.knowledgeDetail) {
      lines.push("", "## 知识点与推导", "", normalizeEssayMarkdown(q.knowledgeDetail));
    } else if (q.explanation) {
      lines.push("", "## 解析", "", normalizeEssayMarkdown(q.explanation));
    }
  } else {
    lines.push("# 答案与解析", "", `**正确答案：${q.answer}**`);
    if (q.quickExplanation) {
      lines.push("", "## 本题理由", "", normalizeMarkdown(q.quickExplanation));
    }
    if (q.knowledgeDetail) {
      lines.push("", "## 知识点梳理", "", normalizeMarkdown(q.knowledgeDetail));
    } else if (q.explanation) {
      lines.push("", "## 解析", "", normalizeMarkdown(q.explanation));
    }
  }
  return lines.join("\n");
}

function pageHtml(marked, markdown, kind) {
  const body = markdownToHtml(marked, markdown);
  const cssClass = kind === "answer" ? "answer" : kind === "option" ? "option" : "stem";
  const mathJaxUrl = pathToFileURL(mathJaxPath).href;
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: transparent;
      color: #20242a;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }
    #card {
      box-sizing: border-box;
      width: 900px;
      background: transparent;
      color: #20242a;
      overflow: hidden;
    }
    .stem #card {
      padding: 24px 28px;
      font-size: 26px;
      line-height: 1.56;
      font-weight: 650;
    }
    .option #card {
      padding: 12px 16px;
      font-size: 24px;
      line-height: 1.36;
      font-weight: 600;
    }
    .answer #card {
      padding: 24px 28px;
      font-size: 22px;
      line-height: 1.58;
      font-weight: 450;
    }
    h1, h2, h3, p, ul, ol, table, pre { margin-top: 0; }
    h1 {
      font-size: 29px;
      line-height: 1.35;
      margin: 0 0 16px;
      color: #2c5fd5;
      font-weight: 800;
    }
    h2 {
      font-size: 24px;
      line-height: 1.38;
      margin: 22px 0 12px;
      color: #2c5fd5;
      font-weight: 800;
    }
    h3 {
      font-size: 22px;
      line-height: 1.4;
      margin: 18px 0 10px;
      font-weight: 800;
    }
    p { margin-bottom: 12px; }
    ul, ol { padding-left: 1.45em; margin-bottom: 14px; }
    li { margin: 0 0 7px; }
    strong { font-weight: 800; color: #16202f; }
    code {
      background: #eef2f7;
      border-radius: 8px;
      padding: 1px 6px;
      font-family: Consolas, "SFMono-Regular", monospace;
      font-size: 0.92em;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 12px 0 16px;
      font-size: 19px;
      line-height: 1.45;
      table-layout: auto;
    }
    th, td {
      border: 1px solid #d8e0ec;
      padding: 8px 9px;
      vertical-align: top;
      word-break: break-word;
    }
    th {
      background: #edf4ff;
      color: #1d4fa3;
      font-weight: 800;
    }
    mjx-container[jax="SVG"] {
      max-width: 100%;
      overflow: visible;
    }
    mjx-container[display="true"] {
      display: block;
      margin: 10px 0 !important;
      padding: 4px 0;
      overflow: visible;
    }
    .option mjx-container[display="true"] {
      margin: 2px 0 !important;
    }
  </style>
  <script>
    window.MathJax = {
      tex: {
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
        processEscapes: true,
        packages: {'[+]': ['ams']}
      },
      svg: { fontCache: 'none' },
      startup: { typeset: false }
    };
  </script>
  <script src="${mathJaxUrl}"></script>
</head>
<body class="${cssClass}">
  <div id="card">${body}</div>
</body>
</html>`;
}

async function renderCard(page, marked, markdown, kind, outputPath) {
  const tempHtmlPath = path.join(outputDir, "_render_signal_system_card.html");
  await page.setViewportSize({ width: 900, height: 1200 });
  fs.writeFileSync(tempHtmlPath, pageHtml(marked, markdown, kind), "utf8");
  await page.goto(pathToFileURL(tempHtmlPath).href, { waitUntil: "load" });
  await page.evaluate(async () => {
    if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
      await window.MathJax.startup.promise;
      await window.MathJax.typesetPromise();
    }
    await document.fonts.ready;
  });
  await page.waitForTimeout(80);
  const card = page.locator("#card");
  const box = await card.boundingBox();
  if (!box) throw new Error(`Cannot locate card for ${outputPath}`);
  const height = Math.max(240, Math.ceil(box.height + 4));
  await page.setViewportSize({ width: 900, height: Math.min(22000, height + 20) });
  await card.screenshot({ path: outputPath, omitBackground: true });
}

async function main() {
  const { chromium } = requirePackage("playwright");
  const { marked } = await importMarked();
  const executablePath = chromeExecutablePath();
  if (!executablePath) throw new Error("Chrome/Edge executable was not found.");
  if (!fs.existsSync(mathJaxPath)) throw new Error(`MathJax asset missing: ${mathJaxPath}`);

  fs.mkdirSync(outputDir, { recursive: true });
  const questions = JSON.parse(fs.readFileSync(questionsPath, "utf8"));
  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: ["--allow-file-access-from-files", "--disable-web-security"],
  });
  const context = await browser.newContext({
    viewport: { width: 900, height: 1200 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  let rendered = 0;
  for (const q of questions) {
    const base = slug(q.label);
    const stemName = `${base}_stem.png`;
    q.stemImages = [assetPath(stemName)];
    await renderCard(page, marked, stemMarkdown(q), "stem", path.join(outputDir, stemName));
    rendered++;

    if (Array.isArray(q.options)) {
      for (const opt of q.options) {
        const optionName = `${base}_option_${String(opt.key || "").toLowerCase()}.png`;
        opt.image = assetPath(optionName);
        await renderCard(page, marked, opt.text || "", "option", path.join(outputDir, optionName));
        rendered++;
      }
    }

    const answerName = `${base}_answer.png`;
    q.answerImages = [assetPath(answerName)];
    await renderCard(page, marked, answerMarkdown(q), "answer", path.join(outputDir, answerName));
    rendered++;
  }

  await browser.close();
  try {
    fs.unlinkSync(path.join(outputDir, "_render_signal_system_card.html"));
  } catch (_) {
    // Temporary render file is best-effort cleanup only.
  }
  fs.writeFileSync(questionsPath, `${JSON.stringify(questions, null, 2)}\n`, "utf8");
  console.log(`Rendered ${rendered} images for ${questions.length} signal-system questions.`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
