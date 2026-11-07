import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import { StrataQueryProvider, ThemeProvider } from "strata-react";
import { App } from "./app";

// ThemeProvider owns the `.dark` class (system until a person chooses). The router is there for
// DataTable, which keeps its sort in the URL; the page is served at /, so no base path.
createRoot(document.getElementById("root")!).render(
  <ThemeProvider>
    <StrataQueryProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrataQueryProvider>
  </ThemeProvider>,
);
