import { useState } from "react";
import axios from "axios";

import { api } from "../services/api";
import type { Coordinates } from "../types/route";

interface Place extends Coordinates { display_name: string }

interface Props {
  target: "origin" | "destination";
  disabled: boolean;
  onSelect: (point: Coordinates) => void;
  onSearching: (searching: boolean) => void;
}

export default function PointSearch({ target, disabled, onSelect, onSearching }: Props) {
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const label = target === "origin" ? "origem" : "destino";

  async function search(event: React.FormEvent) {
    event.preventDefault();
    if (disabled || searching || query.trim().length < 3) return;
    setSearching(true);
    onSearching(true);
    setPlaces([]);
    setMessage("");
    try {
      const response = await api.get<Place[]>("/places", { params: { q: query.trim() }, timeout: 15000 });
      setPlaces(response.data);
      if (!response.data.length) setMessage("Nenhum endereço encontrado. Inclua a cidade na busca.");
    } catch (error) {
      const detail = axios.isAxiosError(error) ? error.response?.data?.detail : null;
      setMessage(typeof detail === "string" ? detail : "Não foi possível buscar o endereço. Tente novamente ou selecione no mapa.");
    } finally {
      setSearching(false);
      onSearching(false);
    }
  }

  function setCoordinates(event: React.FormEvent) {
    event.preventDefault();
    if (disabled || searching) return;
    const point = { lat: Number(lat), lon: Number(lon) };
    if (!lat.trim() || !lon.trim() || !Number.isFinite(point.lat) || !Number.isFinite(point.lon)
      || Math.abs(point.lat) > 90 || Math.abs(point.lon) > 180) {
      setMessage("Informe latitude entre −90 e 90 e longitude entre −180 e 180.");
      return;
    }
    onSelect(point);
    setPlaces([]);
    setMessage("");
  }

  return (
    <details className="point-search">
      <summary>Definir {label} por endereço ou coordenadas</summary>
      <form onSubmit={search}>
        <label htmlFor="address-search">Endereço da {label}</label>
        <input id="address-search" value={query} minLength={3} maxLength={200}
          placeholder="Rua, número e cidade" required disabled={disabled || searching}
          onChange={(event) => { setQuery(event.target.value); setPlaces([]); setMessage(""); }} />
        <button type="submit" className="secondary-button" disabled={disabled || searching || query.trim().length < 3}>
          {searching ? "Buscando…" : "Buscar endereço"}
        </button>
      </form>
      {places.length > 0 && <ul className="place-results" aria-label="Endereços encontrados">
        {places.map((place, index) => <li key={index}>
          <button type="button" disabled={disabled || searching} onClick={() => {
            onSelect({ lat: place.lat, lon: place.lon }); setPlaces([]); setMessage("");
          }}>{place.display_name}</button>
        </li>)}
      </ul>}
      <form onSubmit={setCoordinates}>
        <label htmlFor="point-lat">Latitude da {label}</label>
        <input id="point-lat" type="number" step="any" min={-90} max={90}
          value={lat} required disabled={disabled || searching} onChange={(event) => setLat(event.target.value)} />
        <label htmlFor="point-lon">Longitude da {label}</label>
        <input id="point-lon" type="number" step="any" min={-180} max={180}
          value={lon} required disabled={disabled || searching} onChange={(event) => setLon(event.target.value)} />
        <button type="submit" className="secondary-button" disabled={disabled || searching}>Usar coordenadas</button>
      </form>
      <p role="status" aria-live="polite">{message}</p>
    </details>
  );
}
