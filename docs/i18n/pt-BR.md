# Clean Your TV — guia de uso

o instalador pede um nome, padrão **Home**; CLI: `--tv-name "Aashiyaan"`. Após atualizar uma instalação antiga, **Configurações → Home → Nome da TV** aparece automaticamente. Salve ou restaure Home a qualquer momento. O nome permanece após reiniciar e em atualizações compatíveis; as outras configurações são preservadas. Até 48 caracteres. Configurações salva o nome do inicializador. Para mudar a tela de início da LG, aplique o mesmo nome pelo instalador. Não há outra tela de carregamento; o nome de rede não muda.

Alteração ainda não publicada: antes de uma nova instalação, o instalador do computador verifica se há uma versão estável mais recente no GitHub. Escolha “Abrir o GitHub e baixar a versão mais recente” para parar e baixá-la, ou “Não, instalar esta versão” para continuar explicitamente. Se a verificação falhar, você pode continuar. Operações pendentes e recuperação ignoram a verificação.

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

Para Root, o instalador verifica e escolhe um método disponível para controlar Home. Se não puder verificar a compatibilidade, a instalação será interrompida; não ignore a verificação que falhou.

**No-root → Root:** Se o No-root foi instalado novamente após a remoção completa, mudar para Root pode exigir uma limpeza antes. Salve as preferências do Home, escolha **Desinstalar Clean Your TV** com a conexão Root salva e aguarde a remoção verificada. Isso também remove Home e Helper do No-root. Depois instale Root; preserve os registros de recuperação.

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

A instalação Root continua com um aviso se as entradas da TV não puderem ser lidas, mas a lista de aplicativos for válida. Entradas podem faltar na Home; uma lista de aplicativos com falha ou vazia ainda interrompe a instalação. Salve o relatório de diagnóstico se o aviso persistir.

## 5. Confira o controle remoto

1. Abra outro app na TV e pressione **Home** brevemente. Clean Your TV deve abrir. Informe ao assistente o que você viu; pule a verificação se não a realizou.
2. Confira setas, OK, Voltar, volume e som. Teste separadamente espera/retomada e inicialização depois de desligar da tomada. A instalação bem-sucedida não verifica essas ações por si só.

<a id="uso-e-recuperação"></a>

## 6. Uso e recuperação

Suporte IR No-root: soltar Home após um toque curto agenda o Clean para cerca de 700 ms depois; o LG Home pode aparecer primeiro. Segurar Home continua com o webOS e três toques ainda param o Helper. O acesso pelo Developer Mode padrão não foi verificado; não altere permissões dos dispositivos de entrada.

Setas selecionam; OK abre; segure OK para reorganizar. Um toque em Voltar mantém a navegação e a confirmação de saída do aplicativo. Home abre o lançador com o controle ativo. Segure Voltar por 1,2 segundos para abrir LG Home uma vez. O interruptor de controle do Home e suas configurações não mudam.

**Pressione Home três vezes em dois segundos**, soltando entre os toques. Isso restaura LG Home e interrompe o controle sem apagar preferências.

No-root: Para reiniciar o controle de Home, abra Home Helper, escolha Iniciar Helper e confirme. Sua tela Home escolhida será mantida. Root: ative **Alterar Home** nas configurações do Home para retomar. **Abrir LG Home** abre LG Home uma vez sem mudar o destino de Home. Para restaurar LG Home como destino permanente, desative **Alterar Home**. Nunca execute os dois controladores juntos. Se a falha voltar, mantenha LG Home ativo.

Uma atualização não reinicia um Helper No-root parado. Retome-o explicitamente como descrito acima; não exclua manualmente os marcadores de parada.

## Precisa de ajuda?

