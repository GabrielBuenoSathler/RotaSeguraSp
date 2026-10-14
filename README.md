# RotaSeguraSP

Aplicação experimental para planejar trajetos e comparar a exposição a ocorrências registradas em São Paulo. Backend em FastAPI, SQLAlchemy e PostGIS; roteamento com Valhalla; frontend em React, TypeScript e Leaflet.

## Funcionalidades

- Origem e destino pelo mapa ou por coordenadas, busca por endereço, localização atual e inversão dos pontos.
- Trajeto principal e até duas alternativas, quando o Valhalla as disponibiliza.
- Seleção de cada trajeto para visualizar geometria, distância, duração e análise de ocorrências.
- Análise vinculada ao ID da rota calculada, inclusive em chamadas simultâneas.
- Fonte, atualização e período da base exibidos no resultado. Se a análise falhar, o trajeto continua disponível.

A busca por endereço exige uma instância própria ou um provedor compatível com Nominatim, configurado em `NOMINATIM_URL`. Sem essa configuração, mapa e coordenadas continuam disponíveis. A localização atual depende da permissão do navegador e de HTTPS em produção (localhost funciona no desenvolvimento).

## Desenvolvimento local

Requisitos: Python 3.13+, Poetry, Node.js 22+, PostgreSQL com PostGIS e Valhalla com mapas da região carregados.

1. Copie `.env.example` para `.env` e ajuste credenciais, banco e URL do Valhalla.
2. Garanta que o banco configurado exista e tenha a extensão PostGIS.
3. Instale as dependências, aplique as migrações e inicie a API:

```bash
poetry install --no-root
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

Frontend: http://localhost:5173. Documentação da API: http://localhost:8000/docs. Para mudar o endereço da API em desenvolvimento, copie `frontend/.env.example` para `frontend/.env`.

## Dados de ocorrências

A importação da base ainda é externa ao projeto; o Alembic não cria `ocorrencias_stg`. A tabela precisa conter:

| Coluna | Tipo esperado | Uso |
| --- | --- | --- |
| `rubrica` | texto | Classificação da ocorrência |
| `geog` | geography(Point, 4326), pode ser nula | Distância em metros |
| `geom` | geometry(Point, 4326), pode ser nula | Alternativa quando `geog` estiver nula |
| Coluna configurada em `OCCURRENCE_DATE_COLUMN` | date, timestamp ou timestamptz | Filtro temporal opcional |

Informe a fonte real em `DATASET_SOURCE` e a data da última importação em `DATASET_UPDATED_AT` (AAAA-MM-DD). Esses campos são metadados fornecidos pelo administrador.

Para identificar a coluna temporal sem adivinhar nomes:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'ocorrencias_stg';
```

Se os dados tiverem datas em texto, normalize-as na importação antes de ativar o filtro. Com `OCCURRENCE_DATE_COLUMN` configurada, entram apenas ocorrências entre o instante da análise menos `RISK_WINDOW_DAYS` e o instante da análise; datas nulas e futuras ficam fora. Sem a configuração, todas as datas entram e a interface informa que não existe filtro temporal.

## Metodologia experimental

A metodologia `exposicao-v2` usa um corredor de `RISK_RADIUS_METERS` ao redor da geometria do trajeto, com padrão de 50 metros. A consulta preserva `COALESCE(geog, geom::geography)`.

Os pesos por categoria seguem a regra existente: 5 para as categorias graves cadastradas na consulta; 3 para roubo, extorsão mediante sequestro e arma de fogo; 2 para lesão corporal e tráfico; 1 para furto e demais categorias. A classificação ainda depende do texto da rubrica.

A pontuação original soma os pesos. A pontuação ajustada multiplica cada peso pelo fator de proximidade:

| Distância até a rota | Fator | Exemplo com raio de 50 m |
| --- | --- | --- |
| Até 20% do raio | 1,00 | Até 10 m |
| Até 40% do raio | 0,75 | Mais de 10 até 20 m |
| Até 60% do raio | 0,50 | Mais de 20 até 30 m |
| Até 80% do raio | 0,25 | Mais de 30 até 40 m |
| Até 100% do raio | 0,10 | Mais de 40 até 50 m |

