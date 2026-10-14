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
            "A busca por endereço está indisponível. Informe as coordenadas ou selecione no mapa.",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Não foi possível consultar os endereços.") from exc
