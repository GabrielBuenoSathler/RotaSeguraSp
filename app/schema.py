from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.route_request import TransportMode


class RouteRequestCreate(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)

    destination_lat: float = Field(ge=-90, le=90)
    destination_lon: float = Field(ge=-180, le=180)

    transport_mode: TransportMode = TransportMode.AUTO


class RouteRequestResponse(BaseModel):
    access_token: str
    id: int
    created_at: datetime
    message: str


class RouteGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]]


class RouteResult(BaseModel):
    route_request_id: int
    calculated_route_id: int
    transport_mode: TransportMode
    distance_km: float
    duration_seconds: int
    geometry_points: int
    geometry: RouteGeometry


class CrimeRiskResult(BaseModel):
    crime: str
    quantidade_ocorrencias: int
    pontuacao_original: int
    pontuacao_ajustada: float
    pontos_originais_por_km: float | None
    pontos_ajustados_por_km: float | None


class MonthlyCrimeResult(BaseModel):
    crime: str
    quantidade_ocorrencias: int
    pontuacao_ajustada: float


class MonthlyOccurrenceResult(BaseModel):
    mes: date | None
    quantidade_ocorrencias: int
    pontuacao_ajustada: float
    crimes: list[MonthlyCrimeResult]


class RiskResult(BaseModel):
    ocorrencias_por_mes: list[MonthlyOccurrenceResult] = Field(default_factory=list)
    data_agrupamento_configurada: bool = False
    riscos_por_crime: list[CrimeRiskResult] = Field(default_factory=list)
    calculated_route_id: int
    quantidade_ocorrencias: int
    pontuacao_original: int
    pontuacao_ajustada: float
    pontos_originais_por_km: float | None
    pontos_ajustados_por_km: float | None
    raio_analise_metros: int
    metodologia: str
    fonte: str
    atualizado_em: date | None
    periodo_inicio: datetime | None
    periodo_fim: datetime | None
    filtro_temporal_aplicado: bool


class RiskStatus(BaseModel):
    success: bool
    code: str
    message: str


class RiskData(BaseModel):
    status: RiskStatus
    result: RiskResult | None


class RouteOption(BaseModel):
    route: RouteResult
    risk: RiskData


class CalculateResponse(RouteOption):
    success: bool
    alternatives: list[RouteOption] = Field(default_factory=list)
    message: str


class ValhallaSummary(BaseModel):
    length: float = Field(ge=0, allow_inf_nan=False)
    time: float = Field(ge=0, allow_inf_nan=False)


class ValhallaLeg(BaseModel):
    shape: str = Field(min_length=1, max_length=200000)


class ValhallaTrip(BaseModel):
    summary: ValhallaSummary
    legs: list[ValhallaLeg] = Field(min_length=1, max_length=16)
