import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import SearchIcon from "@mui/icons-material/Search";
import SpaIcon from "@mui/icons-material/Spa";
import gsap from "gsap";

const CATCHPHRASE =
  "Don't take their word for it — Search any company to verify their environmental claims";

const LandingPage = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const wordsRef = useRef<(HTMLSpanElement | null)[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    gsap.fromTo(
      wordsRef.current,
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, duration: 0.5, stagger: 0.05, ease: "power2.out" },
    );
  }, []);

  const handleSearch = () => {
    if (!searchTerm.trim()) return;
    navigate(`/company/${encodeURIComponent(searchTerm.toLowerCase())}`);
  };

  return (
    <div className="h-screen w-full grid grid-rows-[auto_1fr]">
      {/* HEADER */}
      <header className="border-b border-0.5 border-gray-300 p-4">
        <Link to="/" className="flex items-center gap-0.5 w-fit">
          <SpaIcon fontSize="small" className="text-emerald-800" />
          <h1 className=" font-semibold text-xl text-emerald-800">GreenLens</h1>
        </Link>{" "}
      </header>
      <div className="flex flex-col items-center justify-center gap-20 ">
        <h1 className="px-12 text-6xl font-medium text-center">
          {CATCHPHRASE.split(" ").map((word, i) => (
            <span
              key={i}
              ref={(el) => {
                wordsRef.current[i] = el;
              }}
              className="inline-block mr-[0.25em] opacity-0"
            >
              {word}
            </span>
          ))}
        </h1>

        {/* SEARCH BOX */}
        <div className="flex items-center gap-1">
          <div className="border border-gray-300 rounded-md flex items-center gap-0.5 px-2">
            <SearchIcon fontSize="inherit" className="text-gray-300" />
            <input
              type="text"
              placeholder="Enter Company Name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="focus:outline-none text-sm px-1 py-0.5 w-80 placeholder-gray-400"
            />
          </div>

          {/* SEARCH BUTTON */}
          <button
            type="submit"
            onClick={handleSearch}
            className="text-white bg-emerald-800 rounded-sm font-light px-2 py-1 cursor-pointer text-sm"
          >
            Search
          </button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
