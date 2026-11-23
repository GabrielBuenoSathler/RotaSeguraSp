# RotaSeguraSP

**Compare trajetos em São Paulo com informações sobre as ocorrências registradas perto do caminho.**

O RotaSeguraSP é um site que reúne mapa, opções de trajeto e dados de ocorrências
criminais em uma mesma tela. Você informa de onde quer sair e aonde quer chegar,
e pode comparar a distância, o tempo estimado e os registros próximos de cada
percurso.

A proposta é oferecer mais contexto para escolher um caminho. A análise é
experimental: ela compara registros de uma base de dados e não representa a
probabilidade de sofrer um crime.

## O que você pode fazer

- **Escolher a origem e o destino:** clicando no mapa ou buscando um endereço.
- **Usar sua localização atual:** com a sua autorização no navegador.
- **Escolher como vai se deslocar:** de carro, de bicicleta, a pé ou de motocicleta.
- **Comparar caminhos:** visualizar o trajeto principal e até duas alternativas, quando disponíveis.
- **Ver distância e duração estimada:** entender quanto cada opção exige de deslocamento.
- **Consultar ocorrências próximas:** ver a quantidade e os tipos de registros considerados na análise.
- **Explorar o mapa de calor:** observar onde esses registros se concentram.
- **Filtrar a visualização:** selecionar grupos de crimes e meses para explorar os dados.

A busca por endereço e a identificação dos nomes das ruas dependem do serviço
de endereços estar habilitado. A seleção de pontos no mapa continua disponível
mesmo sem esse recurso.

## Como usar

Não é necessário instalar um aplicativo para usar uma versão do site já publicada:
basta abrir o endereço no navegador.

1. **Defina a origem.** Clique no mapa, busque um endereço ou escolha “Usar minha localização”.
2. **Defina o destino.** Escolha o lugar aonde deseja chegar.
3. **Selecione o transporte.** As opções são carro, bicicleta, a pé e motocicleta.
4. **Clique em “Calcular rota”.** O site calcula o trajeto e analisa os registros próximos.
5. **Explore o resultado.** Veja o caminho no mapa e consulte suas informações.
6. **Compare as alternativas.** Quando houver outras opções, abra “Ver alternativas de trajeto” e selecione uma delas.

Ao escolher outra rota, o mapa e a análise passam a mostrar os dados daquela
opção. Você também pode inverter origem e destino ou limpar os pontos para
começar uma nova busca.

## Um exemplo de uso

Imagine um deslocamento de casa para o trabalho. Um dos caminhos pode ser mais
curto, enquanto outro passa perto de menos ocorrências registradas.

O RotaSeguraSP apresenta essas diferenças lado a lado. Assim, você pode observar
o tempo de viagem, a distância e a análise das ocorrências antes de escolher qual
trajeto quer visualizar.

As alternativas dependem das ruas e do meio de transporte escolhido. Por isso,
nem toda busca terá a mesma quantidade de opções.

## Como funciona a análise

Depois que você escolhe os pontos, o sistema realiza quatro etapas:

1. **Calcula os caminhos possíveis** usando os dados das ruas disponíveis no mapa.
2. **Consulta a base de ocorrências** para encontrar registros próximos de cada trajeto.
3. **Calcula uma pontuação de exposição**, considerando o tipo de ocorrência e sua distância até o caminho.
4. **Apresenta a comparação** com os trajetos, seus indicadores e o mapa de calor.

Por padrão, são consideradas ocorrências a até **50 metros do trajeto**. Esse
alcance pode ser ajustado na configuração da instalação.

Os tipos de ocorrência recebem pesos diferentes. Além disso, um registro mais
próximo do caminho tem maior contribuição na pontuação ajustada do que um
registro mais distante. Por esse motivo, contar ocorrências e comparar pontuações
são duas formas diferentes de olhar para o resultado.

## Entendendo os resultados

| Informação | O que significa |
| --- | --- |
| Distância | O tamanho do percurso, em quilômetros. |
| Tempo estimado | A duração calculada para o transporte escolhido. |
| Quantidade de ocorrências | Quantos registros da base foram encontrados perto daquele trajeto. |
| Pontuação de exposição | Um indicador experimental que considera os pesos dos registros próximos. A pontuação ajustada também considera a proximidade ao caminho. |
| Pontos por quilômetro | A pontuação dividida pela distância, para ajudar a comparar percursos de tamanhos diferentes. |
| Índice de equilíbrio | Uma comparação entre tempo e exposição que ajuda a sugerir uma opção entre os trajetos da mesma busca. |

Uma pontuação de exposição menor significa menor exposição **aos registros
considerados naquela análise**. Ela não significa que o caminho seja livre de
crimes.

O índice de equilíbrio também não é uma porcentagem de segurança. Ele serve
para comparar as opções daquela busca, e não trajetos de buscas diferentes.

### O mapa de calor

O mapa de calor mostra a concentração dos registros próximos da rota selecionada.
As ocorrências são agrupadas em pequenas áreas; regiões com maior intensidade
representam maior concentração de registros.

Você pode ligar ou desligar três grupos:

- **Violência contra a pessoa:** inclui, por exemplo, lesão corporal, homicídio e estupro.
- **Assaltos, roubos e arrombamentos.**
- **Outros crimes:** reúne as demais categorias, incluindo furtos.

O calor do mapa representa a quantidade de registros agrupados, não a pontuação
ponderada da rota. A classificação depende de como cada ocorrência está descrita
na base.

O filtro por mês permite explorar os registros de um período na visualização.
Ele não refaz a comparação geral dos trajetos: os indicadores das rotas continuam
considerando o período completo definido para aquela análise.

## De onde vêm as informações?

O projeto combina três conjuntos de informações:

| Informação | Para que serve |
| --- | --- |
| Dados de ruas e mapas do OpenStreetMap | Permitem mostrar o mapa, identificar endereços e calcular os caminhos. |
| Base de ocorrências importada para o projeto | Fornece os registros usados na comparação dos trajetos. O projeto possui um importador para as planilhas da SSP de São Paulo. |
| Origem, destino e transporte escolhidos por você | Definem quais trajetos serão calculados e comparados. |

O nome da fonte, a atualização informada para a base e o período considerado
podem ser consultados no resultado. Esses dados são configurados por quem mantém
a instalação.

Os registros não são um acompanhamento de crimes em tempo real. Os resultados
dependem do conteúdo, da cobertura e da atualização da base importada. Uma região
com poucos registros também pode ter dados incompletos.

## O que considerar ao comparar

Use a distância, o tempo, a pontuação e o mapa em conjunto. O RotaSeguraSP não
leva em conta fatores como fluxo de pessoas, iluminação, presença policial ou
mudanças nas condições da rua em tempo real.

Se a análise de ocorrências estiver indisponível, o trajeto ainda pode ser
exibido, mas não deve ser interpretado como um caminho sem ocorrências.

## Documentação técnica

Para instalar, configurar ou manter o projeto, consulte o
[Guia técnico](docs/GUIA_TECNICO.md).

As configurações específicas também estão documentadas:

- [Serviço de rotas e mapas: Valhalla](deploy/VALHALLA.md).
- [Busca de endereços e identificação de ruas](deploy/GEOCODING.md).
- [Publicação e atualização na VPS](deploy/RELEASES.md).
