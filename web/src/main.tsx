import { createRoot } from "react-dom/client";
import { App } from "./app";

// The theme's dark mode is a `.dark` class; follow the operating system's setting live.
const dark = window.matchMedia("(prefers-color-scheme: dark)");
const apply = () => document.documentElement.classList.toggle("dark", dark.matches);
apply();
dark.addEventListener("change", apply);

createRoot(document.getElementById("root")!).render(<App />);
