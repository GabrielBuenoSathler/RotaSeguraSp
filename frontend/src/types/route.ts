export interface Coordinates {
  lat: number;
  lon: number;
}

export interface RouteResult {
  route_request_id?: number;
  calculated_route_id?: number;
  distance_km?: number;
  duration_seconds?: number;
  geometry_points?: number;
  geometry?: {
    type: "LineString";
    coordinates: [number, number][];
  };
  message?: string;
}

export interface CrimeRiskResult {
  crime: string;
  quantidade_ocorrencias: number;
  pontuacao_original: number;
  pontuacao_ajustada: number;
  pontos_originais_por_km: number | null;
  pontos_ajustados_por_km: number | null;
}

export interface MonthlyOccurrenceResult {
  mes: string | null;
  quantidade_ocorrencias: number;
  pontuacao_ajustada: number;
  crimes: Pick<CrimeRiskResult, "crime" | "quantidade_ocorrencias" | "pontuacao_ajustada">[];
}

export interface RiskResult {
  ocorrencias_por_mes: MonthlyOccurrenceResult[];
  data_agrupamento_configurada: boolean;
  riscos_por_crime: CrimeRiskResult[];
  calculated_route_id: number;
  quantidade_ocorrencias: number;
  pontuacao_original: number;
  pontuacao_ajustada: number;
  pontos_originais_por_km: number | null;
  pontos_ajustados_por_km: number | null;
  raio_analise_metros: number;
  metodologia: string;
  fonte: string;
  atualizado_em: string | null;
  periodo_inicio: string | null;
  periodo_fim: string | null;
  filtro_temporal_aplicado: boolean;
}

export interface RiskData {
  status: { success: boolean; code: string; message: string };
  result: RiskResult | null;
}

export interface RouteOption {
  route: RouteResult;
  risk: RiskData;
}

export interface CalculateResponse extends RouteOption {
  success: boolean;
  alternatives: RouteOption[];
  message: string;
}