Essa regra muda os resultados em relação à versão anterior, na qual todas as ocorrências dentro de 50 metros tinham fator 1. Cada ocorrência é contada uma única vez por trajeto. Também são retornados pontos por quilômetro; para distância zero, o resultado por quilômetro é nulo.

Compare a pontuação total, a distância e a duração das opções. O trajeto principal continua selecionado inicialmente. Uma pontuação menor representa menor exposição às ocorrências presentes na base, sem validar probabilidade de vitimização. Falta de registros também pode refletir falta de cobertura dos dados.

## API

| Método | Endpoint | Resultado |
| --- | --- | --- |
| POST | `/rota/` | Cadastra origem, destino e transporte |
| POST | `/rota/{id}/calculate` | Calcula o trajeto, alternativas e análise de cada opção |
| GET | `/places?q=...` | Até cinco endereços no Brasil, via Nominatim configurado |
| GET | `/health` | Verifica se a aplicação responde; não verifica dependências |

O endpoint de cálculo mantém `route`, `risk`, `success` e `message`, acrescentando `alternatives` como uma lista de objetos com `route` e `risk`. Cada análise contém o seu `calculated_route_id`. Respostas inválidas do Valhalla retornam 502; timeout retorna 504. Falhas da análise retornam o trajeto com `risk.status.success=false`.

A geração das alternativas segue a [API oficial do Valhalla](https://valhalla.github.io/valhalla/api/route/api-reference/). A busca segue a [API Search do Nominatim](https://nominatim.org/release-docs/latest/api/Search/); utilize um provedor adequado ao volume de uso.

## Docker

O Compose utiliza a rede externa `crimes_sp_default` e espera PostgreSQL e Valhalla já disponíveis nessa rede. O PostgreSQL é acessado pelo nome `postgres_ocorrencias`; ajuste `VALHALLA_URL` no `.env` para o nome real do serviço de roteamento, por exemplo `http://criminalidade-valhalla:8002`.

```bash
docker compose build
docker compose run --rm backend alembic upgrade head
docker compose up -d
```

Frontend: http://localhost:3000. O Nginx encaminha `/api/` para o backend, portanto o navegador usa o mesmo domínio em produção. `VITE_API_URL` pode substituir esse caminho no build. O frontend aguarda o healthcheck da aplicação. Aplique HTTPS no serviço que publica o site.

O Compose não importa ocorrências nem prepara mapas do Valhalla. Sem a tabela de ocorrências, o cálculo do trajeto funciona e sua análise fica indisponível.

## Índices e desempenho

A migração de índices preservada no projeto cria um GiST para `COALESCE(geog, geom::geography)` e um índice de histórico por solicitação/data/ID. A análise agora encontra a rota diretamente pela chave primária.

Se `ocorrencias_stg` não existir durante a migração, crie o índice depois da importação:

```sql
CREATE INDEX IF NOT EXISTS ix_ocorrencias_stg_risk_geography
ON ocorrencias_stg USING gist ((COALESCE(geog, geom::geography)));
ANALYZE ocorrencias_stg;
```

A criação do índice pode bloquear escritas; programe-a conforme o tamanho da base. Compare `EXPLAIN (ANALYZE, BUFFERS)` em trajetos representativos para medir o ganho.

## Validação

```bash
poetry run pytest
poetry run ruff check app tests
poetry run ruff format --check app tests
cd frontend
npm run build
npm run lint
```

Os testes da API usam provedores e sessão simulados. Os testes marcados `postgis` executam a consulta espacial real. Para ativá-los, defina `TEST_DATABASE_URL` com uma URL SQLAlchemy `postgresql+asyncpg://...` de um banco com PostGIS e execute:

```bash
poetry run pytest -m postgis
```

Eles criam tabelas temporárias na própria conexão e desfazem as transações, sem alterar as tabelas existentes. Sem a variável, esses testes são pulados. O workflow de CI executa os testes com PostGIS, os checks Python e o build/lint do frontend.
