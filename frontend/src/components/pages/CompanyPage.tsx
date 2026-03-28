import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import SpaIcon from "@mui/icons-material/Spa";
import SatelliteComparison from "../SatelliteComparison";

const CompanyPage = () => {
  const { name } = useParams();
  const [claim, setClaim] = useState<any>(null);
  const [verdict, setVerdict] = useState<any>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    setLoading(true);

    fetch(`http://localhost:8000/search_claim/${encodeURIComponent(name)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Request failed");
        return res.json();
      })
      .then((claimData) => {
        setClaim(claimData);
        return fetch("http://localhost:8000/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company: name,
            claimed_hectares: claimData.hectares ?? 400000,
            location: claimData.location ?? "Brazil",
            year_start: claimData.year_start ?? 2019,
            year_end: claimData.year_end ?? 2023,
          }),
        });
      })
      .then((res) => {
        if (!res.ok) throw new Error("Verify failed");
        return res.json();
      })
      .then((verdictData) => {
        setVerdict(verdictData);
        return fetch("http://localhost:8000/explain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(verdictData),
        });
      })
      .then((res) => res.json())
      .then((data) => setExplanation(data.explanation))
      .catch(() => setError("Failed to fetch data."))
      .finally(() => setLoading(false));
  }, [name]);

  return (
    <div className="h-screen w-full grid grid-rows-[auto_1fr]">
      <div className="border-b border-gray-500 p-4 flex items-center">
        <Link to="/" className="flex items-center gap-0.5">
          <SpaIcon fontSize="small" className="text-emerald-800" />
          <h1 className="font-semibold text-xl text-emerald-800">GreenLens</h1>
        </Link>
      </div>

      <div className="grid grid-rows-[auto_1fr] p-4 gap-2 overflow-hidden">
        <div className="flex flex-col">
          <h1 className="text-4xl font-medium capitalize">{name}</h1>
          {loading && <p className="text-xs text-gray-400">Searching for claim...</p>}
          {error && <p className="text-xs text-red-500">{error}</p>}
          {claim && (
            <h3 className="text-sm text-gray-600">{claim.claim_summary}</h3>
          )}
        </div>

        <div className="grid grid-rows-2 gap-2 overflow-hidden">
          <div className="grid grid-cols-[60%_40%] gap-2 overflow-hidden">
            <div className="border overflow-hidden">
              {claim?.coords ? (
                <SatelliteComparison
                  lat={claim.coords.lat}
                  lon={claim.coords.lon}
                  location={claim.location}
                  yearStart={claim.year_start}
                  yearEnd={claim.year_end}
                />
              ) : (
                <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                  <p className="text-xs text-gray-400">{loading ? "Loading map..." : "No location data"}</p>
                </div>
              )}
            </div>
            <div className="border p-4 flex flex-col gap-2">
              {verdict && (
                <>
                  <p className="text-xs text-gray-500">Truth Score</p>
                  <p className="text-4xl font-semibold">{verdict.truth_score}%</p>
                  <p className={`text-sm font-medium capitalize ${verdict.verdict === "verified" ? "text-green-600" : verdict.verdict === "uncertain" ? "text-yellow-500" : "text-red-500"}`}>
                    {verdict.verdict.replace("_", " ")}
                  </p>
                  <div className="text-xs text-gray-400 mt-2 flex flex-col gap-1">
                    <p>Avg loss before: {verdict.avg_loss_before_ha.toLocaleString()} ha/yr</p>
                    <p>Avg loss after: {verdict.avg_loss_after_ha.toLocaleString()} ha/yr</p>
                    <p>Reduction: {verdict.reduction_ha.toLocaleString()} ha</p>
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="border bg-green-100"></div>
            <div className="border p-4 flex flex-col gap-2">
              <p className="text-xs text-gray-500">Analysis</p>
              {explanation ? (
                <p className="text-sm text-gray-700 leading-relaxed">{explanation}</p>
              ) : (
                <p className="text-xs text-gray-400">{loading ? "Generating analysis..." : ""}</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CompanyPage;
