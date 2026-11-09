---
lang: pt-BR
topic: root-vs-no-root
title: "Root ou No-root para um launcher LG webOS"
description: "Escolha a edição do Clean Your TV adequada para sua LG webOS. Compare acesso, manutenção do Developer Mode, controle do Home e recuperação antes de instalar."
updated: '2026-11-09'
---

Escolha No-root se sua TV LG usa o Developer Mode. Escolha Root somente se ela já tiver acesso root funcionando e serviços compatíveis. As duas edições do Clean Your TV oferecem a mesma interface inicial e funcionam na TV após a instalação. O instalador não obtém acesso root nem grava firmware.

## O que o No-root exige?

O No-root usa LG Developer Mode, Key Server e pareamento local durante a configuração. O Home Helper funciona na TV e controla o botão Home quando o dispositivo e o firmware permitem. Você não precisa deixar um computador ou celular ligado para o uso diário.

O requisito contínuo é o Developer Mode: renove a sessão antes de expirar. A LG avisa que os aplicativos instalados pelo Developer Mode podem ser removidos quando ele é desativado ou a sessão expira. A renovação automática do projeto é um recurso beta opcional, desativado por padrão; não a considere uma garantia. Leia o [guia do Developer Mode](/clean-your-tv-lg-webos/pt-BR/articles/lg-developer-mode/) antes de depender dessa edição.

## O que o Root exige?

O Root usa acesso SSH root já existente, serviços de TV compatíveis e recursos de entrada e ambiente de execução suportados. O acesso root sozinho não comprova compatibilidade. O instalador verifica o ambiente; não contorne um pré-requisito rejeitado nem substitua ambientes de execução do sistema para forçar a aprovação.

O Root tem pacotes e direcionamento do Home próprios. Não ative o Developer Mode sobre uma configuração root existente e pare o Home Helper do No-root antes de usar o direcionamento do Root. A escolha da edição depende do acesso que você já tem, não de um botão que faria root na TV.

## Compare a manutenção e a recuperação

- **Uso diário:** as duas edições funcionam na TV, com aplicativos e temas no launcher.
- **Manutenção do No-root:** mantenha o Developer Mode ativo e preserve o pareamento e a conectividade exigidos pelo Helper.
- **Manutenção do Root:** mantenha disponíveis os serviços independentes de recuperação e o ambiente de execução necessário para eles. A disponibilidade de atualizações depende da edição instalada e do caminho de atualização suportado; o acesso root sozinho não habilita OTA.
- **Saída de emergência:** as edições atualmente suportadas usam três toques curtos no Home em até dois segundos. O Home Helper até a versão 0.6.13 usa, em vez disso, o botão pressionado por dois segundos.

Após uma parada de emergência, reiniciar o direcionamento persistente exige uma ação explícita. No No-root, abra o Home Helper e escolha “Start Helper”; no Root, use “Change Home” nas configurações de Home. Consulte a [comparação das edições](/clean-your-tv-lg-webos/pt-BR/editions/) e a [ajuda de recuperação](/clean-your-tv-lg-webos/pt-BR/help/#home-button).

## Verifique sua TV antes de instalar

Leia a [página de compatibilidade](/clean-your-tv-lg-webos/pt-BR/compatibility/) com o modelo exato, o firmware, o webOS e o controle remoto em mãos. Os resultados relatados pertencem a uma configuração específica. Teste separadamente o Home, a abertura de aplicativos, o som, o modo de espera e a inicialização a frio após configurar. A instalação de um pacote não comprova que tudo isso funciona.

Use o [instalador publicado e o guia de instalação](/clean-your-tv-lg-webos/pt-BR/install/). Se você já tem uma configuração que funciona e quer trocar de edição, siga os passos documentados de transição e remoção em vez de instalar uma por cima da outra.

## Fontes e próximos passos

- [Comparação das edições do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Requisitos e limites conhecidos do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [O que uma tela inicial diferente muda](/clean-your-tv-lg-webos/pt-BR/articles/change-lg-webos-home-screen/)
