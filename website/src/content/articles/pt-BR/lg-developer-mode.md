---
lang: pt-BR
topic: lg-developer-mode
title: "LG Developer Mode para um launcher webOS No-root"
description: "Entenda por que o Clean Your TV No-root precisa do LG Developer Mode, como a expiração da sessão afeta os aplicativos e o que verificar se o launcher desaparecer."
updated: '2026-11-09'
---

O LG Developer Mode permite instalar e testar aplicativos de TV webOS sem fazer root no aparelho. O Clean Your TV No-root usa esse método de acesso junto com o Home Helper, que funciona na própria TV. O Developer Mode tem uma sessão com prazo limitado: confira o tempo restante no aplicativo Developer Mode da LG e renove antes de expirar para manter sua configuração disponível.

## O que o Developer Mode oferece?

O Developer Mode fornece acesso para desenvolvimento; ele não concede privilégios root nem garante que um auxiliar do botão Home funcione em todos os modelos. O Clean Your TV ainda verifica os requisitos de ambiente de execução e de entrada. Aplicativos comuns da loja, aplicativos instalados pelo modo de desenvolvimento e um sistema com root têm formas de acesso diferentes.

Use No-root somente em uma configuração apropriada do Developer Mode. Se a TV já tiver root, não ative o Developer Mode sobre essa configuração. Leia primeiro [Root e No-root](/clean-your-tv-lg-webos/pt-BR/articles/root-vs-no-root/) e os [requisitos de compatibilidade](/clean-your-tv-lg-webos/pt-BR/compatibility/).

## Prepare a TV e o dispositivo de instalação

Siga o [guia de instalação atual](/clean-your-tv-lg-webos/pt-BR/install/) para ver os passos exatos. Você precisará do aplicativo Developer Mode da LG, do login de desenvolvedor LG exigido e do Key Server para o pareamento. A TV e o computador ou dispositivo Android compatível precisam estar em uma rede que permita a comunicação entre eles. Uma rede de convidados ou o isolamento de clientes pode impedir a configuração mesmo que os dois dispositivos tenham acesso à internet.

Mantenha as chaves de pareamento e os dados de conexão privados. Use o instalador publicado no guia, em vez de considerar o download de um IPK qualquer como uma configuração completa do Home. Quando a instalação terminar, o launcher e o Helper funcionarão na TV; o computador poderá ser desligado.

## Mantenha a sessão ativa

Abra o aplicativo Developer Mode da LG, confira o tempo restante da sessão e renove enquanto a conexão necessária estiver disponível. Siga as instruções atuais da LG, em vez de confiar em uma quantidade fixa de horas citada em um artigo antigo. Uma tentativa de renovação não comprova sucesso: confira o tempo restante exibido depois.

O Clean Your TV oferece renovação automática opcional como recurso beta, desativado por padrão. Se você ativar esse recurso, continue verificando o estado real do Developer Mode. Ele não elimina os requisitos de sessão da LG nem torna permanente um modo desativado.

## E se o launcher desaparecer ou Home abrir o LG Home?

Verifique o Developer Mode antes de reinstalar repetidamente. A LG documenta que desativar o Developer Mode ou deixar a sessão expirar pode desinstalar os aplicativos de desenvolvimento. Uma sessão expirada é diferente de uma parada de emergência do Home Helper, de um problema de pareamento ou de uma instalação interrompida.

Se os aplicativos de desenvolvimento foram removidos, restaure o Developer Mode conforme a documentação e use a configuração guiada ou a recuperação do instalador adequada ao estado real. Se os aplicativos continuarem instalados, mas o direcionamento do Home estiver parado, siga a [ajuda do botão Home](/clean-your-tv-lg-webos/pt-BR/help/#home-button). Para operações interrompidas, use o [guia de recuperação](/clean-your-tv-lg-webos/pt-BR/help/#interrupted) em vez de apagar arquivos do sistema. Verifique o comportamento do Home separadamente após a recuperação.

## Fontes e próximos passos

- [LG: como usar o aplicativo Developer Mode](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [Guia de instalação No-root do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Referência de recuperação do projeto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
