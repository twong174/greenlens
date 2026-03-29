import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const ZOOM = 7;

const ESRI_TILE = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const MODIS_TILE = (date: string) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

interface Props {
  lat: number;
  lon: number;
  location: string;
  yearStart: number;
  yearEnd: number;
}

const SatelliteComparison = ({ lat, lon, location, yearStart }: Props) => {
  const center: [number, number] = [lat, lon];
  const beforeDate = `${yearStart}-08-01`;

  return (
    <div className="flex flex-col gap-2 w-full h-full">
      <div className="flex flex-col gap-2 w-full h-full">
        <div className="flex-1 flex flex-col gap-1 min-h-0">
          <p className="text-xs font-medium text-gray-500">Before — {yearStart}</p>
          <MapContainer
            center={center}
            zoom={ZOOM}
            zoomControl={false}
            attributionControl={false}
            style={{ height: "100%", width: "100%", borderRadius: "8px" }}
          >
            <TileLayer url={MODIS_TILE(beforeDate)} />
          </MapContainer>
        </div>

        <div className="flex-1 flex flex-col gap-1 min-h-0">
          <p className="text-xs font-medium text-gray-500">Current</p>
          <MapContainer
            center={center}
            zoom={ZOOM}
            zoomControl={false}
            attributionControl={false}
            style={{ height: "100%", width: "100%", borderRadius: "8px" }}
          >
            <TileLayer url={ESRI_TILE} />
          </MapContainer>
        </div>
      </div>
      <p className="text-xs text-gray-400">
        {location} — MODIS Terra (before) · ESRI World Imagery (current)
      </p>
    </div>
  );
};

export default SatelliteComparison;
