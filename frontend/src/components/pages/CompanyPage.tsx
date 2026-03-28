import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import SpaIcon from "@mui/icons-material/Spa";
import SatelliteComparison from "../SatelliteComparison";

const CompanyPage = () => {
  const { name } = useParams();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    setLoading(true);
    fetch("http://localhost:8000/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: name,
        claimed_hectares: 400000,
        location: "Brazil",
        year_start: 2019,
        year_end: 2023,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Request failed");
        return res.json();
      })
      .then((data) => setResult(data))
      .catch(() => setError("Failed to fetch results."))
      .finally(() => setLoading(false));
  }, [name]);

  return (
    <div className="h-screen w-full p-4 grid grid-rows-[auto_1fr]">
      <Link to="/" className="flex items-center gap-0.5">
        <SpaIcon fontSize="small" className="text-emerald-800" />
        <h1 className="font-semibold text-xl text-emerald-800">GreenLens</h1>
      </Link>

      <div className="flex flex-col items-center justify-center gap-4">
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

export default CompanyPage;
