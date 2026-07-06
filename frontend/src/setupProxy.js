const { createProxyMiddleware } = require("http-proxy-middleware");

// Dev-server only. Proxies API calls to the backend so the browser talks to a
// single origin (http://localhost:3100) — this keeps the backend's
// Secure;SameSite=None auth cookie first-party over plain http localhost.
//
// This file is used ONLY by `craco start` (the CRA dev server). `yarn build`
// ignores it; production serves the static build via nginx, which does the
// equivalent /api proxy (see frontend/nginx.conf).
module.exports = function (app) {
  const target = process.env.PROXY_TARGET || "http://localhost:8000";
  app.use(
    "/api",
    createProxyMiddleware({
      target,
      changeOrigin: true,
    })
  );
};
