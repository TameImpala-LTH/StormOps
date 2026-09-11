import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { useTheme } from '../context/ThemeContext';
import { GeocodedLocationSchema, TargetPeriodWeather } from '../types/weather';
import { MapPin, Compass } from 'lucide-react';

interface WeatherMapProps {
  location: GeocodedLocationSchema;
  weather: TargetPeriodWeather;
  locationB?: GeocodedLocationSchema | null;
  weatherB?: TargetPeriodWeather | null;
  periodLabel: string;
  onCheckWeatherAtCoords?: (lat: number, lng: number) => void;
}

// Configurable Basemap Tile Layer URL & Attribution (single source of truth)
export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

export const WeatherMap: React.FC<WeatherMapProps> = ({
  location,
  weather,
  locationB,
  weatherB,
  periodLabel,
  onCheckWeatherAtCoords,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const markerBRef = useRef<L.Marker | null>(null);
  const clickMarkerRef = useRef<L.Marker | null>(null);
  const { theme } = useTheme();

  const [mapReady, setMapReady] = useState(false);

  const lat = location.latitude;
  const lng = location.longitude;
  const placeName = location.name;

  // Build custom DivIcon HTML
  const createMarkerHtml = (locName: string, pw: TargetPeriodWeather, labelColor: string = 'var(--accent)') => {
    const temp = Math.round(pw.temperature);
    const rain = pw.precipitation_probability;
    return `
      <div style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        border-radius: 9999px;
        background-color: var(--surface);
        border: 1px solid var(--border);
        color: var(--text-primary);
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
        font-family: inherit;
        font-size: 11px;
        white-space: nowrap;
        transform: translate(-50%, -100%);
      ">
        <span style="font-weight: 600; color: ${labelColor};">${temp}°C</span>
        <span style="font-weight: 500;">${locName}</span>
        <span style="
          font-family: monospace;
          font-size: 9px;
          padding: 1px 5px;
          border-radius: 4px;
          background-color: rgba(56,189,248,0.12);
          color: #38bdf8;
          border: 1px solid rgba(56,189,248,0.25);
        ">${rain}% rain</span>
      </div>
    `;
  };

  // Build detailed Popup HTML
  const createPopupHtml = (loc: GeocodedLocationSchema, pw: TargetPeriodWeather) => {
    const fullLoc = `${loc.name}${loc.admin1 ? ', ' + loc.admin1 : ''}${loc.country ? ', ' + loc.country : ''}`;
    return `
      <div style="padding: 6px; font-family: inherit; min-width: 180px;">
        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
          ${fullLoc}
        </div>
        <div style="font-size: 10px; font-family: monospace; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 8px;">
          ${periodLabel}
        </div>
        <div style="display: flex; align-items: baseline; gap: 6px; margin-bottom: 6px;">
          <span style="font-size: 24px; font-weight: 300; color: var(--text-primary);">${Math.round(pw.temperature)}°C</span>
          <span style="font-size: 11px; color: var(--text-secondary); capitalize">${pw.condition}</span>
        </div>
        <div style="font-size: 11px; display: grid; grid-template-cols: 1fr 1fr; gap: 4px; border-top: 1px solid var(--border-muted); padding-top: 6px;">
          <div><span style="color: var(--text-tertiary);">Feels like:</span> ${Math.round(pw.feels_like)}°C</div>
          <div><span style="color: var(--text-tertiary);">Rain:</span> ${pw.precipitation_probability}%</div>
          <div><span style="color: var(--text-tertiary);">Precip:</span> ${pw.precipitation} mm</div>
          <div><span style="color: var(--text-tertiary);">Wind:</span> ${pw.wind_speed} km/h</div>
        </div>
      </div>
    `;
  };

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [lat, lng],
        zoom: 10,
        zoomControl: true,
        attributionControl: true,
      });

      const tileLayer = L.tileLayer(TILE_URL, {
        attribution: TILE_ATTRIBUTION,
        maxZoom: 19,
      }).addTo(map);

      tileLayerRef.current = tileLayer;

      // Create Custom DivIcon Marker A
      const customIconA = L.divIcon({
        className: 'stormops-weather-marker',
        html: createMarkerHtml(placeName, weather, 'var(--accent)'),
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });

      const markerA = L.marker([lat, lng], { icon: customIconA }).addTo(map);
      markerA.bindPopup(createPopupHtml(location, weather));
      markerRef.current = markerA;

      // Create Marker B if comparing locations
      if (locationB && weatherB) {
        const customIconB = L.divIcon({
          className: 'stormops-weather-marker-b',
          html: createMarkerHtml(locationB.name, weatherB, '#38bdf8'),
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        });
        const markerB = L.marker([locationB.latitude, locationB.longitude], { icon: customIconB }).addTo(map);
        markerB.bindPopup(createPopupHtml(locationB, weatherB));
        markerBRef.current = markerB;

        map.fitBounds(
          [
            [lat, lng],
            [locationB.latitude, locationB.longitude],
          ],
          { padding: [50, 50] }
        );
      }

      // Handle map click for optional location query
      map.on('click', (e: L.LeafletMouseEvent) => {
        const clickLat = Math.round(e.latlng.lat * 10000) / 10000;
        const clickLng = Math.round(e.latlng.lng * 10000) / 10000;

        if (clickMarkerRef.current) {
          map.removeLayer(clickMarkerRef.current);
        }

        const tempIcon = L.divIcon({
          className: 'stormops-click-pin',
          html: `
            <div style="
              width: 12px;
              height: 12px;
              border-radius: 50%;
              background-color: #34d399;
              border: 2px solid #ffffff;
              box-shadow: 0 0 10px rgba(52,211,153,0.8);
              transform: translate(-50%, -50%);
            "></div>
          `,
          iconSize: [0, 0],
          iconAnchor: [0, 0],
        });

        const clickMarker = L.marker([clickLat, clickLng], { icon: tempIcon }).addTo(map);
        const popupDiv = document.createElement('div');
        popupDiv.style.padding = '4px';
        popupDiv.style.textAlign = 'center';
        popupDiv.innerHTML = `
          <div style="font-size: 11px; font-family: monospace; color: var(--text-secondary); margin-bottom: 6px;">
            ${clickLat}, ${clickLng}
          </div>
          <button id="btn-check-weather-click" style="
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 500;
            border-radius: 8px;
            background-color: var(--btn-primary-bg);
            color: var(--btn-primary-text);
            border: none;
            cursor: pointer;
          ">Check weather here</button>
        `;

        clickMarker.bindPopup(popupDiv).openPopup();
        clickMarkerRef.current = clickMarker;

        setTimeout(() => {
          const btn = document.getElementById('btn-check-weather-click');
          if (btn && onCheckWeatherAtCoords) {
            btn.onclick = () => {
              onCheckWeatherAtCoords(clickLat, clickLng);
              map.closePopup();
            };
          }
        }, 50);
      });

      mapInstanceRef.current = map;
      setMapReady(true);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Synchronize Map view & Marker positions when location or locationB changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !mapReady) return;

    if (locationB && weatherB) {
      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lng]);
        markerRef.current.setIcon(
          L.divIcon({
            className: 'stormops-weather-marker',
            html: createMarkerHtml(placeName, weather, 'var(--accent)'),
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          })
        );
        markerRef.current.getPopup()?.setContent(createPopupHtml(location, weather));
      }

      if (!markerBRef.current) {
        const markerB = L.marker([locationB.latitude, locationB.longitude], {
          icon: L.divIcon({
            className: 'stormops-weather-marker-b',
            html: createMarkerHtml(locationB.name, weatherB, '#38bdf8'),
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          }),
        }).addTo(map);
        markerB.bindPopup(createPopupHtml(locationB, weatherB));
        markerBRef.current = markerB;
      } else {
        markerBRef.current.setLatLng([locationB.latitude, locationB.longitude]);
        markerBRef.current.setIcon(
          L.divIcon({
            className: 'stormops-weather-marker-b',
            html: createMarkerHtml(locationB.name, weatherB, '#38bdf8'),
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          })
        );
        markerBRef.current.getPopup()?.setContent(createPopupHtml(locationB, weatherB));
      }

      map.fitBounds(
        [
          [lat, lng],
          [locationB.latitude, locationB.longitude],
        ],
        { padding: [50, 50] }
      );
    } else {
      if (markerBRef.current) {
        map.removeLayer(markerBRef.current);
        markerBRef.current = null;
      }
      map.flyTo([lat, lng], 10, {
        duration: 1.2,
        easeLinearity: 0.25,
      });

      if (markerRef.current) {
        markerRef.current.setLatLng([lat, lng]);
        markerRef.current.setIcon(
          L.divIcon({
            className: 'stormops-weather-marker',
            html: createMarkerHtml(placeName, weather, 'var(--accent)'),
            iconSize: [0, 0],
            iconAnchor: [0, 0],
          })
        );
        markerRef.current.getPopup()?.setContent(createPopupHtml(location, weather));
      }
    }

    if (clickMarkerRef.current) {
      map.removeLayer(clickMarkerRef.current);
      clickMarkerRef.current = null;
    }
  }, [lat, lng, locationB?.latitude, locationB?.longitude, weather.temperature, weatherB?.temperature, periodLabel, theme, mapReady]);

  // Update Tile Layer when Theme changes
  useEffect(() => {
    if (!tileLayerRef.current) return;
    tileLayerRef.current.setUrl(TILE_URL);
  }, [theme]);

  // Recenter map on active location
  const handleRecenter = () => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([lat, lng], 10);
    }
  };

  return (
    <div className="space-y-3 pt-4" style={{ borderTop: '1px solid var(--border-muted)' }}>
      {/* Header Bar */}
      <div className="flex items-center justify-between text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
        <span className="flex items-center gap-1.5 font-medium">
          <MapPin className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
          INTERACTIVE WEATHER MAP
        </span>
        <button
          type="button"
          onClick={handleRecenter}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-mono border cursor-pointer transition-colors"
          style={{
            backgroundColor: 'var(--surface-elevated)',
            borderColor: 'var(--border-muted)',
            color: 'var(--text-secondary)',
          }}
          title="Recenter map on selected location"
        >
          <Compass className="w-3 h-3" /> Recenter ({location.name})
        </button>
      </div>

      {/* Map Element Container */}
      <div
        className="w-full h-[300px] sm:h-[340px] rounded-2xl overflow-hidden relative shadow-inner"
        style={{ border: '1px solid var(--border)' }}
      >
        <div ref={mapContainerRef} className="w-full h-full z-0" />
      </div>
    </div>
  );
};
