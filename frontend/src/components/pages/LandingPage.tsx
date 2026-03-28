import { useState } from "react";
import SearchIcon from "@mui/icons-material/Search";

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
      <h1 className="uppercase font-medium text-xl">GreenLens</h1>
      <div className="flex flex-col items-center justify-center gap-4">
        <div className="flex items-center gap-1">
          <div className="border rounded-md flex items-center gap-1 px-2">
            <SearchIcon fontSize="small" className="text-gray-400" />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              className="focus:outline-none text-xs p-2"
            />
          </div>
          <button
            type="submit"
            onClick={handleSearch}
            className="text-white bg-green-500 rounded-md px-3 py-2 cursor-pointer text-xs"
          >
            Search
          </button>
        </div>

        {loading && <p className="text-xs text-gray-400">Loading...</p>}
        {error && <p className="text-xs text-red-500">{error}</p>}
        {result && (
          <pre className="text-xs text-left bg-gray-100 p-4 rounded-md">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

export default LandingPage;
