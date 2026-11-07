# Clean Your TV — guia de uso

Clean Your TV oferece uma tela inicial pessoal para sua LG webOS: seus apps na sua ordem, sem linhas patrocinadas neste menu. Instale pelo computador ou por um celular Android; depois o computador pode ficar desligado.

## Candidato UNRELEASED: Node.js antigo na TV

Estas opções pertencem a um candidato ainda não publicado, não aos downloads publicados. Se Root normal rejeitar a versão do Node.js da TV (exige Node.js 8+), o instalador pode oferecer **No-root usando o SSH root existente**: Home e Home Helper sem instalar Developer Mode. Nunca ative Developer Mode sobre um root existente. Somente **Node.js exatamente 0.12.2** permite oferecer também **Root Beta**, com pacotes separados e confirmação explícita. O Node.js do sistema não é substituído e não há atualizações automáticas/OTA; use o instalador do computador. No-root tem funcionalidade reduzida: sem redirecionamento do Home do sistema nem controles exclusivos do Root. Root Beta não foi testado suficientemente em TVs.

Os demais requisitos nativos, de interfaces Home e de Python continuam obrigatórios. Os testes físicos supervisionados pelo proprietário ainda não foram realizados; isto não confirma compatibilidade. Salve o relatório de diagnóstico, marque testes não realizados e compartilhe voluntariamente um resultado sem dados privados, manualmente, pelo [guia de feedback](../FEEDBACK.md). Nada é publicado automaticamente.

## 1. Baixe o instalador

Toque na imagem do seu dispositivo. Os botões baixam a versão publicada mais recente. No Mac, escolha Apple Silicon (M1 ou mais recente) ou Intel; confira no menu Apple → Sobre Este Mac.