Se aparecer `ssh-identity-changed` após restaurar o TV ou alterar o SSH, pare: o CYTV bloqueou a mudança da chave salva antes da autenticação. A confirmação inicial de confiança não a substitui; uma desinstalação pendente não explica a divergência. Guarde o perfil original, as chaves e os registros de recuperação. Não há comando automático compatível para renovar a confiança. É preciso verificar independentemente a identidade/impressão digital do TV e revisar um procedimento que preserve o perfil: [recuperação da identidade SSH](../RECOVERY.md#ssh-identity-changed).

Se a instalação foi interrompida, use a mesma conexão salva e escolha primeiro **Verificar estado da TV**. Continue apenas pela recuperação oferecida pelo assistente. Se o estado for desconhecido, salve o relatório de diagnóstico e pare; preserve os dados de recuperação e não repita a instalação às cegas.

Durante a recuperação, mantenha o controle de Home desativado e preserve os relatórios originais e a conexão salva. Confirme a inspeção e as alterações separadamente. Siga o guia detalhado para a versão instalada; não force a reinstalação nem apague o estado de recuperação.

Informe modelo, firmware, No-root ou Root, dispositivo de instalação, etapa e mensagem de erro. Remova senhas, chaves, endereços e dados pessoais antes de compartilhar o relatório. Ele não é publicado automaticamente.

[Relatar problema](../FEEDBACK.md) · [Recuperação — inglês](../RECOVERY.md) · [Atualizar ou remover — inglês](../MAINTENANCE.md) · [Outros idiomas](../LANGUAGES.md)

### Remoção simples

Escolha **Desinstalar Clean Your TV** em Manutenção usando a mesma conexão salva. Confirme uma vez. Os apps e arquivos conhecidos do projeto presentes são removidos; os ausentes são ignorados, inclusive após instalação parcial.

Em TVs antigas sem um aplicativo LG Home separado, a remoção No-root pode mudar para a TV ao vivo. Mantenha a TV ligada e reinicie se solicitado; não apague os dados de recuperação nem restaure a TV.

Quando solicitado, desconecte a TV da tomada, reconecte, aguarde a rede e escolha **Tentar novamente**. Espera ou Quick Start não é reinicialização completa; CYTV não reinicia a TV automaticamente. Se a conexão cair, verifique-a e repita a mesma remoção, sem outro assistente de recuperação. Se o acesso for negado, use a conexão Root solicitada; se a TV estiver ocupada, aguarde e tente novamente. O sucesso só aparece após verificar a limpeza final. Preserve as chaves e os relatórios originais. Continuam válidos os controles de emergência e o consentimento para compartilhar.

Uma instalação com falha ou interrompida oferece recuperação diretamente. Se No-root não puder continuar, confirme a remoção completa uma vez. A remoção faz até três tentativas em caso de perda temporária de conexão ou processo CYTV ocupado. Se precisar de Root, escolha **Conectar com Root** para a mesma TV; a limpeza Root verificada também conclui a remoção No-root bloqueada. Se a ativação Root falhar, o CYTV tenta restaurar e verificar LG Home sem repetir a ativação. Cancelar trabalho pendente preserva o relatório e as ações de recuperação. A parada de emergência é mantida.

Após uma falha de conexão durante a remoção, abra os detalhes, verifique a rede ou escolha uma chave SSH Root existente e tente novamente. Endereço, edição, porta e verificação da chave da TV permanecem fixos. No-root verifica o Helper antes do pareamento: pare-o e confirme a nova verificação no mesmo processo. Só uma TV comprovadamente vazia e sem instalação pendente pode dispensar a reinicialização; após remoção real, faça a reinicialização solicitada. Se o serviço de entradas falhar, a limpeza segura dos pacotes continua; o sucesso ainda exige verificar a limpeza do atalho.

**Reinstalar o Root:** Escolha **Configurar minha TV → Root** com a conexão salva e confirme **Reinstalar Root?**. O instalador restaura o LG Home e remove completamente o Clean Your TV, incluindo seus atualizadores, Home Helper e preferências salvas. Após verificar a remoção, instala e ativa os pacotes e o ambiente Root incluídos nesse instalador. Os outros apps da TV e o acesso root/SSH existente são preservados. Se a remoção parar ou solicitar uma reinicialização completa, termine-a antes de iniciar a configuração novamente. **Desinstalar Clean Your TV** sozinho nunca inicia outra instalação.

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

## Clima

Abra Configurações → Clima, abaixo de Papéis de parede. Ative o clima e abra Cidade para pesquisar e selecionar a região e o país corretos, ou escolha Automático para uma cidade aproximada pela conexão. Uma VPN pode alterar o resultado; se a cidade não aparecer ou estiver errada, use a busca manual. A cidade detectada ou escolhida aparece nas configurações. Escolha °C / m/s ou °F / mph e um formato disponível: compacto, atual, detalhado ou quatro dias. A prévia segue o tema; Exemplo indica dados ilustrativos. Liquid Glass aceita apenas o formato compacto. Ribbon e Atmosphere não exibem clima. Desativar interrompe as solicitações e oculta cidade, unidades e formato; a seleção de fonte continua disponível. Em uma falha, dados recentes podem permanecer por algum tempo; depois o clima fica oculto até atualizar.

Escolha a fonte da previsão: Auto, MET Norway ou Open-Meteo. Auto começa com MET Norway, tenta Open-Meteo uma vez em caso de falha e depois reutiliza a última fonte bem-sucedida e seu cache. A seleção manual nunca muda de fonte automaticamente. Novas configurações usam Auto; as salvas sem fonte mantêm Open-Meteo. A fonte real aparece nos ajustes. A disponibilidade depende da rede. O aplicativo consulta o MET no máximo uma vez a cada três horas; o cache expira após seis horas. Campos ausentes ficam ocultos: MET não fornece sensação térmica nem probabilidade de precipitação. Os intervalos diários resumem pontos de previsão, não extremos medidos.

As coordenadas vão para api.met.no ou api.open-meteo.com; as buscas de cidades, para geocoding-api.open-meteo.com. A localização automática opcional envia seu IP público a get.geojs.io. As conexões usam HTTPS; não é necessária chave de API. Local, fonte e cache ficam na TV. Fontes de dados inclui termos e créditos, como o Instituto Meteorológico Norueguês (MET Norway, CC BY 4.0).

O botão Fontes de dados no título Clima abre informações sobre os serviços e as licenças.
