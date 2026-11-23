import type { Coordinates } from "../types/route";

export function pointLabel(point: Coordinates | null, name: string, geocodingEnabled: boolean): string {
  if (!point) return "Selecione no mapa";
  if (name) return name;
  return geocodingEnabled ? "Identificando rua…" : "Ponto selecionado no mapa";
}
