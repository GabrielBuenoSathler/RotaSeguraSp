from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.geocoding import GeocodingService, GeocodingUnavailableError, Place

router = APIRouter(prefix="/places", tags=["Endereços"])


@router.get("", response_model=list[Place])
async def search_places(q: Annotated[str, Query(min_length=3, max_length=200)]):
    query = q.strip()
    if len(query) < 3:
        raise HTTPException(422, "Informe pelo menos três caracteres do endereço.")
    try:
        return await GeocodingService.search(query)
    except GeocodingUnavailableError as exc:
        raise HTTPException(
            503,
            "A busca por endereço está indisponível. Selecione um ponto no mapa ou tente novamente.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Não foi possível consultar os endereços.") from exc


@router.get("/reverse", response_model=Place | None)
async def reverse_place(
    lat: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)],
    lon: Annotated[float, Query(ge=-180, le=180, allow_inf_nan=False)],
):
    try:
        return await GeocodingService.reverse(lat, lon)
    except GeocodingUnavailableError as exc:
        raise HTTPException(503, "A identificação da rua está indisponível.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            502, "Não foi possível identificar a rua deste ponto."
        ) from exc
