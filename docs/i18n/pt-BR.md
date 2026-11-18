# Clean Your TV — guia de uso

Clean Your TV oferece uma tela inicial pessoal para sua LG webOS: seus apps na sua ordem, sem linhas patrocinadas neste menu. Instale pelo computador ou por um celular Android; depois o computador pode ficar desligado.

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

Se o instalador oferecer **No-root**, você pode continuar com a conexão SSH root existente. Essa opção dispensa o Developer Mode.

[Guia detalhado de instalação](../INSTALL.md) · [Compatibilidade](../COMPATIBILITY.md)

### Configurar Developer Mode (No-root)

Developer Mode permite ao CYTV instalar apps em uma TV sem root.

1. Na TV, abra LG Apps, procure Developer Mode e instale o app.
2. Abra Developer Mode e entre com sua conta LG Developer. Se necessário, crie uma conta em [LG Developer](https://webostv.developer.lge.com).
3. Ative Dev Mode Status. A TV reiniciará. Depois, abra Developer Mode novamente.
4. Ative Key Server e deixe Developer Mode aberto. Use o IP Address exibido como endereço da TV no CYTV.
5. Digite a Passphrase: os seis caracteres exibidos no Developer Mode da TV. Respeite maiúsculas e minúsculas.

Use o código da TV, não a senha da sua conta LG. Se o código não aparecer, ative Key Server.

O pareamento é uma etapa separada: quando a TV pedir, autorize o CYTV com o controle remoto. Se a TV recusar a solicitação, confirme no CYTV que deseja tentar novamente com a mesma TV.

Se aparecer um aviso na primeira instalação do No-root de que não foi possível ler as entradas HDMI, você pode continuar com os aplicativos encontrados.

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
4. Siga o assistente. Mantenha a TV ligada, a mesma rede e o CYTV aberto até terminar. Não force a parada do app Android.

No instalador para computador, após verificar a conexão, escolha **Continuar configuração** para manter a mesma conexão e edição. O assistente explica o estado de uma instalação anterior; os resultados técnicos ficam em **Detalhes**. Se uma operação anterior precisar de recuperação, use primeiro a ação de recuperação oferecida. A configuração verifica as versões instaladas e pede confirmação antes de alterações. As solicitações de reinicialização salvas são verificadas novamente; o assistente só pede para reiniciar quando a limpeza atual exige isso.

## 5. Confira o controle remoto

1. Abra outro app na TV e pressione **Home** brevemente. Clean Your TV deve abrir. Informe ao assistente o que você viu; pule a verificação se não a realizou.
2. Confira setas, OK, Voltar, volume e som.

<a id="uso-e-recuperação"></a>

## 6. Uso e recuperação

Para fixar uma entrada HDMI, selecione-a em **+ / Adicionar aplicativo**. Pressione OK para mudar para a entrada. Mantenha OK pressionado para mover ou ocultar o bloco.

Setas selecionam; OK abre; segure OK para reorganizar. Um toque em Voltar mantém a navegação e a confirmação de saída do aplicativo. Home abre o lançador com o controle ativo. Segure Voltar por 1,2 segundos para abrir LG Home uma vez. O interruptor de controle do Home e suas configurações não mudam.

Para editar com toques curtos, abra **Configurações do Home → Aparência → Editar blocos**. Pressione OK para selecionar um bloco, mova-o com as setas e pressione OK para soltá-lo. Voltar cancela o movimento ou encerra a edição.

**Pressione Home três vezes em dois segundos**, soltando entre os toques. Isso restaura LG Home e interrompe o controle sem apagar preferências.

No-root: Para reiniciar o controle de Home, abra Home Helper, escolha Iniciar Helper e confirme. Sua tela Home escolhida será mantida. Root: ative **Alterar Home** nas configurações do Home para retomar. **Abrir LG Home** abre LG Home uma vez sem mudar o destino de Home. Para restaurar LG Home como destino permanente, desative **Alterar Home**. Nunca execute os dois controladores juntos. Se a falha voltar, mantenha LG Home ativo.

Se o Home Helper estiver parado, você também pode selecionar **Iniciar Helper** nas configurações da tela Home ou da proteção de tela. O status é atualizado automaticamente após a inicialização.

## Precisa de ajuda?

Se aparecer `ssh-identity-changed`, pare e verifique a chave SSH da TV. [Recuperação após mudança da chave SSH](../RECOVERY.md#ssh-identity-changed)

Após redefinir sua TV No-root para os padrões de fábrica, escolha **Reconectar após a redefinição de fábrica** quando a chave mudar. Siga as instruções na sua rede doméstica confiável. O perfil anterior e o registro de remoção são preservados.

Se a instalação foi interrompida, use a mesma conexão salva e escolha primeiro **Verificar estado da TV**. Continue apenas pela recuperação oferecida pelo assistente. Se o estado for desconhecido, salve o relatório de diagnóstico e pare; preserve os dados de recuperação e não repita a instalação às cegas.

Durante a recuperação, mantenha o controle de Home desativado e preserve os relatórios originais e a conexão salva. Confirme a inspeção e as alterações separadamente. Siga o guia detalhado para a versão instalada; não force a reinstalação nem apague o estado de recuperação.

Informe modelo, firmware, No-root ou Root, dispositivo de instalação, etapa e mensagem de erro. Remova senhas, chaves, endereços e dados pessoais antes de compartilhar o relatório. Ele não é publicado automaticamente.

Se o No-root oferecer **Repetir a verificação de armazenamento**, selecione essa opção para repetir a verificação de somente leitura na mesma TV. Confirme a instalação separadamente após uma verificação bem-sucedida. Se houver uma operação pendente, escolha **Revisar opções de recuperação**.

Se o instalador de desktop verificar os pacotes, mas o botão Home não abrir o Clean Your TV, escolha **Diagnóstico do botão Home** para No-root ou **Verificar status da TV** para Root na tela de resultados.

Se o instalador no computador falhar, selecione **Relatar um problema** para revisar e copiar o rascunho. Se houver um relatório de diagnóstico salvo, anexe-o ao formulário.

[Relatar problema](../FEEDBACK.md) · [Recuperação — inglês](../RECOVERY.md) · [Atualizar ou remover — inglês](../MAINTENANCE.md) · [Outros idiomas](../LANGUAGES.md)

### Remoção simples

Escolha **Desinstalar Clean Your TV** em Manutenção usando a mesma conexão salva. Confirme uma vez. Os apps e arquivos conhecidos do projeto presentes são removidos; os ausentes são ignorados, inclusive após instalação parcial.

Quando solicitado, desconecte a TV da tomada, reconecte, aguarde a rede voltar. Espera ou Quick Start não é reinicialização completa; CYTV não reinicia a TV automaticamente. Se o acesso for negado, use a conexão Root solicitada; se a TV estiver ocupada, aguarde e tente novamente. O sucesso só aparece após verificar a limpeza final. Preserve as chaves e os relatórios originais. Continuam válidos os controles de emergência e o consentimento para compartilhar.

Se o instalador no computador estiver aguardando a TV, escolha **Continuar a remoção** quando a opção aparecer. Escolha **Cancelar** para parar de aguardar ou **Tentar novamente** para verificar a conexão manualmente.

Se **Voltar ao LG Home** aparecer na tela de remoção, selecione essa opção. Quando o instalador verificar a restauração, escolha **Continuar a remoção**. Voltar ao LG Home diretamente pelo menu de manutenção mantém os aplicativos instalados.

Se o instalador não conseguir verificar a remoção, a limpeza final, os controles da TV ou o resultado da operação de pacotes, ou informar que os caminhos do projeto mudaram, escolha **Revisar opções de recuperação** com a conexão original salva. Confirme a continuação separadamente se o instalador oferecer essa opção. Se a recuperação da instalação No-root oferecer **Verificar status da TV**, escolha essa opção e preserve os dados de recuperação.

Se o instalador não conseguir verificar a reinicialização completa solicitada, salve e anexe o relatório de diagnóstico. Mantenha a conexão salva e os dados de recuperação. Não repita os ciclos de energia nem apague manualmente a operação pendente.

Após a confirmação da remoção, você pode fechar o instalador no computador ou escolher **Configurar minha TV** para iniciar uma nova instalação na mesma TV com a mesma edição e conexão.

**Reinstalar o Root:** Escolha **Configurar minha TV → Root** com a conexão salva e confirme **Reinstalar Root?**. O instalador restaura o LG Home e remove completamente o Clean Your TV, incluindo seus atualizadores, Home Helper e preferências salvas. Após verificar a remoção, instala e ativa os pacotes e o ambiente Root incluídos nesse instalador. Os outros apps da TV e o acesso root/SSH existente são preservados. Se o assistente no computador pausar, abra o mesmo instalador e escolha **Continuar a reinstalação do Root**. Após a verificação da remoção, escolha **Continuar a instalação do Root**. **Desinstalar Clean Your TV** sozinho nunca inicia outra instalação.

### Alterar configurações da LG e concluir a recuperação do Root

No instalador para computador, abra **Ação de manutenção → Ajustar as configurações da LG (Debloat)** com a conexão salva da TV. Selecione as configurações que quer alterar, escolha **Aplicar configurações selecionadas** e confira os resultados. Se houver uma operação pendente, escolha primeiro **Revisar opções de recuperação** com a conexão original salva.

- [Root Updater](../RECOVERY.md#standalone-root-updater-rollback-readiness)
- [Root System Updater](../RECOVERY.md#root-system-rollback-readiness-candidate)

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

<a id="candidato-unreleased-nodejs-antigo-na-tv"></a>
<a id="nodejs-antigo-na-tv-publicado-na-v1120"></a>
<a id="remoção-simples-v1110"></a>

## Configurações

Em **Configurações → Aparência**, ative **Ordenar por frequência de uso**. A ordem do dock é preservada. Segure OK para mover ou ocultar um bloco na ordem manual. Desative a opção para voltar à ordem manual. A opção também fica no fim das configurações do instalador cytv.

Use ↑ ↓ para escolher uma categoria e → ou OK para entrar. ← volta às categorias; Voltar retorna primeiro a elas e depois fecha as configurações. Ao retornar a uma seção, o foco volta ao último controle disponível. Em Colunas, as setas seguem a grade de três colunas. Em Idioma, o foco entra no idioma selecionado.

Em **Configurações → Sua tela Home → Formato da hora**, escolha **Automático (região da TV)**, **12 horas** ou **24 horas**.

Se No-root não conseguir ler o estado de Home, escolha Tentar novamente. Um controle indisponível não significa que Home esteja desativado. Em Papéis de parede, envie uma imagem do telefone ou CYTV; qualidade e escurecimento aparecem quando há um papel de parede disponível. A remoção de um papel de parede pessoal pede confirmação; Cancelar o mantém.

## Clima

Abra Configurações → Clima, abaixo de Papéis de parede. Ative o clima e abra Cidade para pesquisar e selecionar a região e o país corretos, ou escolha Automático para uma cidade aproximada pela conexão. Uma VPN pode alterar o resultado; se a cidade não aparecer ou estiver errada, use a busca manual. A cidade detectada ou escolhida aparece nas configurações. Escolha °C / m/s ou °F / mph e um formato disponível: compacto, atual, detalhado ou quatro dias. A prévia segue o tema; Exemplo indica dados ilustrativos. Liquid Glass aceita apenas o formato compacto. Ribbon e Atmosphere não exibem clima. Desativar interrompe as solicitações e oculta cidade, unidades e formato; a seleção de fonte continua disponível. Em uma falha, dados recentes podem permanecer por algum tempo; depois o clima fica oculto até atualizar.

Escolha a fonte da previsão: Auto, MET Norway ou Open-Meteo. Auto começa com MET Norway, tenta Open-Meteo uma vez em caso de falha e depois reutiliza a última fonte bem-sucedida e seu cache. A seleção manual nunca muda de fonte automaticamente. Novas configurações usam Auto; as salvas sem fonte mantêm Open-Meteo. A fonte real aparece nos ajustes. A disponibilidade depende da rede. O aplicativo consulta o MET no máximo uma vez a cada três horas; o cache expira após seis horas. Campos ausentes ficam ocultos: MET não fornece sensação térmica nem probabilidade de precipitação. Os intervalos diários resumem pontos de previsão, não extremos medidos.

As coordenadas vão para api.met.no ou api.open-meteo.com; as buscas de cidades, para geocoding-api.open-meteo.com. A localização automática opcional envia seu IP público a get.geojs.io. As conexões usam HTTPS; não é necessária chave de API. Local, fonte e cache ficam na TV. Fontes de dados inclui termos e créditos, como o Instituto Meteorológico Norueguês (MET Norway, CC BY 4.0).

O botão Fontes de dados no título Clima abre informações sobre os serviços e as licenças.

## Papel de parede do iPhone

Abra Configurações → Papéis de parede → Enviar do telefone e leia o código. Escolha JPG, PNG ou HEIC/HEIF, recorte, confirme o limite de qualidade e envie. Escolha Aplicar na TV. Safari usa suporte HEIC nativo; Chrome, Firefox e outros navegadores modernos usam o decodificador local incluído quando necessário. A conversão ocorre no telefone, sem serviço externo. Cancelar ou escolher outro arquivo interrompe a conversão. Entrada: 32 MiB e 50 milhões de pixels; saída: até 1080p e 2 MiB. Se falhar, tente outra foto ou JPG/PNG. É para a página do telefone, não o app Mac.

## Configure seu Clean Your TV

Antes de escolher um tema, use **Debloat** para selecionar quais opções de anúncios, recomendações, privacidade e notificações da LG você quer alterar. Confira cada resultado. Se o instalador não conseguir ler o valor original, não poderá salvá-lo para reversão automática. Escolha **Pular Debloat** para manter as configurações atuais.

Durante a desinstalação, você pode restaurar os valores originais salvos pelo Debloat. Se pular a restauração, a desinstalação continua sem alterar esses ajustes.

Após a instalação bem-sucedida, escolha Classic, Liquid Glass ou Ribbon e ative ou desative o clima. Ribbon não oferece clima; Liquid Glass usa o formato compacto. A cidade é estimada pela conexão e pode ser alterada na Home.

No-root com Developer Mode oferece renovação automática; continue verificando o temporizador oficial. Nas novas instalações do No-root por um acesso SSH root existente, a aba Developer Mode fica oculta. Root permite bloquear atualizações de firmware LG pelo Homebrew Channel, incluindo as de segurança; é preciso reiniciar a TV de verdade pelo Homebrew Channel. As atualizações CYTV são separadas.

Manter configurações atuais pula a personalização. O interruptor mostra o estado atual da função do modo. Configurações não alteradas são mantidas. Reinstalar Root continua removendo preferências CYTV conforme descrito acima. Confira a aparência na TV e opções não confirmadas na Home antes de tentar novamente.

## Atualizações em uma TV com root

Se o System Updater com atualização própria estiver configurado, use **Atualizações de software → Atualizar tudo** para Root ou No-root em uma TV com root. Mantenha a TV ligada até terminar. Para reparar somente o atualizador, abra o Home e escolha **Atualizações de software → Recuperação → Reinstalar System Updater**; o Home e suas configurações serão preservados. No-root sem acesso root continua usando a instalação pelo computador.
