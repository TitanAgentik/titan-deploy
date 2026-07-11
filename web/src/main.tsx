import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { DataProvider } from "@/lib/providers";
import "./styles/global.css";
import "./styles/titan-theme.css";

function resolveTheme(): "light" | "dark" {
  const stored = localStorage.getItem("titan-theme");
  if (stored === "dark" || stored === "classic") return "dark";
  if (stored === "light" || stored === "fable") return "light";
  return "light";
}

document.documentElement.dataset.theme = resolveTheme();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <DataProvider>
      <App />
    </DataProvider>
  </StrictMode>,
);
