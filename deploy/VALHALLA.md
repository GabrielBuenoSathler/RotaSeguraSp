# Valhalla na VPS com mapas locais

O serviço usa os mapas já gerados para o Sudeste e a mesma imagem do Valhalla
3.9.1 da instalação local. A imagem está fixada por digest para preservar a
compatibilidade com esses mapas. A documentação oficial está em
[Valhalla Docker](https://github.com/valhalla/valhalla/blob/master/docker/README.md).

O ambiente de produção precisa estar iniciado, com a rede
`rotasegura-prod_default` disponível. Copie para `custom_files/` na VPS:

- `valhalla_tiles.tar`
- `admins.sqlite`
- `timezones.sqlite`
- `default_speeds.json`
- `valhalla.json`

O `valhalla.json` deve usar os caminhos `/custom_files/` para esses arquivos e
escutar na porta 8002. Não é necessário copiar o PBF nem os tiles descompactados.
Não versione os mapas; `custom_files/` já está no `.gitignore`.

Execute na raiz do repositório na VPS:

```bash
docker compose -p rotasegura-routing -f deploy/compose.valhalla.yaml up -d --wait
```

O serviço compartilha a rede da aplicação, tem reinício automático e limite de
memória de 2 GiB. A porta 8002 fica disponível somente para os containers nessa
rede. `VALHALLA_THREADS` permite ajustar o número de workers, com padrão 2;
`VALHALLA_DOCKER_NETWORK` permite escolher outra rede existente.

Em `deploy/.env.prod`, configure:

```dotenv
VALHALLA_URL=http://valhalla:8002
```

Recrie somente o backend para carregar o novo endereço. Para o deploy por Compose:

```bash
docker compose -p rotasegura-prod --env-file deploy/.env.prod \
  -f deploy/compose.yaml up -d --no-deps --no-build backend
```

Se o ambiente usa releases versionados, reaplique o release pelo procedimento
de `deploy/RELEASES.md` para carregar a variável, preservando as imagens fixadas.

Para consultar o estado e os logs:

```bash
docker compose -p rotasegura-routing -f deploy/compose.valhalla.yaml ps
docker compose -p rotasegura-routing -f deploy/compose.valhalla.yaml logs --tail 50
```

O healthcheck confirma que o serviço responde. Para validar também os mapas,
calcule uma rota pelo backend e confira se a análise das ocorrências retornou.
