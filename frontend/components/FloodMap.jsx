import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
// import { useState } from "react";
import L from "leaflet";

function ClickHandler({ onSelect }) {
  useMapEvents({
    click(e) {
        onSelect(e.latlng);
    },
  });
  return null;
}

export default function FloodMap({ selectedPoint, setSelectedPoint }) {
  return (
    <MapContainer
        center={[-6.2, 106.8]}
        zoom={10}
        zoomControl={false}
        style={{ height: "100vh", width: "100vw" }}
    >
        <TileLayer
            attribution="© OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <ClickHandler onSelect={setSelectedPoint} />

        {selectedPoint && (
            <Marker position={[selectedPoint.lat, selectedPoint.lng]} />
        )}
    </MapContainer>
  );
}
