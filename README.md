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

A ingestão por link da SSP está disponível em `scripts/ingest_ssp.py` (instruções abaixo). O Alembic não cria `ocorrencias_stg`. A tabela precisa conter:

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

## Ambientes dev, homolog e prod

Os ambientes em `deploy/` usam projetos Compose separados, cada um com seu próprio PostgreSQL/PostGIS, volume e rede. O Compose original continua disponível para a instalação que utiliza serviços externos.

Para acessar os bancos pelo host (por exemplo, no DBeaver), use `127.0.0.1` e as credenciais do arquivo `deploy/.env.<ambiente>`:

| Ambiente | Banco | Porta PostgreSQL |
| --- | --- | --- |
| dev | rotasegura_dev | 5441 |
| homolog | rotasegura_homolog | 5442 |
| prod | rotasegura_prod | 5443 |

`DATABASE_PORT` define a porta no host; entre containers o PostgreSQL continua na porta 5432. As cópias dos dados são independentes e não sincronizam alterações entre ambientes.

Requisitos: Python 3 para gerar as credenciais locais e Docker com Compose 2.24.4+ (suporte a `!override`). Execute na raiz do projeto:

```bash
# Repita para homolog e prod, trocando o nome do ambiente.
./scripts/env.sh dev init
# Edite deploy/.env.dev: senha e URLs dos serviços externos.
./scripts/env.sh dev migrate
./scripts/env.sh dev up
```

Se o arquivo do ambiente já existir, `init` o preserva e encerra sem sobrescrevê-lo. Os arquivos `deploy/.env.dev`, `deploy/.env.homolog` e `deploy/.env.prod` são locais e ignorados pelo Git; os modelos `.example` ficam versionados. `init` gera uma senha aleatória exclusiva para cada ambiente.

| Ambiente | APP_ENV | Frontend padrão | Backend |
| --- | --- | --- | --- |
| dev | development | http://localhost:5173 | http://localhost:8000, com recarga automática |
| homolog | staging | http://localhost:3001 | Acesso pelo proxy `/api` |
| prod | production | http://localhost:3000 | Acesso pelo proxy `/api` |

Dev usa Vite e recarrega alterações de frontend e backend. Homolog e prod compilam o frontend e o servem pelo Nginx. Os três podem funcionar simultaneamente. As portas ficam vinculadas ao host local; configure HTTPS em um proxy reverso para publicar homolog/prod. Ajuste `BIND_HOST` quando precisar expor o frontend em outra interface. `CORS_ORIGINS=[]` funciona com o proxy de mesma origem; configure origens explícitas para clientes web que acessem diretamente a API de dev.

```bash
./scripts/env.sh homolog migrate
./scripts/env.sh homolog up
./scripts/env.sh prod migrate
./scripts/env.sh prod up
./scripts/env.sh dev logs -f
./scripts/env.sh homolog ps
./scripts/env.sh prod down
```

`migrate` constrói a imagem, aguarda o banco e aplica as migrações. Execute antes do primeiro `up` e ao atualizar o esquema. `down` preserva o volume do banco. `config` permite validar a configuração; sua saída pode conter credenciais.

Valhalla continua externo: o padrão `http://host.docker.internal:8002` aponta para um serviço publicado no host Docker. Ajuste `VALHALLA_URL` e, se necessário, `NOMINATIM_URL` para serviços acessíveis aos contêineres. Importe separadamente os mapas e a tabela de ocorrências em cada ambiente; os bancos começam vazios e não copiam os dados da instalação existente. Ao mudar dependências do frontend de dev, execute `./scripts/env.sh dev deps` para atualizar o volume de módulos.

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

## Segurança da API e credenciais do banco

A criação de rota retorna `access_token` uma única vez. O cálculo exige
`Authorization: Bearer <access_token>` da mesma solicitação; o banco guarda somente
SHA-256 do segredo aleatório de 256 bits. Tokens ausentes, inválidos e IDs inexistentes
retornam 404. O frontend usa o segredo apenas durante o fluxo, sem persistência no
navegador. Rotas criadas antes da migração de segurança ficam inacessíveis pela API.
As respostas de rotas usam `Cache-Control: no-store`.

