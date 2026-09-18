// Standalone Node test of the hand-written docx round-trip logic from
// app.js (copied here verbatim rather than imported, since app.js is an
// IIFE with browser-only globals). Node's built-in DOMParser (24+) is used
// for the read side, matching the browser API this targets.
const JSZip = require("./vendor/jszip.min.js");
const assert = require("assert");
const { DOMParser } = require("@xmldom/xmldom");

function escapeXml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function docxParagraphsXml(text) {
  const paragraphs = (text || "").split(/\n\s*\n/);
  return paragraphs
    .map((para) => {
      const lines = para.split("\n").map(escapeXml);
      const runs = lines
        .map((line, i) => (i === 0 ? "" : "<w:br/>") + `<w:t xml:space="preserve">${line}</w:t>`)
        .join("");
      return `<w:p><w:r>${runs}</w:r></w:p>`;
    })
    .join("");
}

async function buildDocx(text) {
  const zip = new JSZip();
  zip.file(
    "[Content_Types].xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>`
  );
  zip.file(
    "_rels/.rels",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>`
  );
  zip.file(
    "word/document.xml",
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>${docxParagraphsXml(text)}<w:sectPr/></w:body>
</w:document>`
  );
  return zip.generateAsync({ type: "nodebuffer" });
}

async function readDocxText(buffer) {
  const inner = await JSZip.loadAsync(buffer);
  const docXml = inner.file("word/document.xml");
  const xml = await docXml.async("string");
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const paragraphs = Array.from(doc.getElementsByTagName("w:p"));
  return paragraphs
    .map((p) => {
      let out = "";
      const nodes = p.getElementsByTagName("*");
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];
        if (node.localName === "t") out += node.textContent;
        else if (node.localName === "br") out += "\n";
      }
      return out;
    })
    .join("\n\n");
}

(async () => {
  const cases = [
    "Simple single paragraph.",
    "Two paragraphs.\n\nSecond one here.",
    "A paragraph\nwith a line break inside it,\nand another.",
    "Special chars: & < > \" ' and unicode: café, naïve, — em dash.",
    "",
    "Three\n\nparagraphs\n\nhere.",
  ];

  let allOk = true;
  for (const original of cases) {
    const buf = await buildDocx(original);
    const roundTripped = await readDocxText(buf);
    const ok = roundTripped === original;
    console.log(ok ? "PASS" : "FAIL", JSON.stringify(original), ok ? "" : `-> got ${JSON.stringify(roundTripped)}`);
    if (!ok) allOk = false;
  }

  // Also confirm the produced bytes look like a real, valid zip/docx: check
  // the expected internal file list is present.
  const buf = await buildDocx("Check structure.");
  const zip = await JSZip.loadAsync(buf);
  const names = Object.keys(zip.files).sort();
  console.log("docx internal files:", names);
  assert(names.includes("word/document.xml"));
  assert(names.includes("[Content_Types].xml"));
  assert(names.includes("_rels/.rels"));

  console.log(allOk ? "\nALL ROUND-TRIP TESTS PASSED" : "\nSOME TESTS FAILED");
  process.exit(allOk ? 0 : 1);
})();
