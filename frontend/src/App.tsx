import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useEffect } from "react";
import Lenis from "lenis";
import LandingPage from "./components/pages/LandingPage";
import CompanyPage from "./components/pages/CompanyPage";

function App() {
  useEffect(() => {
    const lenis = new Lenis();
    const raf = (time: number) => {
      lenis.raf(time);
      requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
    return () => lenis.destroy();
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/company/:name" element={<CompanyPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
