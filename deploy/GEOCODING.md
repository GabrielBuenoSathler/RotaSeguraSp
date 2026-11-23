# Identificação de ruas e busca de endereços

A identificação dos pontos no mapa usa `/places/reverse`; a busca por endereço
usa `/places`. Ambas dependem de `FEATURE_GEOCODING=true` e de `NOMINATIM_URL`
apontando para um serviço compatível com Nominatim. O Valhalla continua sendo
usado para calcular os trajetos.

## Configuração de testes na VPS

O uso do Nominatim público foi escolhido para os testes deste projeto. Em
`deploy/.env.prod`, a configuração é:

```dotenv
FEATURE_GEOCODING=true
NOMINATIM_URL=https://nominatim.openstreetmap.org
GEOCODER_USER_AGENT="RotaSeguraSP/0.1 (https://rota-segura-sp-git-main-gabrielbuenosathlers-projects.vercel.app)"
```

Esse provedor recebe as coordenadas e os endereços consultados. A
[política de uso](https://operations.osmfoundation.org/policies/nominatim/)
limita o aplicativo inteiro a uma consulta por segundo, exige identificação e
atribuição ao OpenStreetMap e proíbe autocomplete. Não envie dados confidenciais.
O frontend atual faz buscas por envio do formulário e identifica pontos apenas
quando selecionados pelo usuário; a atribuição aparece no mapa.

O backend serializa as consultas com intervalo mínimo de 1,05 segundo e mantém
até 512 respostas em cache por uma hora. Essa proteção é por processo: mantenha
um único worker e uma única instância consultando esse provedor público. Antes
de escalar, use um provedor adequado ao volume ou coordene os limites e o cache
entre todas as instâncias. O serviço público não oferece garantia de latência
ou disponibilidade.

Depois de alterar o ambiente, recrie apenas o backend:

```bash
docker compose -p rotasegura-prod --env-file deploy/.env.prod \
  -f deploy/compose.yaml up -d --no-deps --no-build --wait backend
```

Para ambientes com releases versionados, reaplique o release conforme
`deploy/RELEASES.md`, preservando suas imagens fixadas.

Verifique a configuração pública:

```bash
curl https://api.smartgado.com.br/features
```

O campo `geocoding` deve ser `true`. Recarregue o frontend para que ele consulte
essa configuração novamente; a URL pública da API na Vercel continua a mesma.
O provedor pode ser trocado alterando `NOMINATIM_URL` e recriando o backend.

Se o provedor estiver desativado, os pontos ainda permitem calcular trajetos.
O frontend deve mostrar “Ponto selecionado no mapa”, sem indicar uma busca em
andamento.
