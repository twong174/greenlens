import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const ZOOM = 7;

const ESRI_TILE =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const MODIS_TILE = (date: string) =>
  `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

// GFW Hansen cumulative loss tiles — red = confirmed forest loss since 2000
const GFW_LOSS_TILE =
  "https://tiles.globalforestwatch.org/umd_tree_cover_loss/v1.9/tcd_30/{z}/{x}/{y}.png";

const MapResizer = () => {
  const map = useMap();
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 100);
  }, [map]);
  return null;
};

interface Props {
  lat: number;
  lon: number;
  location: string;
  yearStart: number;
  yearEnd: number;
}

const SatelliteComparison = ({ lat, lon, location, yearStart, yearEnd }: Props) => {
  const center: [number, number] = [lat, lon];
  const beforeDate = `${yearStart}-08-01`;

  return (
    <div className="flex flex-col gap-2 w-full h-full">
      <div className="flex flex-col gap-2 w-full h-full">
        {/* BEFORE — clean satellite, no loss overlay */}
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
            <MapResizer />
          </MapContainer>
        </div>

        {/* AFTER — same satellite + GFW loss heatmap overlay */}
        <div className="flex-1 flex flex-col gap-1 min-h-0">
          <div className="flex items-center gap-2">
            <p className="text-xs font-medium text-gray-500">After — {yearEnd}</p>
            <div className="flex items-center gap-1">
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-red-500 opacity-80" />
              <p className="text-xs text-gray-400">forest loss</p>
            </div>
          </div>
          <div className="relative w-full h-full">
            <MapContainer
              center={center}
              zoom={ZOOM}
              zoomControl={false}
              attributionControl={false}
              style={{ height: "100%", width: "100%", borderRadius: "8px" }}
            >
              <TileLayer url={ESRI_TILE} />
              <TileLayer url={GFW_LOSS_TILE} opacity={0.8} />
              <MapResizer />
            </MapContainer>
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-400">
        {location} · ESRI World Imagery · Forest loss data: Hansen/UMD via GFW
      </p>
    </div>
  );
};

export default SatelliteComparison;
