import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import SpaIcon from "@mui/icons-material/Spa";
import SatelliteComparison from "../SatelliteComparison";
import SkeletonLoader from "./SkeletonLoader";

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
      <div className="border-b border-gray-300 p-4 flex items-center">
        <Link to="/" className="flex items-center gap-0.5">
          <SpaIcon fontSize="small" className="text-emerald-800" />
          <h1 className="font-semibold text-xl text-emerald-800">GreenLens</h1>
        </Link>
      </div>

      {loading ? <SkeletonLoader /> : <div className="grid grid-cols-2 gap-2 p-4 overflow-hidden">
        {/* LEFT: all info */}
        <div className="flex flex-col gap-3 overflow-hidden">
          {/* Company name + summary */}
          <div className="flex flex-col gap-2">
            <h1 className="text-5xl font-medium capitalize">{name}</h1>
            {error && <p className="text-xs text-red-500">{error}</p>}
            {claim?.claim_summary && (
              <p className="text-sm text-gray-600">{claim.claim_summary}</p>
            )}
            {claim?.source_url && (
              <a
                href={claim.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-emerald-700 underline underline-offset-2 w-fit"
              >
                Source ↗
              </a>
            )}
          </div>

          {/* Truth score + Analysis */}
          <div className="border border-gray-300 rounded-md p-4 flex flex-col gap-4 flex-1">
            {verdict ? (
              <>
                <div className="flex gap-6">
                  <div className="flex flex-col gap-2">
                    <p className="text-xs lg:text-lg tracking-tight uppercase font-medium">Truth Score</p>
                    <p className="text-4xl font-medium">{verdict.truth_score}%</p>
                    <p className={`text-sm font-medium capitalize ${verdict.verdict === "verified" ? "text-green-600" : verdict.verdict === "uncertain" ? "text-yellow-500" : "text-red-500"}`}>
                      {verdict.verdict.replace("_", " ")}
                    </p>
                    <div className="text-xs text-gray-500 flex flex-col gap-1">
                      <p>Before pledge: {verdict.avg_loss_before_ha.toLocaleString()} ha lost/yr</p>
                      <p>After pledge: {verdict.avg_loss_after_ha.toLocaleString()} ha lost/yr</p>
                      <p>Forest saved: {verdict.reduction_ha.toLocaleString()} ha/yr</p>
                    </div>
                  </div>
                  <div className="w-px bg-gray-200 self-stretch" />
                  <div className="flex flex-col gap-3 justify-center">
                    <div className="flex flex-col gap-0.5">
                      <p className="text-xs text-gray-400 uppercase tracking-tight">Location</p>
                      <p className="text-sm font-medium">{claim?.location ?? "—"}</p>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <p className="text-xs text-gray-400 uppercase tracking-tight">Hectares</p>
                      <p className="text-sm font-medium">{claim?.hectares != null ? Number(claim.hectares).toLocaleString() : "—"} ha</p>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <p className="text-xs text-gray-400 uppercase tracking-tight">Timeline</p>
                      <p className="text-sm font-medium">{claim?.year_start ?? "—"} – {claim?.year_end ?? "—"}</p>
                    </div>
                  </div>
                </div>
                <div className="border-t border-gray-200 pt-4 flex flex-col gap-2">
                  <p className="text-xs lg:text-lg tracking-tight uppercase font-medium">Analysis</p>
                  {explanation ? (
                    <p className="text-md text-gray-700 leading-relaxed">{explanation}</p>
                  ) : (
                    <p className="text-xs text-gray-400">{loading ? "Generating analysis..." : ""}</p>
                  )}
                  {claim?.source_quote && (
                    <blockquote className="mt-2 border-l-2 border-emerald-400 pl-3 text-xs text-gray-400 italic leading-relaxed">
                      "{claim.source_quote}"
                    </blockquote>
                  )}
                </div>
              </>
            ) : (
              <p className="text-xs text-gray-400">No verdict data</p>
            )}
          </div>
        </div>

        {/* RIGHT: stacked satellite maps */}
        <div className="border border-gray-300 rounded-md p-2 overflow-hidden">
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
              <p className="text-xs text-gray-400">No location data</p>
            </div>
          )}
        </div>
      </div>}
    </div>
  );
};

export default CompanyPage;
