import type { RouteOption } from "../types/route";

function exposure(option: RouteOption): number | undefined {
  const value = option.risk.status.success ? option.risk.result?.pontuacao_ajustada : undefined;
  return value !== undefined && Number.isFinite(value) && value >= 0 ? value : undefined;
}

// Relative to this set of alternatives: lower exposure and shorter time score higher.
// The +1 avoids division by zero when the dataset contains no nearby records.
export function routeBalance(option: RouteOption, options: RouteOption[]): number | undefined {
  const valid = options.filter(candidate => exposure(candidate) !== undefined
    && Number.isFinite(candidate.route.duration_seconds) && candidate.route.duration_seconds! > 0);
  const score = exposure(option);
  const duration = option.route.duration_seconds;
  if (!valid.includes(option) || score === undefined || duration === undefined) return undefined;
  const minimumExposure = Math.min(...valid.map(candidate => exposure(candidate)!));
  const minimumTime = Math.min(...valid.map(candidate => candidate.route.duration_seconds!));
  return 100 * Math.sqrt(((1 + minimumExposure) / (1 + score)) * (minimumTime / duration));
}

export function recommendedRoute(options: RouteOption[]): RouteOption | undefined {
  return options.filter(option => routeBalance(option, options) !== undefined).sort((a, b) =>
    routeBalance(b, options)! - routeBalance(a, options)!
    || a.risk.result!.pontuacao_ajustada - b.risk.result!.pontuacao_ajustada
    || a.route.duration_seconds! - b.route.duration_seconds!
  )[0] ?? options.filter(option => exposure(option) !== undefined).sort((a, b) =>
    exposure(a)! - exposure(b)!
  )[0];
}
