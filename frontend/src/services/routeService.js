const API_URL = import.meta.env.VITE_API_URL;

export async function calculateRoute(routeRequestId) {
  const response = await fetch(
    `${API_URL}/rota/${routeRequestId}/calculate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      data?.detail?.message ||
      data?.detail ||
      "Não foi possível calcular a rota."
    );
  }

  return data;
}
