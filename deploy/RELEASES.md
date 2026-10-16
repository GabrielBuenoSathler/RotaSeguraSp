# Releases na VPS

O workflow `.github/workflows/ci.yml` valida pushes e PRs. Somente um push aprovado
na branch padrão publica as imagens `backend` e `frontend` no GHCR, com tag
`sha-<SHA completo>` e o rótulo OCI do commit. As imagens são construídas em jobs
separados com cache BuildKit. O workflow prepara os artefatos; o deploy na VPS é
acionado pelo operador, sem guardar uma chave SSH no CI.

Requisitos: VPS Linux x86-64, Docker com Compose 2.24.4+, Python 3 e acesso às
imagens do repositório. O workflow atual produz imagens `linux/amd64`.
Em repositórios com políticas restritas, permita ao workflow publicar packages;
para imagens privadas, autentique a VPS com `docker login ghcr.io` usando uma
credencial com permissão de leitura de packages. Não inclua tokens no `.env` da aplicação.

## Primeira instalação

Copie o repositório para um diretório permanente na VPS. Mantenha os scripts e o
Compose na versão correspondente ao release que será instalado. Inicialize o
ambiente e ajuste URLs, credenciais, metadados da base e flags:

```bash
./scripts/env.sh prod init
# Edite deploy/.env.prod antes de continuar.
```

O arquivo é preservado se já existir. O banco é PostgreSQL/PostGIS 17, com volume
próprio. Valhalla, mapas e dados de ocorrências precisam ser disponibilizados
separadamente. Configure o domínio/HTTPS no proxy externo; mantenha a API privada.

Espere os dois jobs de imagens terminarem no GitHub Actions. Use o SHA completo
da execução aprovada, não o SHA sintético de uma PR. Neste repositório:

```bash
RELEASE_SHA='SHA_COMPLETO_APROVADO_NO_CI'

# Inicialização ou mudança de esquema: operação explícita sobre o banco.
python3 scripts/release.py prod migrate \
  --registry ghcr.io/gabrielbuenosathler/rotasegurasp --version "$RELEASE_SHA"

# Importar ocorrências é uma etapa separada; depois da importação:
./scripts/env.sh prod db-access

python3 scripts/release.py prod deploy \
  --registry ghcr.io/gabrielbuenosathler/rotasegurasp --version "$RELEASE_SHA"
```

`migrate` inicializa o banco quando necessário, aplica Alembic com a imagem alvo
e provisiona o usuário restrito. Em uma instalação existente, faça backup antes
de alterar o esquema e confira sua compatibilidade com a aplicação em uso.

`deploy` baixa as duas imagens, confere os rótulos do commit e grava referências
por digest SHA256. Ele verifica se o Alembic da imagem e o banco têm as mesmas
revisões antes de substituir os serviços. Apenas frontend e backend são trocados;
o comando não reconstrói imagens, não recria o banco e não executa migrações.
Os dois containers da aplicação são recriados mesmo ao reaplicar a mesma versão,
para que o Nginx resolva novamente o endereço do backend após mudanças nas flags.

## Atualização e rollback

Teste primeiro em `homolog`, substituindo `prod` nos comandos. Para atualizar,
repita `deploy` com o próximo SHA aprovado. Execute `migrate` separadamente somente
quando necessário. A versão passa a ser considerada ativa depois dos healthchecks
da API, da página inicial e de `/api/health` através do Nginx.

```bash
python3 scripts/release.py prod status
python3 scripts/release.py prod rollback
```

O rollback usa os digests registrados da versão anterior, mesmo que uma tag seja
alterada no registry. Se as imagens já estiverem locais, não precisa baixá-las.
Mantenha as versões anteriores no registry e evite removê-las da VPS sem necessidade.

Se uma atualização falhar nos healthchecks, o script tenta restaurar a última
versão ativa. Se o processo for interrompido ou a restauração falhar, o estado
fica marcado como pendente; `rollback` tenta recuperar a última versão saudável.
Um lock impede dois comandos de release simultâneos no mesmo diretório/ambiente.

O estado fica em `.releases/<ambiente>.json`, fora do Git e do contexto Docker.
Preserve esse diretório entre atualizações e restrinja sua escrita ao operador.
`env.sh logs`, `ps`, `down` e `db-access` continuam disponíveis; `up`, `build` e
`migrate` são bloqueados depois que o ambiente passa a usar releases.

## Limites do procedimento

- O primeiro deploy gerenciado ainda não tem versão anterior registrada; ele
  não captura automaticamente containers de uma instalação antiga. Faça essa
  transição em janela de manutenção e mantenha uma forma de restaurar a instalação anterior.
- Rollback troca as imagens da aplicação. Não restaura `.env`, Compose, dados,
  PostgreSQL ou mapas. Mudanças de configuração precisam continuar compatíveis.
- Uma revisão Alembic diferente bloqueia o rollback, mesmo que a mudança pareça
  aditiva. Não há `downgrade` automático. Mudanças de esquema precisam de um plano
  próprio de compatibilidade e restauração; prefira correção progressiva quando possível.
- Os healthchecks não garantem acesso ao Valhalla/Nominatim nem análise de dados.
  Depois do deploy, teste uma rota completa e a busca de endereços, quando habilitada.
- Compose substitui os containers no mesmo conjunto de portas. Há possibilidade
  de breve interrupção; este fluxo não oferece deploy sem downtime.

Referências: [imagens no GitHub Actions](https://github.com/docker/build-push-action),
[espera por saúde no Compose](https://docs.docker.com/reference/cli/docker/compose/up/)
e [remoção de build no override](https://docs.docker.com/reference/compose-file/merge/).
