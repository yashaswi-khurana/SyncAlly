import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/inter-tight/wght.css";
import "@fontsource-variable/geist/wght.css";
import "@fontsource-variable/geist-mono/wght.css";
// the shared design system loads first so component stylesheets can refine it
import "./styles.css";
import App from "./App";
import { startGlobalFx } from "./ui/fx";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// page-wide presentation effects (scroll reveals, pointer-following fills)
startGlobalFx();
