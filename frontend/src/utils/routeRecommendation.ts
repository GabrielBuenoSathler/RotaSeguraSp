import type { RouteOption } from "../types/route";

// Recommend only routes with a successful, finite exposure analysis.
export function recommendedRoute(options: RouteOption[]): RouteOption | undefined {
  return options.filter(option => option.risk.status.success && option.risk.result
    && Number.isFinite(option.risk.result.pontuacao_ajustada)).sort((a, b) =>
    a.risk.result!.pontuacao_ajustada - b.risk.result!.pontuacao_ajustada
    || (a.route.duration_seconds ?? Infinity) - (b.route.duration_seconds ?? Infinity)
    || (a.route.distance_km ?? Infinity) - (b.route.distance_km ?? Infinity)
  )[0];
}
