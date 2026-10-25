import React, { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";

import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/newsreader/latin-400.css";
import "@fontsource/newsreader/latin-600.css";
import "@fontsource/instrument-serif/latin-400.css";
import "@fontsource/instrument-serif/latin-400-italic.css";
import "@fontsource/jetbrains-mono/latin-400.css";
import "@fontsource/jetbrains-mono/latin-500.css";
import "./styles.css";
import { App } from "./App";

const InterfaceSpecimens = lazy(()=>import("./views/InterfaceSpecimens"));
const reviewing = new URLSearchParams(location.search).get("ui-review") === "1";

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    {reviewing ? <Suspense fallback={<p>Loading interface specimens…</p>}><InterfaceSpecimens /></Suspense> : <App />}
  </React.StrictMode>,
);
