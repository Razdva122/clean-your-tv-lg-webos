---
lang: pt-BR
topic: change-lg-webos-home-screen
title: "Como mudar a tela inicial de uma TV LG webOS"
description: "Personalize a tela inicial da sua LG webOS com o Clean Your TV. Entenda o que um launcher muda, como escolher a edição e o que verificar antes de instalar."
updated: '2026-11-09'
---

O Clean Your TV é uma tela inicial alternativa para TVs LG webOS. Ele organiza os aplicativos na ordem que você preferir e oferece temas e um dock personalizável. Após a configuração, ele funciona na própria TV, então você pode desligar o computador. A possibilidade de controlar o botão Home depende da TV, do firmware, do controle remoto e do método de instalação.

## O que você pode personalizar?

O launcher muda a tela usada para encontrar e abrir os aplicativos da TV. Você pode organizar os favoritos e escolher um layout como Classic, Liquid Glass ou Ribbon. Experimente a [demonstração no navegador](/clean-your-tv-lg-webos/demo/) para comparar os layouts antes de instalar qualquer coisa. Os controles da TV são simulados na demonstração; ela não testa a compatibilidade com o seu aparelho.

Um launcher alternativo não substitui o firmware do webOS, não libera streaming pago e não remove anúncios dentro de outros aplicativos. As configurações de imagem, as entradas e os serviços de streaming continuam sendo partes separadas da TV. Leia [o que muda em relação aos anúncios](/clean-your-tv-lg-webos/pt-BR/articles/lg-tv-home-screen-ads/) se o seu principal objetivo é uma tela inicial mais tranquila.

## Qual método de instalação escolher?

Use No-root em uma TV com o LG Developer Mode ativo. O Home Helper, que funciona na própria TV, controla o botão Home quando há suporte. O Developer Mode precisa continuar ativo; sessões expiradas podem causar a remoção dos aplicativos instalados por esse modo.

Use Root somente se a TV já tiver acesso root funcionando e atender aos requisitos de ambiente de execução e serviços. O instalador do Clean Your TV não faz root na TV. Não ative o Developer Mode sobre uma configuração root existente nem use os dois métodos de direcionamento do Home ao mesmo tempo. O [guia das edições](/clean-your-tv-lg-webos/pt-BR/articles/root-vs-no-root/) explica as diferenças.

## Antes de mudar uma configuração que funciona

1. Anote o modelo exato, o firmware, a versão do webOS e o tipo de controle remoto. Compare esses dados com os [requisitos e resultados relatados em TVs](/clean-your-tv-lg-webos/pt-BR/compatibility/); cada relato se aplica à configuração registrada nele.
2. Siga o [guia de instalação](/clean-your-tv-lg-webos/pt-BR/install/) e use o instalador publicado no link indicado. Durante a configuração, a TV e o dispositivo com o instalador precisam estar em uma rede que permita a comunicação entre eles.
3. Após configurar, verifique a abertura de aplicativos e o Home; depois teste separadamente o som, a entrada e saída do modo de espera e a inicialização a frio. Instalar um pacote com sucesso não verifica esses comportamentos.

## Como voltar ao LG Home?

Nas edições atualmente suportadas, três toques curtos no Home em até dois segundos acionam a saída de emergência. Versões antigas do Home Helper até a 0.6.13 usam o Home pressionado por dois segundos. Abrir o LG Home uma vez e desativar o direcionamento persistente do Home são ações diferentes; siga as [instruções de recuperação](/clean-your-tv-lg-webos/pt-BR/help/#home-button) da edição instalada. Mantenha uma forma de recuperação disponível antes de mudar o comportamento de inicialização.

## Fontes e próximos passos

- [Referência de edições e controles do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Instalação e pré-requisitos do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: como manter uma configuração No-root disponível](/clean-your-tv-lg-webos/pt-BR/articles/lg-developer-mode/)