[![Baixar — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Baixar — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Baixar — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Baixar — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Baixar — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="escolher-a-edição"></a>

<a id="requisitos"></a>

## 2. Escolher a edição

Ligue a TV e conecte-a à mesma rede doméstica do computador ou celular. Permita ao CYTV acesso à rede local quando solicitado.

- **No-root** — se você não tem acesso root. Prepare o Developer Mode abaixo.
- **Root** — se você já tem acesso root por SSH. O instalador não faz root na TV. Não ative Developer Mode nessa TV; preserve o acesso SSH e os dados de recuperação.

### Configurar Developer Mode (No-root)

Developer Mode permite ao CYTV instalar apps em uma TV sem root.

1. Na TV, abra LG Apps, procure Developer Mode e instale o app.
2. Abra Developer Mode e entre com sua conta LG Developer. Se necessário, crie uma conta em [LG Developer](https://webostv.developer.lge.com).
3. Ative Dev Mode Status. A TV reiniciará. Depois, abra Developer Mode novamente.
4. Ative Key Server e deixe Developer Mode aberto. Use o IP Address exibido como endereço da TV no CYTV.
5. Digite a Passphrase: os seis caracteres exibidos no Developer Mode da TV. Respeite maiúsculas e minúsculas.

Use o código da TV, não a senha da sua conta LG. Se o código não aparecer, ative Key Server.

O pareamento é uma etapa separada: quando a TV pedir, autorize o CYTV com o controle remoto.

Mantenha Developer Mode ativo: antes de o tempo acabar, abra o app e pressione EXTEND com a TV conectada à Internet. Se expirar, a LG pode remover esses apps.

<a id="instalação-e-idioma"></a>

## 3. Abra o instalador

- **Windows x64:** baixe `cytv-windows-x64-desktop.zip`, escolha **Extrair tudo** no Explorador de Arquivos e abra `cytv-desktop/cytv-desktop.exe`. Mantenha a pasta `_internal` ao lado.
- **macOS 13+:** extraia `cytv-macos-arm64.zip` para Apple Silicon ou `cytv-macos-x64.zip` para Intel; mova `cytv.app` para Aplicativos e abra. Permita acesso à rede local. Se uma cópia confiável for bloqueada, use Privacidade e Segurança → Abrir Mesmo Assim; não desative o Gatekeeper.
- **Linux x64:** no Ubuntu 22.04+, Debian 12+ ou Mint 21+, instale `cytv-linux-x64.deb` com o gerenciador gráfico de pacotes e abra Clean Your TV pelo menu. Pode ser necessário acesso à Internet para bibliotecas. Não há pacote Linux ARM.

**Android ARM64:** use um celular ARM de 64 bits com Android 7+ e WebView/Chrome 108+. Abra o APK baixado e permita a instalação dessa fonte se o Android pedir. Abra o CYTV; escolha o idioma no canto superior direito. Atualize sem desinstalar nem apagar dados.

O assistente usa inicialmente o idioma do sistema e salva sua escolha explícita. Na TV, abra **Configurações → Idioma** e escolha um idioma ou a opção automática do sistema. As preferências da TV e do instalador são independentes. Veja os códigos no [índice de idiomas](../LANGUAGES.md).

## 4. Instale na TV

1. No CYTV, escolha **Configurar minha TV**. No computador, selecione uma TV encontrada; no Android, digite o endereço IP. Se a busca não encontrar a TV, digite o endereço manualmente.
2. Escolha **No-root** ou **Root** e confira a TV selecionada antes de continuar.
3. No-root: digite o código do Developer Mode e aceite a solicitação na TV. Root: use suas credenciais SSH. Aceite uma nova identidade SSH apenas para sua própria TV em uma rede confiável. Se uma chave salva mudou, pare e investigue.
4. Siga o assistente. Mantenha a TV ligada, a mesma rede e o CYTV aberto até terminar. Não force a parada do app Android. Root ativa o controle de Home logo após preparar a recuperação.

No próximo candidato ainda não publicado, a instalação Root continua com um aviso se as entradas da TV não puderem ser lidas, mas a lista de aplicativos for válida. Entradas podem faltar na Home; uma lista de aplicativos com falha ou vazia ainda interrompe a instalação. Salve o relatório de diagnóstico se o aviso persistir.

## 5. Confira o controle remoto

1. Abra outro app na TV e pressione **Home** brevemente. Clean Your TV deve abrir. Informe ao assistente o que você viu; pule a verificação se não a realizou.
2. Confira setas, OK, Voltar, volume e som. Teste separadamente espera/retomada e inicialização depois de desligar da tomada. A instalação bem-sucedida não verifica essas ações por si só.

<a id="uso-e-recuperação"></a>

## 6. Uso e recuperação

Setas selecionam; OK abre; segure OK para reorganizar. Um toque em Voltar mantém a navegação e a confirmação de saída do aplicativo. Home abre o lançador com o controle ativo. Segure Voltar por 1,2 segundos para abrir LG Home uma vez. O interruptor de controle do Home e suas configurações não mudam.

**Pressione Home três vezes em dois segundos**, soltando entre os toques. Isso restaura LG Home e interrompe o controle sem apagar preferências.

No-root: Para reiniciar o controle de Home, abra Home Helper, escolha Iniciar Helper e confirme. Sua tela Home escolhida será mantida. Root: ative **Alterar Home** nas configurações do Home para retomar. **Abrir LG Home** abre LG Home uma vez sem mudar o destino de Home. Para restaurar LG Home como destino permanente, desative **Alterar Home**. Nunca execute os dois controladores juntos. Se a falha voltar, mantenha LG Home ativo.

## Precisa de ajuda?

Se a instalação foi interrompida, use a mesma conexão salva e escolha primeiro **Verificar estado da TV**. Continue apenas pela recuperação oferecida pelo assistente. Se o estado for desconhecido, salve o relatório de diagnóstico e pare; preserve os dados de recuperação e não repita a instalação às cegas.

Durante a recuperação, mantenha o controle de Home desativado e preserve os relatórios originais e a conexão salva. Confirme a inspeção e as alterações separadamente. Siga o guia detalhado para a versão instalada; não force a reinstalação nem apague o estado de recuperação.

Informe modelo, firmware, No-root ou Root, dispositivo de instalação, etapa e mensagem de erro. Remova senhas, chaves, endereços e dados pessoais antes de compartilhar o relatório. Ele não é publicado automaticamente.

[Relatar problema](../FEEDBACK.md) · [Recuperação — inglês](../RECOVERY.md) · [Atualizar ou remover — inglês](../MAINTENANCE.md) · [Outros idiomas](../LANGUAGES.md)

Nas próximas versões, o aviso e o botão “Desativar prévia HDMI” aparecem com 4K selecionado ou ativo somente em temas com a prévia de entradas ativada. Durante a prévia HDMI, o vídeo de fundo em 4K é temporariamente substituído por uma imagem estática em 1080p. Desative a prévia de entradas para manter o fundo em 4K.

### Candidato: remoção simples

Os botões acima continuam oferecendo a versão publicada. No próximo candidato, escolha **Desinstalar Clean Your TV** em Manutenção usando a mesma conexão salva. Confirme uma vez. Os apps e arquivos conhecidos do projeto presentes são removidos; os ausentes são ignorados, inclusive após instalação parcial.

Quando solicitado, desconecte a TV da tomada, reconecte, aguarde a rede e escolha **Tentar novamente**. Espera ou Quick Start não é reinicialização completa; CYTV não reinicia a TV automaticamente. Se a conexão cair, verifique-a e repita a mesma remoção, sem outro assistente de recuperação. Se o acesso for negado, use a conexão Root solicitada; se a TV estiver ocupada, aguarde e tente novamente. O sucesso só aparece após verificar a limpeza final. Preserve as chaves e os relatórios originais. Continuam válidos os controles de emergência e o consentimento para compartilhar.

Neste candidato, uma instalação com falha ou interrompida oferece recuperação diretamente. Se No-root não puder continuar, confirme a remoção completa uma vez. A remoção faz até três tentativas em caso de perda temporária de conexão ou processo CYTV ocupado. Se precisar de Root, escolha **Conectar com Root** para a mesma TV; a limpeza Root verificada também conclui a remoção No-root bloqueada. Se a ativação Root falhar, o CYTV tenta restaurar e verificar LG Home sem repetir a ativação. Cancelar trabalho pendente preserva o relatório e as ações de recuperação. A parada de emergência é mantida.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="python-opcional-para-root"></a>
<a id="testes-em-hardware-e-limites"></a>
<a id="bloqueio-de-firmware-lg-no-120"></a>
<a id="novidades-da-130-recuperação-guiada-no-computador"></a>
<a id="novidades-da-130--12"></a>
<a id="candidato-não-publicado-instalar-root-pelo-homebrew"></a>
<a id="candidato-não-publicado-recuperação-de-som-hdmi-root"></a>
<a id="temas-154"></a>
<a id="categorias-de-configurações-candidato-não-publicado"></a>
<a id="resolução-gráfica-automática-candidato"></a>
<a id="atualização-e-remoção"></a>
<a id="ajuda-e-outras-instruções"></a>
<a id="temas"></a>
<a id="categorias-de-configurações-154"></a>
<a id="resolução-gráfica-automática-160"></a>
<a id="espaço-de-armazenamento"></a>

Referências detalhadas em inglês: [requisitos](../COMPATIBILITY.md) · [controles](../CONTROLS.md) · [temas](../THEMES.md) · [atualizações](../UPDATES.md).

> Candidato não publicado: Root Home experimental é escolhido pelas capacidades do Qt SDK 6–9, sem lista de modelos. Compatibilidade física e OTA normal não foram verificadas. Outras integrações Home não são alteradas; após parada de segurança ou energia, ative Home explicitamente. [#364](../development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).
