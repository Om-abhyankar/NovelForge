/*
 * NovelForge Web - a lightweight, browser-only companion to the desktop app.
 *
 * No server, no account. The working project lives in this browser's
 * IndexedDB. Export bundles it into a .zip holding a real .docx per scene
 * plus a project.json manifest (the same split the desktop app uses: .docx
 * is the prose, json is only structure) - open the zip anywhere, or Import
 * it back here later to keep going.
 */
(function () {
  "use strict";

  const DB_NAME = "novelforge-web";
  const DB_STORE = "state";
  const DB_KEY = "current";
  const AUTOSAVE_DELAY_MS = 600;

  // ------------------------------------------------------------------
  // IndexedDB - a single JSON blob under one key. Simple beats clever here.
  // ------------------------------------------------------------------

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        if (!req.result.objectStoreNames.contains(DB_STORE)) {
          req.result.createObjectStore(DB_STORE);
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function dbLoad() {
    try {
      const db = await openDb();
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(DB_STORE, "readonly");
        const req = tx.objectStore(DB_STORE).get(DB_KEY);
        req.onsuccess = () => resolve(req.result || null);
        req.onerror = () => reject(req.error);
      });
    } catch (err) {
      console.error("IndexedDB read failed", err);
      return null;
    }
  }

  async function dbSave(value) {
    try {
      const db = await openDb();
      await new Promise((resolve, reject) => {
        const tx = db.transaction(DB_STORE, "readwrite");
        tx.objectStore(DB_STORE).put(value, DB_KEY);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
      return true;
    } catch (err) {
      console.error("IndexedDB write failed", err);
      return false;
    }
  }

  // ------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------

  let project = null;     // { id, title, author, created, modified, chapters: [...] }
  let sceneTexts = {};     // { [sceneId]: string }
  let activeSceneId = "";
  let autosaveTimer = null;
  let dirty = false;

  function newId(prefix) {
    return prefix + "_" + Math.random().toString(36).slice(2, 10);
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function emptyProject(title, author) {
    return {
      id: newId("proj"),
      title: title || "Untitled Novel",
      author: author || "",
      created: nowIso(),
      modified: nowIso(),
      chapters: [],
    };
  }

  function allScenes() {
    const out = [];
    for (const chapter of project.chapters) {
      for (const scene of chapter.scenes) out.push(scene);
    }
    return out;
  }

  function findScene(sceneId) {
    for (const chapter of project.chapters) {
      const scene = chapter.scenes.find((s) => s.id === sceneId);
      if (scene) return { chapter, scene };
    }
    return null;
  }

  function wordCount(text) {
    const trimmed = (text || "").trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }

  // ------------------------------------------------------------------
  // Mutating actions
  // ------------------------------------------------------------------

  function addChapter(title) {
    project.chapters.push({
      id: newId("ch"),
      title: title || `Chapter ${project.chapters.length + 1}`,
      order: project.chapters.length,
      scenes: [],
    });
    touch();
  }

  function addScene(chapterId, title) {
    const chapter = project.chapters.find((c) => c.id === chapterId);
    if (!chapter) return;
    const scene = {
      id: newId("sc"),
      title: title || `Scene ${chapter.scenes.length + 1}`,
      order: chapter.scenes.length,
      synopsis: "",
      status: "draft",
    };
    chapter.scenes.push(scene);
    sceneTexts[scene.id] = "";
    touch();
    selectScene(scene.id);
  }

  function renameChapter(chapterId, title) {
    const chapter = project.chapters.find((c) => c.id === chapterId);
    if (chapter && title) {
      chapter.title = title;
      touch();
    }
  }

  function renameScene(sceneId, title) {
    const found = findScene(sceneId);
    if (found && title) {
      found.scene.title = title;
      touch();
    }
  }

  function deleteChapter(chapterId) {
    const chapter = project.chapters.find((c) => c.id === chapterId);
    if (!chapter) return;
    for (const scene of chapter.scenes) delete sceneTexts[scene.id];
    project.chapters = project.chapters.filter((c) => c.id !== chapterId);
    if (activeSceneId && !findScene(activeSceneId)) closeEditor();
    touch();
  }

  function deleteScene(sceneId) {
    const found = findScene(sceneId);
    if (!found) return;
    found.chapter.scenes = found.chapter.scenes.filter((s) => s.id !== sceneId);
    delete sceneTexts[sceneId];
    if (activeSceneId === sceneId) closeEditor();
    touch();
  }

  function moveChapter(chapterId, delta) {
    const idx = project.chapters.findIndex((c) => c.id === chapterId);
    const target = idx + delta;
    if (idx < 0 || target < 0 || target >= project.chapters.length) return;
    const [item] = project.chapters.splice(idx, 1);
    project.chapters.splice(target, 0, item);
    project.chapters.forEach((c, i) => (c.order = i));
    touch();
  }

  function moveScene(sceneId, delta) {
    const found = findScene(sceneId);
    if (!found) return;
    const scenes = found.chapter.scenes;
    const idx = scenes.findIndex((s) => s.id === sceneId);
    const target = idx + delta;
    if (target < 0 || target >= scenes.length) return;
    const [item] = scenes.splice(idx, 1);
    scenes.splice(target, 0, item);
    scenes.forEach((s, i) => (s.order = i));
    touch();
  }

  function touch() {
    project.modified = nowIso();
    dirty = true;
    render();
    scheduleAutosave();
  }

  function scheduleAutosave() {
    setSaveState("saving");
    if (autosaveTimer) clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(async () => {
      const ok = await dbSave({ project, sceneTexts });
      dirty = false;
      setSaveState(ok ? "saved" : "error");
    }, AUTOSAVE_DELAY_MS);
  }

  function setSaveState(state) {
    const el = document.getElementById("save-state");
    if (!el) return;
    el.classList.toggle("saving", state === "saving");
    el.textContent =
      state === "saving" ? "Saving…" :
      state === "saved" ? "Saved to this browser" :
      state === "error" ? "Could not save - export your work" : "";
  }

  // ------------------------------------------------------------------
  // Editor
  // ------------------------------------------------------------------

  function selectScene(sceneId) {
    activeSceneId = sceneId;
    const found = findScene(sceneId);
    const editor = document.getElementById("editor");
    const titleInput = document.getElementById("scene-title");
    if (!found) {
      closeEditor();
      return;
    }
    editor.disabled = false;
    titleInput.disabled = false;
    editor.value = sceneTexts[sceneId] || "";
    titleInput.value = found.scene.title;
    updateWordCount();
    renderBinder();
    editor.focus();
  }

  function closeEditor() {
    activeSceneId = "";
    const editor = document.getElementById("editor");
    const titleInput = document.getElementById("scene-title");
    editor.value = "";
    editor.disabled = true;
    titleInput.value = "";
    titleInput.disabled = true;
    updateWordCount();
    renderBinder();
  }

  function updateWordCount() {
    const text = document.getElementById("editor").value;
    document.getElementById("word-count").textContent =
      wordCount(text).toLocaleString() + " words";
  }

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------

  function render() {
    const hasProject = !!project;
    document.getElementById("welcome").hidden = hasProject;
    document.getElementById("layout").hidden = !hasProject;
    if (hasProject) renderBinder();
  }

  function renderBinder() {
    const tree = document.getElementById("binder-tree");
    tree.innerHTML = "";
    if (!project.chapters.length) {
      const empty = document.createElement("div");
      empty.className = "empty-binder";
      empty.textContent = "No chapters yet. Add one above to start.";
      tree.appendChild(empty);
      return;
    }
    for (const chapter of [...project.chapters].sort((a, b) => a.order - b.order)) {
      tree.appendChild(chapterRow(chapter));
      for (const scene of [...chapter.scenes].sort((a, b) => a.order - b.order)) {
        tree.appendChild(sceneRow(chapter, scene));
      }
      const addBtn = document.createElement("button");
      addBtn.className = "add-scene-btn";
      addBtn.textContent = "+ Scene";
      addBtn.onclick = () => addScene(chapter.id, "");
      tree.appendChild(addBtn);
    }
  }

  function chapterRow(chapter) {
    const row = document.createElement("div");
    row.className = "chapter-row";
    const label = document.createElement("span");
    label.className = "scene-title-cell";
    label.textContent = chapter.title;
    row.appendChild(label);
    row.appendChild(
      rowActions([
        ["↑", () => moveChapter(chapter.id, -1)],
        ["↓", () => moveChapter(chapter.id, 1)],
        ["✎", async () => {
          const title = await showPrompt("Rename chapter", "Chapter title", chapter.title);
          if (title) renameChapter(chapter.id, title);
        }],
        ["✕", async () => {
          if (await showConfirm("Delete chapter?",
              `"${chapter.title}" and its ${chapter.scenes.length} scene(s) will be removed from this browser. This cannot be undone here - export first if you want a copy.`)) {
            deleteChapter(chapter.id);
          }
        }],
      ])
    );
    return row;
  }

  function sceneRow(chapter, scene) {
    const row = document.createElement("div");
    row.className = "scene-row" + (scene.id === activeSceneId ? " active" : "");
    const label = document.createElement("span");
    label.className = "scene-title-cell";
    label.textContent = scene.title + `  ·  ${wordCount(sceneTexts[scene.id]).toLocaleString()}w`;
    row.appendChild(label);
    row.onclick = (e) => {
      if (e.target === row || e.target === label) selectScene(scene.id);
    };
    row.appendChild(
      rowActions([
        ["↑", () => moveScene(scene.id, -1)],
        ["↓", () => moveScene(scene.id, 1)],
        ["✕", async () => {
          if (await showConfirm("Delete scene?",
              `"${scene.title}" will be removed from this browser. This cannot be undone here - export first if you want a copy.`)) {
            deleteScene(scene.id);
          }
        }],
      ])
    );
    return row;
  }

  function rowActions(buttons) {
    const wrap = document.createElement("span");
    wrap.className = "row-actions";
    for (const [label, handler] of buttons) {
      const btn = document.createElement("button");
      btn.textContent = label;
      btn.onclick = (e) => {
        e.stopPropagation();
        handler();
      };
      wrap.appendChild(btn);
    }
    return wrap;
  }

  // ------------------------------------------------------------------
  // Minimal, hand-written .docx (real OOXML, no dependency beyond JSZip)
  // ------------------------------------------------------------------

  function escapeXml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
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
    return zip.generateAsync({ type: "arraybuffer" });
  }

  async function readDocxText(zipFileEntry) {
    const buffer = await zipFileEntry.async("arraybuffer");
    const inner = await JSZip.loadAsync(buffer);
    const docXml = inner.file("word/document.xml");
    if (!docXml) return "";
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

  function safeFilename(name) {
    return (name || "Untitled").replace(/[<>:"/\\|?*]/g, " ").trim().slice(0, 80) || "Untitled";
  }

  // ------------------------------------------------------------------
  // Export / Import
  // ------------------------------------------------------------------

  async function exportProject() {
    if (!project) return;
    const zip = new JSZip();
    const manifest = {
      id: project.id,
      title: project.title,
      author: project.author,
      created: project.created,
      modified: project.modified,
      exportedFrom: "novelforge-web",
      chapters: [],
    };

    for (const chapter of project.chapters) {
      const folder = `${String(chapter.order + 1).padStart(2, "0")} ${safeFilename(chapter.title)}`;
      const chapterEntry = { id: chapter.id, title: chapter.title, order: chapter.order, scenes: [] };
      for (const scene of chapter.scenes) {
        const filename = `${String(scene.order + 1).padStart(2, "0")} ${safeFilename(scene.title)}.docx`;
        const path = `${folder}/${filename}`;
        const bytes = await buildDocx(sceneTexts[scene.id] || "");
        zip.file(path, bytes);
        chapterEntry.scenes.push({
          id: scene.id,
          title: scene.title,
          order: scene.order,
          synopsis: scene.synopsis || "",
          status: scene.status || "draft",
          docx: path,
        });
      }
      manifest.chapters.push(chapterEntry);
    }

    zip.file("project.json", JSON.stringify(manifest, null, 2));
    const blob = await zip.generateAsync({ type: "blob" });
    downloadBlob(blob, `${safeFilename(project.title)}.novelforge.zip`);
    notify(`Exported "${project.title}" - ${allScenes().length} scene(s) as real .docx files.`, "success");
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  async function importProject(file) {
    try {
      const zip = await JSZip.loadAsync(file);
      const manifestFile = zip.file("project.json");
      if (!manifestFile) {
        notify("That doesn't look like a NovelForge export - no project.json found inside the zip.", "error");
        return;
      }
      const manifest = JSON.parse(await manifestFile.async("string"));

      if (project && await hasAnyContent()) {
        const proceed = await showConfirm(
          "Replace what's here?",
          `Importing "${manifest.title}" will replace the novel currently open in this browser. Export it first if you want to keep a copy.`,
          "Replace"
        );
        if (!proceed) return;
      }

      const newProject = {
        id: manifest.id || newId("proj"),
        title: manifest.title || "Untitled Novel",
        author: manifest.author || "",
        created: manifest.created || nowIso(),
        modified: nowIso(),
        chapters: [],
      };
      const newSceneTexts = {};

      for (const chapter of manifest.chapters || []) {
        const scenes = [];
        for (const scene of chapter.scenes || []) {
          const entry = zip.file(scene.docx);
          const text = entry ? await readDocxText(entry) : "";
          newSceneTexts[scene.id] = text;
          scenes.push({
            id: scene.id, title: scene.title, order: scene.order,
            synopsis: scene.synopsis || "", status: scene.status || "draft",
          });
        }
        newProject.chapters.push({ id: chapter.id, title: chapter.title, order: chapter.order, scenes });
      }

      project = newProject;
      sceneTexts = newSceneTexts;
      activeSceneId = "";
      await dbSave({ project, sceneTexts });
      closeEditor();
      render();
      notify(`Imported "${project.title}".`, "success");
    } catch (err) {
      console.error(err);
      notify("Could not read that file - is it a .zip exported from NovelForge Web?", "error");
    }
  }

  async function hasAnyContent() {
    if (!project) return false;
    if (project.chapters.length === 0) return false;
    return allScenes().some((s) => (sceneTexts[s.id] || "").trim().length > 0) || project.chapters.length > 0;
  }

  // ------------------------------------------------------------------
  // Tiny modal helpers (replace native prompt()/confirm() with something
  // that looks like it belongs on this page)
  // ------------------------------------------------------------------

  function showModal(builder) {
    return new Promise((resolve) => {
      const backdrop = document.getElementById("modal-backdrop");
      const modal = document.getElementById("modal");
      modal.innerHTML = "";
      const finish = (value) => {
        backdrop.hidden = true;
        resolve(value);
      };
      builder(modal, finish);
      backdrop.hidden = false;
      const firstInput = modal.querySelector("input,button.btn-primary");
      if (firstInput) firstInput.focus();
    });
  }

  function showPrompt(title, label, defaultValue) {
    return showModal((modal, finish) => {
      modal.innerHTML = `
        <h2>${escapeXml(title)}</h2>
        <input type="text" id="modal-input" placeholder="${escapeXml(label)}">
        <div class="modal-actions">
          <button class="btn" id="modal-cancel">Cancel</button>
          <button class="btn btn-primary" id="modal-ok">OK</button>
        </div>`;
      const input = modal.querySelector("#modal-input");
      input.value = defaultValue || "";
      input.select();
      const submit = () => finish(input.value.trim() || null);
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") submit();
        if (e.key === "Escape") finish(null);
      });
      modal.querySelector("#modal-ok").onclick = submit;
      modal.querySelector("#modal-cancel").onclick = () => finish(null);
    });
  }

  function showConfirm(title, message, confirmLabel) {
    return showModal((modal, finish) => {
      modal.innerHTML = `
        <h2>${escapeXml(title)}</h2>
        <p>${escapeXml(message)}</p>
        <div class="modal-actions">
          <button class="btn" id="modal-cancel">Cancel</button>
          <button class="btn btn-primary" id="modal-ok">${escapeXml(confirmLabel || "Delete")}</button>
        </div>`;
      modal.querySelector("#modal-ok").onclick = () => finish(true);
      modal.querySelector("#modal-cancel").onclick = () => finish(false);
    });
  }

  let noticeTimer = null;
  function notify(message, tone) {
    const el = document.getElementById("notice");
    el.textContent = message;
    el.className = "notice" + (tone ? " " + tone : "");
    el.hidden = false;
    if (noticeTimer) clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { el.hidden = true; }, 6000);
  }

  // ------------------------------------------------------------------
  // Wiring
  // ------------------------------------------------------------------

  async function startNewProject() {
    const title = await showPrompt("New novel", "Title", "");
    if (!title) return;
    project = emptyProject(title, "");
    sceneTexts = {};
    activeSceneId = "";
    await dbSave({ project, sceneTexts });
    render();
    notify(`Started "${title}". Add a chapter to begin.`, "success");
  }

  function wireUp() {
    document.getElementById("btn-new").onclick = async () => {
      if (project && await hasAnyContent()) {
        const proceed = await showConfirm(
          "Start a new novel?",
          "This replaces the novel currently open in this browser. Export first if you want to keep it.",
          "Start new"
        );
        if (!proceed) return;
      }
      startNewProject();
    };
    document.getElementById("btn-welcome-new").onclick = startNewProject;

    const fileInput = document.getElementById("file-import");
    const triggerImport = () => fileInput.click();
    document.getElementById("btn-import").onclick = triggerImport;
    document.getElementById("btn-welcome-import").onclick = triggerImport;
    fileInput.onchange = () => {
      if (fileInput.files[0]) importProject(fileInput.files[0]);
      fileInput.value = "";
    };

    document.getElementById("btn-export").onclick = () => {
      if (!project) {
        notify("Nothing to export yet.", "error");
        return;
      }
      exportProject();
    };

    document.getElementById("btn-add-chapter").onclick = async () => {
      const title = await showPrompt("New chapter", "Chapter title", `Chapter ${(project?.chapters.length || 0) + 1}`);
      if (title) addChapter(title);
    };

    const editor = document.getElementById("editor");
    editor.addEventListener("input", () => {
      if (!activeSceneId) return;
      sceneTexts[activeSceneId] = editor.value;
      updateWordCount();
      renderBinder();
      touch();
    });

    const titleInput = document.getElementById("scene-title");
    titleInput.addEventListener("change", () => {
      if (activeSceneId) renameScene(activeSceneId, titleInput.value.trim());
    });

    window.addEventListener("beforeunload", () => {
      if (dirty) dbSave({ project, sceneTexts });
    });
  }

  async function init() {
    wireUp();
    const saved = await dbLoad();
    if (saved && saved.project) {
      project = saved.project;
      sceneTexts = saved.sceneTexts || {};
    }
    render();
  }

  init();
})();