Cada processo da API permite 60 requisições por minuto por IP para criação/busca/cálculo,
com até 10 cálculos por minuto por IP, 600 requisições totais por minuto e quatro
requisições simultâneas nesses endpoints. Excessos retornam 429 e `Retry-After`.
As janelas são fixas; reiniciar o processo reinicia as cotas. Múltiplos workers/réplicas
exigem um limitador compartilhado no proxy ou Redis para manter cotas globais.
Consultas PostgreSQL têm `statement_timeout` de 15 segundos, configurável por
`DATABASE_STATEMENT_TIMEOUT_MS`. Geometrias retornadas pelo roteador também têm limites.

No Compose de `deploy/`, o backend fica privado e confia nos cabeçalhos do Nginx,
que substitui `X-Forwarded-For`. Não publique a porta do backend nessa configuração.
Um proxy adicional na frente do Nginx precisa de configuração explícita de IPs
confiáveis; sem isso, clientes desse proxy compartilham a mesma cota.

`POSTGRES_ADMIN_USER` e `POSTGRES_ADMIN_PASSWORD` pertencem exclusivamente ao banco
e ao serviço temporário `migrate`. `POSTGRES_USER` e `POSTGRES_PASSWORD` identificam
um usuário diferente, restrito à aplicação. O backend não recebe os segredos administrativos.
`init` gera senhas independentes. Para volumes existentes, mantenha nas variáveis
administrativas as credenciais que inicializaram o volume e escolha uma identidade
nova para a aplicação; mudar variáveis não altera a senha de um usuário já existente.

Para aplicar em cada ambiente, depois de conferir suas credenciais locais:

```bash
./scripts/env.sh prod migrate
./scripts/env.sh prod up
```

`migrate` aplica o Alembic como administrador e provisiona o usuário restrito.
Esse usuário pode consultar as tabelas de rotas e ocorrências e inserir solicitações
e resultados; não pode administrar o PostgreSQL, criar tabelas ou apagar registros.
Depois de importar/recriar `ocorrencias_stg`, execute `./scripts/env.sh prod db-access`
para conceder leitura à tabela. A rotina recusa usuários administrativos ou com objetos
próprios, em vez de rebaixar uma identidade existente.

O Compose antigo exige `BACKEND_ENV_FILE` com somente configurações da aplicação,
`POSTGRES_APP_USER` e `POSTGRES_APP_PASSWORD` de um usuário já provisionado no banco
externo. Migrações nesse banco devem ser aplicadas separadamente com credenciais
administrativas. O fluxo automatizado de migração/provisionamento pertence a `deploy/`.

A análise retorna `riscos_por_crime`, agrupada pela rubrica da base (sem distinguir maiúsculas ou espaços nas extremidades). Cada tipo inclui quantidade de ocorrências, pontuações original e ajustada e pontos por quilômetro, com os mesmos pesos, raio e período do total. A lista é ordenada pela pontuação ajustada decrescente e aparece para o trajeto selecionado, incluindo alternativas. Sem ocorrências, a lista fica vazia; com distância zero, pontos por quilômetro são nulos. Não se trata de probabilidade de vitimização.

### Ocorrências por mês

Configure `OCCURRENCE_GROUP_DATE_COLUMN=data_ocorrencia_bo` para categorizar os registros pela data em que ocorreram, independentemente da data de registro do boletim. A coluna deve ser `date` ou `timestamp`. A resposta de cada rota inclui `ocorrencias_por_mes`, com totais, pontuação de exposição e crimes de cada mês. Datas ausentes ficam em “Data não informada”; os totais são preservados.

Na interface, use “Data das ocorrências” no painel de crimes para consultar um mês. Esse seletor altera apenas a lista detalhada da rota selecionada; os cartões continuam comparando todo o período analisado. O agrupamento não ativa a janela de `RISK_WINDOW_DAYS`: esse filtro continua dependendo de `OCCURRENCE_DATE_COLUMN`.


## Ingestão automática por link da SSP

