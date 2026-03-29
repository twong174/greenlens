import { useState, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import SearchIcon from "@mui/icons-material/Search";
import SpaIcon from "@mui/icons-material/Spa";
import gsap from "gsap";
import topoBg from "../../assets/matthew-jackson-BWlzubEi1DU-unsplash.jpg";

const CATCHPHRASE =
  "Don't take their word for it — search any company to verify their environmental claims";

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
    <div className="h-screen w-full grid grid-rows-[auto_1fr] relative bg-[#253D2C]">
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: `url(${topoBg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          opacity: 0.08,
          filter: "grayscale(100%)",
        }}
      />
      {/* HEADER */}
      <header className="p-4 relative z-10 text-white">
        <Link to="/" className="flex items-center gap-0.5 w-fit">
          <SpaIcon fontSize="small" className="" />
          <h1 className="font-semibold text-xl">GreenLens</h1>
        </Link>
      </header>
      <div className="flex flex-col items-center justify-center gap-20 relative z-10">
        <h1 className="px-12 lg:px-70 lg:text-7xl text-6xl font-medium text-center text-white">
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
        <div className="flex flex-col items-center gap-3">
          <p className="text-sm lg:text-lg font-light text-white text-center mb-2">
            We cross-reference corporate pledges with real satellite data from Global Forest Watch
          </p>
          <div className="flex items-center gap-1">
            <div className="border border-white/30 rounded-md flex items-center gap-1 px-3 py-2 bg-white/10">
              <SearchIcon fontSize="small" className="text-white/50" />
              <input
                type="text"
                placeholder="Enter Company Name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="focus:outline-none text-base px-1 w-96 placeholder-white/40 text-white bg-transparent"
              />
            </div>

            {/* SEARCH BUTTON */}
            <button
              type="submit"
              onClick={handleSearch}
              className="text-[#253D2C] bg-white rounded-sm font-medium px-4 py-2 cursor-pointer text-base"
            >
              Search
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
