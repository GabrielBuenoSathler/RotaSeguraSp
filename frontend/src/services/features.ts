export type Features = {
  geocoding: boolean;
  route_alternatives: boolean;
};

export const disabledFeatures: Features = { geocoding: false, route_alternatives: false };

export function parseFeatures(value: unknown): Features {
  if (!value || typeof value !== "object") return disabledFeatures;
  return {
    geocoding: "geocoding" in value && value.geocoding === true,
    route_alternatives: "route_alternatives" in value && value.route_alternatives === true,
  };
}
