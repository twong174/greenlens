import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Mato Grosso, Brazil — Amazon deforestation hotspot
const CENTER: [number, number] = [-11.8, -55.3];
const ZOOM = 10;

const gibsTile = (date: string) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual/default/${date}/GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpg`;

const SatelliteComparison = () => {
  return (
    <div className="flex flex-col gap-2 w-full">
      <div className="flex gap-4 w-full h-72">
        <div className="flex-1 flex flex-col gap-1">
          <p className="text-xs font-medium text-gray-500">Before — 2010</p>
          <MapContainer
            center={CENTER}
            zoom={ZOOM}
            zoomControl={false}
            attributionControl={false}
            style={{ height: "100%", width: "100%", borderRadius: "8px" }}
          >
            <TileLayer url={gibsTile("2010-01-01")} />
          </MapContainer>
        </div>

        <div className="flex-1 flex flex-col gap-1">
          <p className="text-xs font-medium text-gray-500">After — 2015</p>
          <MapContainer
            center={CENTER}
            zoom={ZOOM}
            zoomControl={false}
            attributionControl={false}
            style={{ height: "100%", width: "100%", borderRadius: "8px" }}
          >
            <TileLayer url={gibsTile("2015-01-01")} />
          </MapContainer>
        </div>
      </div>
      <p className="text-xs text-gray-400">
        Satellite imagery: Mato Grosso, Brazil — Landsat via NASA GIBS
      </p>
    </div>
  );
};

export default SatelliteComparison;
