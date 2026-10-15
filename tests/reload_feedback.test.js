"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

async function dashboard(snapshot) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: id === "status" ? "all" : id === "sort" ? "name" : "",
      hidden: false, textContent: "", innerHTML: "", disabled: false,
      setAttribute() {}, addEventListener() {},
    });
    return elements.get(id);
  };
  const state = {next: async () => snapshot, calls: 0};
  const context = vm.createContext({
    document: {getElementById: element, querySelectorAll: () => [], documentElement: {dataset: {theme: "light"}}},
    localStorage: {getItem: () => null, setItem() {}},
    matchMedia: () => ({addEventListener() {}}), setInterval() {}, URL,
    fetch: async () => { state.calls++; return {ok: true, json: () => state.next()}; },
  });
  const source = fs.readFileSync(path.join(__dirname, "../site/app.js"), "utf8")
    .replace(/loadSnapshot\(\);\s*$/, "globalThis.initialLoad = loadSnapshot();");
  vm.runInContext(source, context);
  await context.initialLoad;
  return {element, state, context, reload: () => vm.runInContext("loadSnapshot(true)", context)};
}
const snapshot = (minutes = 0) => ({schema_version: 1, repositories: [], generated_at: new Date(Date.now() - minutes * 60000).toISOString(), refresh_minutes: 30});

test("reload confirms when the published snapshot has not changed", async () => {
  const app = await dashboard(snapshot());
  await app.reload();
  assert.match(app.element("reload-feedback").textContent, /^No newer snapshot is published/);
  assert.equal(app.element("reload-feedback").hidden, false);
  assert.equal(app.element("reload").textContent, "Reload data");
});

test("reload distinguishes a newly published snapshot", async () => {
  const app = await dashboard(snapshot(40));
  app.state.next = async () => snapshot();
  await app.reload();
  assert.match(app.element("reload-feedback").textContent, /^Loaded the published snapshot/);
  assert.equal(app.element("notice").hidden, true);
});

test("failed reload preserves the displayed snapshot and reports failure", async () => {
  const original = snapshot(40), app = await dashboard(original);
  app.state.next = async () => { throw Error("Network unavailable"); };
  await app.reload();
  assert.match(app.element("reload-feedback").textContent, /Reload failed.*Keeping/);
  assert.equal(vm.runInContext("view.snapshot.generated_at", app.context), original.generated_at);
  assert.equal(app.element("reload").disabled, false);
});

test("overdue collection is explained separately from successful snapshot downloads", async () => {
  const app = await dashboard(snapshot(180));
  await app.reload();
  assert.match(app.element("reload-feedback").textContent, /^No newer snapshot/);
  assert.equal(app.element("notice").hidden, false);
  assert.match(app.element("notice").innerHTML, /Collection is overdue/);
  assert.match(app.element("notice").innerHTML, /https:\/\/github.com\/eco-ansible-content\/eco-ansible-dashboard\/actions\/workflows\/dashboard.yml/);
  assert.match(app.element("refresh-description").textContent, /Collection scheduled every 30 minutes/);
});

test("loading prevents duplicate requests and restores the button afterward", async () => {
  const app = await dashboard(snapshot());
  let resolve;
  app.state.next = () => new Promise(done => { resolve = done; });
  const loading = app.reload();
  await Promise.resolve();
  assert.equal(app.element("reload").disabled, true);
  assert.equal(app.element("reload").textContent, "Reloading…");
  await app.reload();
  assert.equal(app.state.calls, 2);
  resolve(snapshot());
  await loading;
  assert.equal(app.element("reload").disabled, false);
  assert.equal(app.element("reload").textContent, "Reload data");
});
