import { useState } from "react";
import axios from "axios";

import { api } from "../services/api";
import type { Coordinates } from "../types/route";

interface Place extends Coordinates { display_name: string }

interface Props {
  target: "origin" | "destination";
  disabled: boolean;
  onSelect: (point: Coordinates, name?: string) => void;
  onSearching: (searching: boolean) => void;
}

export default function PointSearch({ target, disabled, onSelect, onSearching }: Props) {
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");
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

  return (
    <div className="point-search">
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
            onSelect({ lat: place.lat, lon: place.lon }, place.display_name); setPlaces([]); setMessage("");
          }}>{place.display_name}</button>
        </li>)}
      </ul>}
      <p role="status" aria-live="polite">{message}</p>
    </div>
  );
}