O script baixa a planilha XLSX diretamente da SSP. Com o link da página de consultas,
consulta o catálogo oficial e seleciona **Dados criminais** pelo ano informado.
Também aceita o link HTTPS direto de uma planilha compatível, via `--url`.
As abas de documentação são ignoradas; todas as abas de dados são processadas.

O ambiente `test` tem container, banco e volume próprios, separados de dev/homolog/prod.
A tabela de testes usa o esquema de `ocorrencias_stg` e inicia vazia, com PostGIS e pg_trgm.

```bash
poetry install
# O arquivo local já existe nesta instalação. Em uma instalação nova:
# cp deploy/.env.test.example deploy/.env.test
# Edite POSTGRES_ADMIN_PASSWORD com uma senha própria antes de iniciar.
docker compose -p rotasegura-test --env-file deploy/.env.test -f deploy/compose.test.yaml up -d --build --wait db

# Download automático e teste de inserção de uma amostra real:
poetry run python scripts/ingest_ssp.py --ano 2026 --target test --limit 100
# Repetir o comando permite conferir que linhas idênticas não são reinseridas.

# Simular a carga de São Paulo, sem inserir:
poetry run python scripts/ingest_ssp.py --ano 2026 --target test --municipio-ibge 3550308 --dry-run

# Carregar o ano inteiro no banco de testes (sem --limit):
poetry run python scripts/ingest_ssp.py --ano 2026 --target test

# Depois da validação, carregar em dev:
poetry run python scripts/ingest_ssp.py --ano 2026 --target dev

# Testes de conversão e integração real (os registros artificiais sofrem rollback):
SSP_TEST_DATABASE=1 poetry run pytest tests/test_ssp_ingestion.py -q
```

Destino padrão: `test`. Banco de testes: `rotasegura_test`, em `127.0.0.1:5444`;
credenciais em `deploy/.env.test`. Dev usa `deploy/.env.dev`.
O importador permite apenas test/dev e conecta como administrador para carregar os dados.
`--limit` só é permitido em test; sem filtro de município, inclui todo o estado.

A carga é transacional: falhas de leitura, validação ou inserção desfazem a carga inteira.
O relatório mostra linhas lidas, novas, duplicadas e inseridas. A comparação usa as
30 colunas originais: linhas idênticas, inclusive já presentes no banco, não são
reinseridas. Uma linha alterada na fonte é adicionada como nova, sem atualizar ou
excluir a versão anterior. Execuções deste importador são serializadas no banco.
As coordenadas ausentes/zeradas ficam sem `geom`/`geog`; valores inválidos ou fora dos limites
geográficos são convertidos em nulos, sem ponto, e contabilizados no log. Datas, inteiros e valores nulos são normalizados.
Os campos `id`, `geom`, `geog` e `bairro_normalizado` são gerados durante a inserção.
Após uma carga em dev, atualize os metadados `DATASET_SOURCE` e `DATASET_UPDATED_AT`
da aplicação conforme a fonte e a data efetivas.

Cada execução baixa a versão atual da planilha; o script não instala um agendamento.
O volume de testes é preservado ao parar o Compose. As planilhas temporárias são
removidas ao terminar, inclusive em caso de falha.

### Completar produção a partir do banco de testes

`scripts/merge_ssp_prod.py` lê a maior data presente em `rotasegura_prod` e seleciona
somente linhas de `rotasegura_test` com data estritamente posterior ao corte.
Escolha explicitamente `data_registro` ou `data_ocorrencia_bo`:

```bash
# Simulação; não altera produção:
poetry run python scripts/merge_ssp_prod.py --date-column data_registro
# Aplicação; salva um backup da tabela em backups/ antes da inserção:
poetry run python scripts/merge_ssp_prod.py --date-column data_registro --apply
```

A operação acrescenta linhas, preserva os registros existentes e usa a mesma
comparação contra duplicatas e transação do importador. Registros do período
anterior ao corte, inclusive novas correções nesse período, não são incorporados.
O destino é exclusivamente `rotasegura_prod`; o banco original `Criminalidade`
não é alterado por esse comando. Datas nulas não participam do corte.
