import { useEffect } from "react";
import { useMap } from "react-leaflet";
import type { HeatCell } from "../types/route";

import { crimeGroups } from "../utils/crimeGroups";

export default function CrimeHeatmap({ cells, groups, month }: {
  cells: HeatCell[];
  groups: string[];
  month: string;
}) {
  const map = useMap();
  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.className = "crime-heat-canvas";
    canvas.setAttribute("aria-hidden", "true");
    map.getContainer().appendChild(canvas);
    const visible = cells.filter(cell => groups.includes(cell.grupo)
      && (month === "todos" || (cell.mes ?? "sem-data") === month));
    // A common scale keeps the three crime groups comparable.
    const maximum = cells.reduce((maximum, cell) => Math.max(maximum, cell.quantidade), 1);
    function draw() {
      const size = map.getSize();
      if (size.x <= 0 || size.y <= 0) return;
      const ratio = window.devicePixelRatio || 1;
      canvas.width = size.x * ratio;
      canvas.height = size.y * ratio;
      canvas.style.width = `${size.x}px`;
      canvas.style.height = `${size.y}px`;
      const context = canvas.getContext("2d");
      if (!context) return;
      context.scale(ratio, ratio);
      const radius = Math.max(14, Math.min(48, 22 * 2 ** (map.getZoom() - 15)));
      for (const group of crimeGroups) {
        // Accumulate density before colorizing; overlapping events intensify the heat.
        context.clearRect(0, 0, size.x, size.y);
        for (const cell of visible.filter(cell => cell.grupo === group.id)) {
          const point = map.latLngToContainerPoint([cell.lat, cell.lon]);
          if (point.x < -radius || point.y < -radius || point.x > size.x + radius || point.y > size.y + radius) continue;
          const gradient = context.createRadialGradient(point.x, point.y, 0, point.x, point.y, radius);
          gradient.addColorStop(0, `rgba(0,0,0,${0.15 + 0.65 * Math.sqrt(cell.quantidade / maximum)})`);
          gradient.addColorStop(1, "rgba(0,0,0,0)");
          context.fillStyle = gradient;
          context.fillRect(point.x - radius, point.y - radius, radius * 2, radius * 2);
        }
        const layer = context.getImageData(0, 0, canvas.width, canvas.height);
        const rgb = group.color.match(/\w\w/g)!.map(value => parseInt(value, 16));
        for (let i = 0; i < layer.data.length; i += 4) {
          layer.data[i] = rgb[0]; layer.data[i + 1] = rgb[1]; layer.data[i + 2] = rgb[2];
        }
        // Save each colored layer while drawing the next one.
        const buffer = document.createElement("canvas");
        buffer.width = canvas.width; buffer.height = canvas.height;
        buffer.getContext("2d")!.putImageData(layer, 0, 0);
        layers.push(buffer);
      }
      context.clearRect(0, 0, size.x, size.y);
      for (const layer of layers) context.drawImage(layer, 0, 0, size.x, size.y);
      layers.length = 0;
    }
    const layers: HTMLCanvasElement[] = [];
    draw();
    map.on("move zoom resize", draw);
    return () => { map.off("move zoom resize", draw); canvas.remove(); };
  }, [map, cells, groups, month]);
  return null;
}
