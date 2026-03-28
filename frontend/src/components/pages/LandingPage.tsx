import { useState } from "react";
import { Link } from "react-router-dom";
import SearchIcon from "@mui/icons-material/Search";
import SatelliteComparison from "../SatelliteComparison";
import SpaIcon from "@mui/icons-material/Spa";

const LandingPage = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("http://localhost:8000/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: searchTerm,
          claimed_hectares: 400000,
          location: "Brazil",
          year_start: 2019,
          year_end: 2023,
        }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError("Failed to fetch results.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-full grid grid-rows-[auto_1fr] p-4">
      <Link to="/" className="flex items-center gap-0.5">
        <SpaIcon fontSize="small" className="text-emerald-800" />
        <h1 className=" font-semibold text-xl text-emerald-800">GreenLens</h1>
      </Link>{" "}
      <div className="flex flex-col items-center justify-center gap-15">

        <h1 className="text-6xl font-medium text-center">Don't take their word for it — Search any company to verify their environmental claims</h1>
        <div className="flex items-center gap-1">
          <div className="border rounded-xs flex items-center gap-0.5 px-1">
            <SearchIcon fontSize="inherit" className="text-gray-400" />
            <input
              type="text"
              placeholder="Enter Company Name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="focus:outline-none text-xs p-1"
            />
          </div>
          <button
            type="submit"
            onClick={handleSearch}
            className="text-white bg-emerald-800 rounded-xs px-2 py-1 cursor-pointer text-xs"
          >
            Search
          </button>
        </div>

        {loading && <p className="text-xs text-gray-400">Loading...</p>}
        {error && <p className="text-xs text-red-500">{error}</p>}
        {result && (
          <>
            <pre className="text-xs text-left bg-gray-100 p-4 rounded-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
            <SatelliteComparison />
          </>
        )}
      </div>
    </div>
  );
};

export default LandingPage;
