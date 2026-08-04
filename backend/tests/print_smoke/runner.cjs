// PRINT SMOKE RUNNER — stubs the browser surface printTakeoff touches,
// then invokes the bundled matrix in BOTH languages. Any ReferenceError
// (the _lang class) crashes node -> the pytest pin fails.
const store = {};
globalThis.localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
  removeItem: (k) => { delete store[k]; },
};
globalThis.navigator = { language: "en-US" };
globalThis.document = {
  documentElement: { lang: "en" },
  createElement: () => { throw new Error("iframe fallback reached — window.open stub failed"); },
};
globalThis.window = {
  open: () => ({
    document: {
      open() {},
      write(html) { globalThis.__printCapture += html; },
      close() {},
    },
  }),
  addEventListener() {},
  print() {},
};

const bundle = require(process.argv[2]);
for (const lang of ["en", "es"]) {
  store["ui-lang-v1"] = lang;
  const results = bundle.run(lang);
  for (const surface of results) {
    console.log(`PRINT-SMOKE-OK ${lang} ${surface}`);
  }
}
console.log("PRINT-SMOKE-DONE");
