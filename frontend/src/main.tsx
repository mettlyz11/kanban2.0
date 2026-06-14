import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import Router from "./router"
import ErrorBoundary from "./components/ErrorBoundary"
import { AuthProvider } from "./hooks/useAuth"

// SW cleanup on page load
window.addEventListener("load", function() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.getRegistrations().then(function(regs) {
      for (var i = 0; i < regs.length; i++) regs[i].unregister();
    });
  }
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
    <AuthProvider>
      <Router />
    </AuthProvider>
    </ErrorBoundary>
  </StrictMode>
)
