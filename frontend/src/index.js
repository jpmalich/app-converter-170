import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import "@/styles/blueprint.css";
import App from "@/App";
import { readStoredTheme, applyTheme, watchSystemTheme } from "@/lib/themes";

// Iter 79j.46 — Theme boot. The FOUC guard in public/index.html has
// already applied the correct data-theme before first paint, but we
// re-apply here after React hydrates so any late-arriving OS scheme
// change is respected, and start the prefers-color-scheme watcher so
// "auto" flips live.
applyTheme(readStoredTheme());
watchSystemTheme(readStoredTheme);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register service worker for PWA install
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
