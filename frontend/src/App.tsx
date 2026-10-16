import { useEffect, useRef, useState } from "react";

import MapView from "./components/MapView";
import { crimeGroups } from "./utils/crimeGroups";
import PointSearch from "./components/PointSearch";
import { api } from "./services/api";
import { disabledFeatures, parseFeatures } from "./services/features";
import { recommendedRoute, routeBalance } from "./utils/routeRecommendation";

import type {
  CalculateResponse, Coordinates, RiskData, RouteOption, RouteResult,
} from "./types/route";

import "./App.css";

function InterfaceIcon({ name }: { name: "route" | "pin" | "info" | "shield" }) {
  const paths = {
    route: "M5 6a2 2 0 1 0 0 .01M19 18a2 2 0 1 0 0 .01M7 6h9a4 4 0 0 1 0 8H8a4 4 0 0 0 0 8h9",
    pin: "M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    info: "M12 11v6M12 7v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z",
    shield: "m12 2 8 4v6c0 5-4 8-8 10-4-2-8-5-8-10V6l8-4Zm-4 10 3 3 5-6",
  };
  return <svg className="interface-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>;
}

export default function App() {
  const [features, setFeatures] = useState(disabledFeatures);
  useEffect(() => {
    const controller = new AbortController();
    api.get("/features", { signal: controller.signal, timeout: 10000 })
      .then(({ data }) => setFeatures(parseFeatures(data)))
      .catch(() => { /* Map selection remains available if configuration fails. */ });
    return () => controller.abort();
  }, []);
  const [origin, setOrigin] = useState<Coordinates | null>(null);
  const [destination, setDestination] =
    useState<Coordinates | null>(null);

  const [selecting, setSelecting] = useState<
    "origin" | "destination" | null>("origin");

  const crimePanel = useRef<HTMLDetailsElement>(null);
  const [activePanel, setActivePanel] = useState<"planner" | "map" | "routes" | "crimes">("planner");
  const [detailPanel, setDetailPanel] = useState<"routes" | "crimes">("routes");
  const [heatGroups, setHeatGroups] = useState<string[]>(["pessoa", "patrimonio", "outros"]);
  const [selectedMonth, setSelectedMonth] = useState("todos");
  const [originName, setOriginName] = useState("");
  const [destinationName, setDestinationName] = useState("");

  const [showAlternatives, setShowAlternatives] = useState(false);
  const [transportMode, setTransportMode] = useState("auto");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [result, setResult] = useState<RouteResult | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [options, setOptions] = useState<RouteOption[]>([]);
  const [locating, setLocating] = useState(false);
  const [searching, setSearching] = useState(false);
  const busy = loading || locating || searching;
  const [geometry, setGeometry] = useState<[number, number][] | null>(null);

  useEffect(() => {
    if (!features.geocoding || !origin || originName) return;
    const controller = new AbortController();
    api.get<{ display_name: string } | null>("/places/reverse", {
      params: origin, signal: controller.signal, timeout: 15000,
    }).then(({ data }) => {
      setOriginName(data?.display_name || "Rua não identificada — ponto selecionado no mapa");
    }).catch(() => {
      if (!controller.signal.aborted) setOriginName("Endereço indisponível — ponto selecionado no mapa");
    });
    return () => controller.abort();
  }, [origin, originName, features.geocoding]);

  useEffect(() => {
    if (!features.geocoding || !destination || destinationName) return;
    const controller = new AbortController();
    api.get<{ display_name: string } | null>("/places/reverse", {
      params: destination, signal: controller.signal, timeout: 15000,
    }).then(({ data }) => {
      setDestinationName(data?.display_name || "Rua não identificada — ponto selecionado no mapa");
    }).catch(() => {
      if (!controller.signal.aborted) setDestinationName("Endereço indisponível — ponto selecionado no mapa");
    });
    return () => controller.abort();
  }, [destination, destinationName, features.geocoding]);

  function invalidateResult() {
    setResult(null);
    setRisk(null);
    setGeometry(null);
    setOptions([]);
    setShowAlternatives(false);
  }

  function chooseRoute(option: RouteOption) {
    setSelectedMonth("todos");
    setResult(option.route);
    setRisk(option.risk);
    setGeometry(option.route.geometry?.coordinates.map(
      ([lon, lat]): [number, number] => [lat, lon]
    ) ?? null);
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setError("Seu navegador não oferece localização. Busque uma rua ou escolha no mapa.");
      return;
    }
    setLocating(true);
    setError("");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        invalidateResult();
        setOriginName("");
        setOrigin({ lat: coords.latitude, lon: coords.longitude });
        setSelecting("destination");
        setLocating(false);
      },
      () => {
        setError("Não foi possível obter sua localização. Verifique a permissão do navegador ou selecione a origem no mapa.");
        setLocating(false);
      },
      { timeout: 10000, maximumAge: 60000 }
    );
  }

  function swapPoints() {
    invalidateResult();
    setError("");
    setOriginName(destinationName);
    setDestinationName(originName);
    setSelecting("origin");
    setOrigin(destination);
    setDestination(origin);
  }

  /**
   * Seleciona um ponto no mapa.
   * O primeiro clique define a origem.
   * O segundo clique define o destino.
   */
  function selectPoint(point: Coordinates, name = "") {
    if (busy || !selecting) return;
    setError("");
    invalidateResult();

    if (selecting === "origin") {
      setOrigin(point);
      setOriginName(name);
      setSelecting("destination");
    } else {
      setDestination(point);
      setDestinationName(name);
    }
  }

  /**
   * Limpa a origem, o destino e os resultados.
   */
  function clearSelection() {
    setOriginName("");
    setDestinationName("");
    setOrigin(null);
    setDestination(null);
    invalidateResult();
    setError("");
    setSelecting("origin");
  }

  /**
   * Cria a solicitação e calcula a rota e o risco.
   */
  async function calculateRoute() {
    if (busy) return;
    if (!origin || !destination) {
      setError("Selecione a origem e o destino no mapa.");
      return;
    }

    setLoading(true);
    setError("");
    invalidateResult();

    try {
      // 1. Criar a solicitação de rota.

      const createResponse = await api.post("/rota/", {
        origin_lat: origin.lat,
        origin_lon: origin.lon,
        destination_lat: destination.lat,
        destination_lon: destination.lon,
        transport_mode: transportMode,
      });

      // 2. Recuperar o ID da solicitação.

      const requestId =
        createResponse.data.id ??
        createResponse.data.route_request_id;

      if (requestId == null) {
        throw new Error(
          "A API não retornou o ID da solicitação de rota."
        );
      }

      // 3. Calcular a rota e o risco.

      const calculateResponse = await api.post<CalculateResponse>(
        `/rota/${requestId}/calculate`,
        undefined,
        { headers: { Authorization: `Bearer ${createResponse.data.access_token}` } }
      );

      const data = calculateResponse.data;
      const routeOptions = [{ route: data.route, risk: data.risk }, ...data.alternatives];
      setOptions(routeOptions);
      chooseRoute(recommendedRoute(routeOptions) ?? routeOptions[0]);
      setSelecting(null);
      setDetailPanel("routes");
      setActivePanel("map");
    } catch (err: unknown) {
      console.error("Erro ao calcular rota:", err);

      if (
        typeof err === "object" &&
        err !== null &&
        "response" in err
      ) {
        const response = (
          err as {
            response?: {
              status?: number;
              data?: {
                detail?: string | object | unknown[];
              };
            };
          }
        ).response;

        const detail = response?.data?.detail;

        if (typeof detail === "string") {
          setError(detail);
        } else if (
          typeof detail === "object" &&
          detail !== null &&
          "message" in detail &&
          typeof detail.message === "string"
        ) {
          setError(detail.message);
        } else if (detail !== undefined) {
          setError(JSON.stringify(detail));
        } else {
          setError(
            `Erro HTTP ${response?.status ?? "desconhecido"}. ` +
              "Verifique o backend."
          );
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Erro desconhecido ao calcular a rota.");
      }
    } finally {
      setLoading(false);
    }
  }

  /**
   * Converte a duração em segundos para um formato legível.
   */
  function formatDuration(seconds?: number): string {
    if (seconds === undefined) {
      return "—";
    }

    const minutes = Math.round(seconds / 60);

    if (minutes < 60) {
      return `${minutes} min`;
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return `${hours} h ${remainingMinutes} min`;
  }

  /**
   * Formata as coordenadas para exibição.
   */
  function formatCoordinate(
    point: Coordinates | null
  ): string {
    if (!point) {
      return "Selecione no mapa";
    }

    return "Identificando rua…";
  }

  const recommendation = recommendedRoute(options);
  const recommendedId = recommendation?.route.calculated_route_id;
  const selectedIndex = options.findIndex(option => option.route.calculated_route_id === result?.calculated_route_id);
  const analysis = risk?.status.success ? risk.result : null;
  const monthGroups = analysis?.ocorrencias_por_mes ?? [];
  const selectedGroup = monthGroups.find(group => (group.mes ?? "sem-data") === selectedMonth);
  const heatCells = analysis?.mapa_calor;
  const visibleCount = selectedMonth === "todos" ? analysis?.quantidade_ocorrencias : selectedGroup?.quantidade_ocorrencias;
  const monthLabel = (month: string | null) => month ? new Date(`${month}T12:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" }) : "Data não informada";
  const number = (value: number) => value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  const routeName = (index: number) => index === 0 ? "Trajeto principal" : `Alternativa ${index}`;

  return (
    <main className="app">
      <header className="header">
        <div className="brand">
          <svg className="brand-icon" viewBox="0 0 32 36" fill="none" aria-hidden="true"><path d="M16 2 28 7v10c0 8-6 13-12 16C10 30 4 25 4 17V7L16 2Z" stroke="currentColor" strokeWidth="2.4" /><path d="m10 17 4 4 8-9" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <h1>RotaSegura<span>SP</span></h1>
        </div>
        <div className="header-meta"><span>São Paulo, Brasil</span><span className="status"><InterfaceIcon name="info" />Versão experimental</span></div>
      </header>
      <div className={`workspace ${result ? "has-results" : ""}`} data-panel={activePanel} data-details={detailPanel}>
      <nav className="panel-navigation" aria-label="Painéis do trajeto">
        {([['planner', 'Planejar'], ['map', 'Mapa'], ['routes', 'Rotas'], ['crimes', 'Análise']] as const).map(([panel, label]) =>
          <button key={panel} data-panel={panel} aria-pressed={activePanel === panel} disabled={(panel === "routes" || panel === "crimes") && !result} onClick={() => setActivePanel(panel)}>{label}</button>
        )}
      </nav>
      {result && <nav className="result-navigation" aria-label="Resultados do trajeto">
        {([['routes', 'Rotas'], ['crimes', 'Análise']] as const).map(([panel, label]) =>
          <button key={panel} aria-pressed={detailPanel === panel} onClick={() => setDetailPanel(panel)}>{label}</button>
        )}
      </nav>}
        <aside className="planner" aria-labelledby="planner-title">
          <h2 id="planner-title"><InterfaceIcon name="route" />Seu trajeto</h2>
          <p className="hint">De onde você sai e aonde quer chegar?</p>
          <div className="point-list">
            {(["origin", "destination"] as const).map((target, index) => (
              <button key={target} type="button" className="selection-item" aria-pressed={selecting === target}
                disabled={busy || !!result} onClick={() => setSelecting(target)}>
                <span className="point-icon">{index === 0 ? "A" : "B"}</span>
                <span><strong>{index === 0 ? "Origem" : "Destino"}</strong>
                <small title={(index === 0 ? originName : destinationName) || undefined}>{(index === 0 ? originName : destinationName) || formatCoordinate(index === 0 ? origin : destination)}</small></span>
              </button>
            ))}
          </div>
          {result ? <button className="secondary-button" disabled={busy} onClick={() => { invalidateResult(); setSelecting("origin"); setActivePanel("planner"); }}>Editar pontos</button> : <>
            {selecting && features.geocoding && <PointSearch key={selecting} target={selecting} disabled={busy} onSelect={selectPoint} onSearching={setSearching} />}
            <div className="point-actions">
              <button className="text-button" disabled={busy} onClick={useCurrentLocation}>{locating ? "Obtendo localização…" : "Usar minha localização"}</button>
              <button className="text-button" disabled={busy || !origin || !destination} onClick={swapPoints}>Inverter pontos</button>
            </div>
          </>}
          <label htmlFor="transport" className="field-label">Meio de transporte</label>
          <select id="transport" disabled={busy} value={transportMode} onChange={event => { setTransportMode(event.target.value); invalidateResult(); setSelecting("origin"); setError(""); }}>
            <option value="auto">Carro</option><option value="bicycle">Bicicleta</option><option value="pedestrian">A pé</option><option value="motorcycle">Motocicleta</option>
          </select>
          <button className="primary-button" disabled={!origin || !destination || busy} onClick={calculateRoute}>{loading ? "Calculando trajeto…" : result ? "Recalcular rota" : "Calcular rota"}</button>
          <button className="text-button clear-button" disabled={busy || (!origin && !destination)} onClick={clearSelection}>Limpar seleção</button>
          <p className="selection-help" role="status" aria-live="polite">{loading ? "Calculando o trajeto e analisando as ocorrências." : result ? "Sua rota está pronta. Veja o trajeto no mapa." : !origin ? "Defina a origem para começar." : !destination ? "Agora defina o destino." : "Origem e destino definidos. Você já pode calcular."}</p>
          {error && <div className="error-message" role="alert">{error}</div>}
        </aside>

        <section className={`map-section ${selecting && !busy ? "is-editing" : ""}`} aria-label="Mapa dos trajetos">
          <div className="map-toolbar"><strong><InterfaceIcon name="pin" />{result ? routeName(selectedIndex) : "São Paulo, SP"}</strong><span>{busy ? "Aguarde…" : selecting ? `Clique para definir ${selecting === "origin" ? "a origem" : "o destino"}` : "Mapa de calor do trajeto selecionado"}</span></div>
          <MapView heatCells={heatCells ?? []} heatGroups={heatGroups} heatMonth={selectedMonth} origin={origin} destination={destination} geometry={geometry} options={showAlternatives ? options : options.filter(option => option.route.calculated_route_id === result?.calculated_route_id)} recommendedId={recommendedId} selectedId={result?.calculated_route_id}
            editing={!!selecting && !busy} onSelectPoint={selectPoint} onChooseRoute={chooseRoute} />
          {analysis && <details className="heat-controls">
            <summary>Camadas do mapa de calor</summary>
            <div className="heat-controls-body">
            <div className="heat-groups">{crimeGroups.map(group => <label key={group.id} title={group.detail}>
              <input type="checkbox" checked={heatGroups.includes(group.id)} onChange={event => setHeatGroups(current => event.target.checked ? [...current, group.id] : current.filter(id => id !== group.id))} />
              <i style={{ background: group.color }} /><span>{group.label}</span>
            </label>)}</div>
            {analysis.data_agrupamento_configurada && <select aria-label="Mês do mapa de calor" value={selectedMonth} onChange={event => setSelectedMonth(event.target.value)}>
              <option value="todos">Todo o período</option>
              {monthGroups.map(group => <option key={group.mes ?? "sem-data"} value={group.mes ?? "sem-data"}>{monthLabel(group.mes)}</option>)}
            </select>}
            <small role="status">{!heatCells ? "Mapa de calor indisponível. Recalcule a rota após atualizar a API." : !heatGroups.length ? "Selecione um grupo para visualizar." : `${number(heatCells.filter(cell => heatGroups.includes(cell.grupo) && (selectedMonth === "todos" || (cell.mes ?? "sem-data") === selectedMonth)).reduce((sum, cell) => sum + cell.quantidade, 0))} registros · maior intensidade = maior concentração`}</small>
            </div>
          </details>}
          <div className="map-legend"><span><b>A</b> Origem</span><span><b>B</b> Destino</span><span><i /> {recommendation ? "Recomendada" : "Trajeto"}</span>{showAlternatives && <span><i className="alternative-line" /> Alternativas</span>}</div>
        </section>

        {options.length > 0 && <section className="comparison" aria-labelledby="comparison-title">
          <div className="section-heading"><h2 id="comparison-title">Seu caminho</h2><span>{options.length} {options.length === 1 ? "trajeto encontrado" : "trajetos encontrados"}</span></div>
          <p className="hint">A recomendação equilibra tempo e exposição aos registros. Quanto maior o índice, melhor esse equilíbrio entre os trajetos analisados.</p>
          {options.length > 1 && <button className="secondary-button alternatives-toggle" aria-expanded={showAlternatives} onClick={() => setShowAlternatives(value => !value)}>{showAlternatives ? "Ocultar alternativas" : "Ver alternativas de trajeto"}</button>}
          {showAlternatives && <p className="hint">Uma rota mais rápida pode ter maior exposição aos registros. Compare antes de escolher.</p>}
          <div className={`route-options ${showAlternatives ? "" : "single-route"}`}>{options.filter(option => showAlternatives || option.route.calculated_route_id === result?.calculated_route_id).map(option => {
            const index = options.indexOf(option);
            const balance = routeBalance(option, options);
            const data = option.risk.status.success ? option.risk.result : null;
            return <article className="route-option" key={option.route.calculated_route_id} data-recommended={recommendedId === option.route.calculated_route_id} data-selected={result?.calculated_route_id === option.route.calculated_route_id}>
              <button className="route-select" aria-pressed={result?.calculated_route_id === option.route.calculated_route_id} onClick={() => chooseRoute(option)}>
                <span className="route-option-heading"><strong>{routeName(index)}{recommendedId === option.route.calculated_route_id && <small className="recommended-badge">Recomendada</small>}</strong><span>{result?.calculated_route_id === option.route.calculated_route_id ? "Selecionada" : "Selecionar"}</span></span>
                <span className="route-metrics"><span><small>Tempo</small><b>{formatDuration(option.route.duration_seconds)}</b></span><span><small>Distância</small><b>{option.route.distance_km === undefined ? "—" : `${number(option.route.distance_km)} km`}</b></span><span><small>Ocorrências</small><b>{data ? number(data.quantidade_ocorrencias) : "—"}</b></span></span>
                <span className="exposure-score"><b>{balance === undefined ? "—" : `${number(Math.round(balance))}/100`}</b><small>Equilíbrio entre exposição e tempo · maior é melhor</small></span>
                {data && <span className="exposure-detail">{number(data.pontuacao_ajustada)} pontos de exposição</span>}
              </button>
              {!data && <p className="route-unavailable" role="status">{option.risk.status.message}</p>}
            </article>;
          })}</div>
        </section>}

        {risk && <details ref={crimePanel} tabIndex={-1} className="crime-panel" id="crime-details" key={result?.calculated_route_id} open>
          <summary>Sobre a análise</summary>
          <div className="panel-body">{analysis ? <>
            <p className="hint">Registros em até {analysis.raio_analise_metros} metros deste trajeto, agrupados no mapa de calor.</p>
            {analysis.data_agrupamento_configurada ? <div className="month-filter">
              <label htmlFor="occurrence-month" className="field-label">Data das ocorrências</label>
              <select id="occurrence-month" value={selectedMonth} onChange={event => setSelectedMonth(event.target.value)}>
                <option value="todos">Todo o período ({number(analysis.quantidade_ocorrencias)})</option>
                {monthGroups.map(group => <option key={group.mes ?? "sem-data"} value={group.mes ?? "sem-data"}>{monthLabel(group.mes)} ({number(group.quantidade_ocorrencias)})</option>)}
              </select>
              <p className="hint" role="status">{number(visibleCount ?? 0)} ocorrências · {selectedMonth === "todos" ? "todo o período" : monthLabel(selectedGroup?.mes ?? null)}. O filtro altera o mapa de calor; a comparação das rotas considera todo o período analisado.</p>
            </div> : <p className="hint">A classificação por data ainda não está disponível nesta base.</p>}
            <p className="hint">Veja a concentração dos registros no mapa. Ative os grupos desejados na legenda.</p>
            <details className="methodology"><summary>Como a análise funciona</summary>
              <p>Índice de equilíbrio = 100 × raiz de [(1 + menor exposição) / (1 + exposição da rota) × menor tempo / tempo da rota]. Tempo e exposição têm o mesmo peso. O índice é relativo aos trajetos calculados e não deve ser comparado entre buscas. Sem tempo ou análise válidos, fica indisponível.</p>
              <p>Não há dados de fluxo de pessoas ou veículos nesta base. Portanto, não é possível estimar ocorrências por viajante nem a chance de sofrer um crime. O índice não mede segurança absoluta; ausência de registros não garante segurança.</p>
              <p>A pontuação considera a gravidade e a proximidade das ocorrências. Ela é um indicador experimental, não uma probabilidade de sofrer um crime.</p>
              <dl><div><dt>Pontuação original</dt><dd>{number(analysis.pontuacao_original)}</dd></div><div><dt>Pontuação ajustada</dt><dd>{number(analysis.pontuacao_ajustada)}</dd></div><div><dt>Pontos ajustados por km</dt><dd>{analysis.pontos_ajustados_por_km === null ? "Indisponível" : number(analysis.pontos_ajustados_por_km)}</dd></div></dl>
              <p>Fonte: {analysis.fonte}. Atualização: {analysis.atualizado_em ? new Date(`${analysis.atualizado_em}T12:00:00`).toLocaleDateString("pt-BR") : "não informada"}.</p>
              <p>{analysis.filtro_temporal_aplicado && analysis.periodo_inicio && analysis.periodo_fim ? `Período: ${new Date(analysis.periodo_inicio).toLocaleDateString("pt-BR")} a ${new Date(analysis.periodo_fim).toLocaleDateString("pt-BR")}.` : "Período: todas as datas da base; filtro temporal não configurado."}</p>
            </details>
          </> : <p role="status">{risk.status.message}</p>}
          {!geometry && <p className="hint">O desenho deste trajeto está indisponível no mapa.</p>}
          </div>
        </details>}
      </div>
      <footer className="footer"><p>Os registros não garantem a segurança de uma rota. Ausência de ocorrências na base não significa ausência de risco.</p><span>RotaSegura SP · Dados de ocorrências e mapas OpenStreetMap</span></footer>
    </main>
  );
}
