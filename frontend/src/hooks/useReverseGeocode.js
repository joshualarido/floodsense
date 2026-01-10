import { useEffect, useState } from "react";

export function useReverseGeocode(point) {
  const [locationName, setLocationName] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!point) {
      setLocationName(null);
      return;
    }

    let cancelled = false;

    async function fetchLocation() {
      setLoading(true);

      try {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${point.lat}&lon=${point.lng}`,
          {
            headers: {
              "Accept": "application/json",
              // good practice for Nominatim
              "User-Agent": "FloodSense/1.0",
            },
          }
        );

        const data = await res.json();

        if (!cancelled) {
          setLocationName(
            data.display_name ??
              `${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}`
          );
        }
      } catch {
        if (!cancelled) {
          setLocationName(`${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchLocation();

    return () => {
      cancelled = true;
    };
  }, [point]);

  return { locationName, loading };
}
