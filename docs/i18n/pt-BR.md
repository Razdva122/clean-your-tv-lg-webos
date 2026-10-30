# Clean Your TV — guia de uso

> v1.5.0: temas, galeria e envio do PC para a TV. Limites conhecidos de Root: Appearance pode se deslocar 110 px; Home pode não abrir automaticamente após o modo de espera. A validação por dispositivo continua limitada. [1.5.0](../RELEASE-1.5.0.md).

[Documentação](../README.md) · [Relatar um problema](../FEEDBACK.md)

Este guia descreve a versão publicada **[1.4.1](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.4.1)**. A aceitação no C3 abrange os testes registrados de energia, Home, foco, estado desligado e reversão manual. Outras TVs, áudio eARC e dispositivos Android físicos continuam sem verificação; instalar com sucesso não comprova compatibilidade. [Escopo testado (inglês)](../RELEASE-1.4.0-ACCEPTANCE.md).

## Escolher a edição

No-root e Root são opções equivalentes para diferentes configurações da TV. Escolha No-root para LG Developer Mode ou Root se já tiver acesso root por SSH. A compatibilidade e os testes realizados são específicos de cada edição.

- **No-root:** ative LG Developer Mode e Key Server. Digite a frase de acesso exibida na TV e aceite nela o pedido separado de pareamento. Developer Mode deve continuar ativo: a expiração pode remover aplicativos instalados por esse método. Confira o cronômetro oficial mesmo com a renovação Beta ativada. O monitoramento do Helper depende da rede local.
- **Root:** é necessário acesso SSH root já existente. O instalador não faz root. Não ative Developer Mode em uma TV que já tenha root. Mantenha o acesso root e os serviços de recuperação disponíveis.

Root exige interfaces Home funcionais de Settings Service e System Profile (`com.webos.service.systemprofile`); ter acesso root não garante compatibilidade.

## Requisitos

Ligue a TV e conecte os dois dispositivos à mesma rede local confiável. Depois, o computador pode ficar desligado. A compatibilidade depende do modelo, firmware e controle remoto; Root ainda tem testes em hardware pendentes.

No-root Helper precisa de Node.js **0.12.2+** na TV. Root precisa de Node.js **8+** e Python **3.9+** funcional. Se necessário, o instalador baixa um Python privado verificado; a preparação inicial precisa de **320 MiB** livres. Ele não substitui o Python do sistema. Preserve os ambientes usados na recuperação. [Python (inglês)](../OPTIONAL-PYTHON.md). A renovação do Developer Mode é **Beta, desativada por padrão**; a renovação real sem root não está confirmada. Continue conferindo o cronômetro oficial.

### Configurar Developer Mode (No-root)

Developer Mode permite ao CYTV instalar apps em uma TV sem root.

1. Na TV, abra LG Apps, procure Developer Mode e instale o app.
2. Abra Developer Mode e entre com sua conta LG Developer. Se necessário, crie uma conta em webostv.developer.lge.com.
3. Ative Dev Mode Status. A TV reiniciará. Depois, abra Developer Mode novamente.
4. Ative Key Server e deixe Developer Mode aberto. Use o IP Address exibido como endereço da TV no CYTV.
5. Digite a Passphrase: os seis caracteres exibidos no Developer Mode da TV. Respeite maiúsculas e minúsculas.

Use o código da TV, não a senha da sua conta LG. Se o código não aparecer, ative Key Server.

O pareamento é uma etapa separada: quando a TV pedir, autorize o CYTV com o controle remoto.

Mantenha Developer Mode ativo: antes de o tempo acabar, abra o app e pressione EXTEND com a TV conectada à Internet. Se expirar, a LG pode remover esses apps.

## Instalação e idioma

- **Windows x64:** baixe `cytv-windows-x64-desktop.zip`, escolha **Extrair tudo** no Explorador de Arquivos e abra `cytv-desktop/cytv-desktop.exe`. Mantenha a pasta `_internal` ao lado. A assinatura de editor do Windows não está configurada. O console separado é `cytv-windows-x64.exe`; renomeie para `cytv.exe` e use `.\cytv.exe` no PowerShell para os comandos abaixo.
- **macOS 13+:** extraia `cytv-macos-arm64.zip` para Apple Silicon ou `cytv-macos-x64.zip` para Intel; mova `cytv.app` para Aplicativos e abra. Permita acesso à rede local. Se uma cópia confiável for bloqueada, use Privacidade e Segurança → Abrir Mesmo Assim; não desative o Gatekeeper. A compatibilidade com sistemas antigos não foi confirmada.
- **Linux x64:** no Ubuntu 22.04+, Debian 12+ ou Mint 21+, instale `cytv-linux-x64.deb` com o gerenciador gráfico de pacotes e abra Clean Your TV pelo menu. Pode ser necessário acesso à Internet para bibliotecas. Não há pacote Linux ARM. O executável independente `cytv-linux-x64` é a CLI; use o `.deb` para o app gráfico.

[Instalador Android (inglês)](../../android/README.md): escolha o idioma no canto superior direito. Atualize sem desinstalar nem apagar dados. Android 7 / WebView 108 é o mínimo, não um telefone verificado; a aceitação usou emulador Android 15 ARM64 / WebView 124. Telefones físicos e recuperação conectada a uma TV real continuam sem verificação.

O assistente usa inicialmente o idioma do sistema e salva sua escolha explícita. Na TV, abra **Configurações → Idioma** e escolha um idioma ou a opção automática do sistema. As preferências da TV e do instalador são independentes. Veja os códigos no [índice de idiomas](../LANGUAGES.md).

Para a CLI baixada separadamente no macOS/Linux, na pasta extraída:

```sh
chmod +x cytv
./cytv --language pt-BR install
```

Escolha a TV ou informe o IP, selecione a edição e confira o resumo. Confirme uma nova identidade SSH apenas para sua TV em uma rede confiável; uma chave salva que mudou bloqueia o acesso. Root prepara a recuperação e ativa Home imediatamente, sem período de teste nem etapa de confirmação para manter. Teste setas, OK, Home, Voltar/Cancelar, volume, espera e inicialização a frio.

## Uso e recuperação

Setas selecionam; OK abre; segure OK para reorganizar. Um toque em Voltar mantém a navegação e a confirmação de saída do aplicativo. Home abre o lançador com o controle ativo. Segure Voltar por 1,2 segundos para abrir LG Home uma vez. O interruptor de controle do Home e suas configurações não mudam.

**Pressione Home três vezes em dois segundos**, soltando entre os toques. Isso restaura LG Home e interrompe o controle sem apagar preferências. No No-root Helper até a versão 0.6.13, segure Home por cerca de dois segundos. Segurar Home não é o gesto de emergência do Root.

No-root: Para reiniciar o controle de Home, abra Home Helper, escolha Iniciar Helper e confirme. Sua tela Home escolhida será mantida. Root: ative **Alterar Home** nas configurações do Home para retomar. **Abrir LG Home** abre LG Home uma vez sem mudar o destino de Home. Para restaurar LG Home como destino permanente, desative **Alterar Home** ou execute `cytv restore`. Nunca execute os dois controladores juntos. Se a falha voltar, mantenha LG Home ativo.

```sh
./cytv --language pt-BR status
./cytv --language pt-BR doctor --report
./cytv --language pt-BR restore
./cytv --language pt-BR uninstall
```

Após uma interrupção, execute primeiro `status` e preserve os registros. `restore` restaura LG Home sem remover aplicativos; `uninstall` restaura antes de remover. Os dados de recuperação Root são mantidos de propósito: não os apague para forçar a reinstalação. Revise relatórios antes de compartilhar; não publique chaves nem pastas de perfis.

Somente no candidato ainda não publicado, nas duas edições: abra **Configurações do Home → Aparência → Colunas** e escolha de 1 a 8 colunas, ou **Conforme o tema** para usar o valor do tema (Classic: 5). Um número explícito tem prioridade sobre o tema. Temas com disposição fixa ocultam a opção Colunas e usam o valor do autor. Sua escolha salva volta a valer ao mudar para um tema que ofereça esse ajuste. Na prévia candidata Alpine, os apps ficam em uma única faixa horizontal circular: Esquerda/Direita rola, Cima abre os atalhos e Baixo volta ao mesmo app. Na prévia Alpine, a roda do mouse ou o touchpad também rola a faixa; Home não se move atrás de uma caixa de diálogo aberta.

Candidato ainda não publicado, ambas as edições: em **Configurações do Home → Aparência**, desative **Mostrar bloco «Adicionar app»** para ocultar +. A opção vem ativada. Use **Adicionar app** na mesma seção para adicionar ou restaurar apps mesmo com + oculto. Continua sendo possível mover e ocultar apps; a escolha permanece após reiniciar. Se todos os apps estiverem ocultos, os controles superiores e as configurações continuam disponíveis.

Nas prévias de temas do candidato ainda não publicado com barra lateral opcional, Cima/Baixo seleciona um item do menu, Direita vai para os aplicativos e Esquerda na primeira coluna de aplicativos volta ao menu.

No-root 1.5.0: Helper pode se recuperar de um timeout temporário do watchdog ao sair do modo de espera, com no máximo cinco tentativas em dez minutos. Stop e três toques em Home ainda exigem iniciar o Helper explicitamente; falhas repetidas o mantêm parado. A validação na TV está pendente. [Comportamento e limites (inglês)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Atualização e remoção

Após conectar, cytv mostra versão instalada → incluída e diferencia primeira instalação, reinstalação e retorno a uma versão anterior. Confira o resumo antes de confirmar; `--yes` mantém as verificações de compatibilidade. Guarde pacotes funcionais e cópias privadas das configurações. Ao atualizar pelo computador, pare o No-root Helper antes de substituir os pacotes; não desinstale primeiro. Não instale uma IPK isolada sobre Root ativo: use o procedimento adequado do cytv. Remover o aplicativo do computador não remove os aplicativos da TV.

Abra configurações do Home → Atualizações de software e revise as versões antes de confirmar. Atualização e reversão na TV exigem **root, Homebrew Channel** e infraestrutura de atualização compatível já preparada, mesmo na edição No-root. Sem root, use o computador. Preparar atualizações completas é uma ação explícita separada: [atualizações (inglês)](../UPDATES.md). Recuperação mostra a versão salva; a reversão pode perder alterações posteriores nas configurações.

**Instalação 1.3.0 existente:** o System Updater original não consegue aplicar 1.4.0 porque mudou a lista de arquivos permitidos. Se a tentativa parou antes da substituição, preserve o registro e pare; não apague o estado nem repita às cegas. Migre por recuperação verificada e nova instalação 1.4.0; atualizar só o app não substitui os drivers Root preservados. A próxima correção OTA **ainda não foi publicada**. [Migração e recuperação (inglês)](../UPDATES.md#one-time-computer-preparation).

Correção ainda não publicada do canal de configurações do Home: atualize Home e Helper juntos quando houver um candidato coordenado. Atualizar apenas o Home não entrega a correção. A validação na TV da compilação final da versão está pendente. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

A recuperação de som HDMI do Root é experimental e **desativada por padrão**; ative somente se precisar. Ela pode interromper áudio saudável e não comprova compatibilidade eARC. [Recuperação de som (inglês)](../development/ROOT-AUDIO-RECOVERY.md). O **CYTV Installer do Homebrew continua sem publicação**; use o instalador publicado para computador ou Android.

Homebrew Channel negou acesso a este instalador. No webOS 11, o Homebrew 0.7.3 precisa de uma atualização de compatibilidade dos desenvolvedores. Use o instalador publicado para computador ou Android até uma versão compatível do Homebrew incluir a correção. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

Somente candidato não publicado: se o acesso à API de firmware falhar por diretórios Root antigos graváveis, `cytv enable-firmware-access --edition root --repair-package-permissions` verifica o pacote atual com dados privados confiáveis e remove a escrita de grupo/outros apenas nos caminhos próprios do Root. Arquivos desconhecidos ou alterados interrompem o reparo. Perfil, escolha de Home e bloqueio de firmware são preservados; [detalhes (inglês)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

Somente no candidato não publicado: `cytv recover-system-rollback --edition root` trata uma reversão Root verificada em que todos os instaladores terminaram, mas o prazo de prontidão do launcher expirou. Exige o sinal real do launcher e recusa resultados de instalação desconhecidos. Preserva pacotes, código e chaves fixados, evidências de falha e a desativação explícita do controle Home. Um registro privado documenta a tentativa limitada. Repetir normalmente não estende o prazo. Só após os 120 segundos expirarem, sem sinal de prontidão aceito nem resultado de instalação desconhecido, `--new-recovery-attempt` arquiva todo o registro anterior por UUID/hash e abre explicitamente outra tentativa. A recuperação concluída permanece idempotente; não há tentativas automáticas. [Procedimento e limites (inglês)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0: o pacote de substituição inclui System Updater 1.1.2. Antes do OTA, substitua explicitamente 1.1.0 ou 1.1.1 com `cytv replace-system-updater --edition root`. Apenas o System Updater muda; apps Root/Root Updater, perfil completo e escolha de Home são preservados, e o estado anterior é arquivado. Operações desconhecidas ou incompletas bloqueiam a substituição. O requisito não bloqueia feeds No-root. [Procedimento (inglês)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Ajuda e outras instruções

Após falha ou interrupção, confira o estado e salve o relatório de diagnóstico daquela tentativa. A recuperação guiada pede confirmações separadas para remoção e reinstalação. Se o resultado for incerto, pare e preserve registros privados e arquivos de recuperação; nunca os apague para forçar outra tentativa. [Recuperação (inglês)](../RECOVERY.md). Para pedir ajuda, informe modelo, firmware, edição, versão do instalador, etapa com falha e resultado esperado/real; revise e remova segredos do relatório antes de compartilhar.

[Documentação](../README.md) · [Relatar um problema](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="python-opcional-para-root"></a>
<a id="testes-em-hardware-e-limites"></a>
<a id="bloqueio-de-firmware-lg-no-120"></a>
<a id="novidades-da-130-recuperação-guiada-no-computador"></a>
<a id="novidades-da-130--12"></a>
<a id="candidato-não-publicado-instalar-root-pelo-homebrew"></a>
<a id="candidato-não-publicado-recuperação-de-som-hdmi-root"></a>


## Temas: candidato em desenvolvimento

No candidato com suporte: **Configurações → Aparência**. **Classic** e **Alpine** são integrados e dispensam baixar o tema; Classic continua padrão. **Channel** é externo, do showcase. Nos testes da galeria: Escolha o tema e **Manter tema** em até **20 segundos**. **Reverter**, Back ou o fim do prazo restaura o anterior. Uma prévia interrompida faz Home iniciar com Classic. Temas integrados e baixados escolhidos na lista instalada são aplicados e salvos imediatamente, sem temporizador. Isso inclui temas recebidos do computador ou instalados por URL. Apenas Testar tema dentro da galeria inicia um teste de 20 segundos.

Os temas instalados aparecem em uma única linha com rolagem horizontal. O tema ativo fica sempre em primeiro lugar e seu cartão é destacado. Use Esquerda/Direita para percorrer a linha.

A galeria mostra apenas temas não instalados nesta TV. Classic, Alpine e os baixados ficam ocultos, mesmo com uma versão mais recente. Após remover um tema, ele reaparece. Atualize por URL ou transferência do computador.

Os cartões ficam diretamente em Aparência, ao lado das categorias. A galeria, a instalação por link e a transferência do computador abrem nesse painel; só um teste da galeria mostra Home temporariamente.

Abrir a galeria ou escolher Atualizar consulta as novidades revisadas no repositório principal sem atualizar Home nem recarregar a página. Novas entradas chegam após a integração normal; um candidato ainda não integrado pode mostrar o catálogo incluído. Sem conexão ou em caso de erro, usam-se entradas e prévias incluídas. Os temas integrados correspondem à versão instalada de Home. Abra a prévia de Channel e escolha **Baixar tema** (exige internet). Após baixar, teste e escolha **Manter tema** em até **20 segundos**. Temas instalados funcionam offline. **Adicionar por URL** continua disponível para links fixados.

Para testar um tema não publicado, abra primeiro **Configurações → Aparência → Receber do computador** na TV. Digite o endereço da TV e PIN de seis dígitos em **Send to TV** na prévia do computador, envie e escolha **Aplicar tema** na TV. O método principal conecta o PC à porta TCP **8879 da TV**, sem alterar o firewall do computador. Ambos devem estar na mesma rede doméstica confiável. O receptor fecha após um envio, cancelamento, saída ou **10 minutos**. O PIN não é salvo; o tema instalado funciona offline. Não é necessário publicar no GitHub.

Para um tema publicado, abra **Mais opções → Adicionar por URL** e digite o ID (por exemplo `102300a209`), `da.gd/102300a209` ou o link completo do GitHub. Home mostra o endereço da.gd antes de carregar e verifica o destino GitHub e o pacote. O autor pode copiar o ID das notas da versão ou de **TV link → Copy ID** na prévia.

Os pacotes publicados podem ainda não incluir esses controles. Testes de navegador não comprovam compatibilidade na TV. [Guia completo](../THEMES.md).

Temas mostra prévias dos temas integrados e de todos os que você instalou, inclusive offline. Um botão separado abre o catálogo publicado; instalar um tema pessoal não o publica.

No candidato, Aparência mostra prévias grandes dos temas instalados e indica o selecionado. A vitrine e receber do computador são as ações principais. Mais opções contém adicionar por URL, restaurar Classic e limpar temas baixados. As setas movem o foco entre cartões e botões; esquerda na borda volta às categorias.

Na prévia do navegador, Receber do computador explica os passos na TV; não inicia um receptor de TV no computador. Use Send to TV acima da prévia. Remover um tema baixado exige confirmação; se estiver ativo, Classic é restaurado primeiro. Cancelar mantém o tema.

<a id="categorias-de-configurações-candidato-não-publicado"></a>

## Categorias de configurações (1.5.0)

Nas duas edições, as categorias ficam à esquerda e as configurações à direita: tela inicial, Aparência (temas e colunas), Idioma, Atualizações de software e Avançado. No-root também tem Developer Mode; Root inclui firmware LG nas atualizações e som HDMI em Avançado. Cima/baixo navega na coluna, direita entra nas configurações e esquerda volta às categorias. Voltar retorna primeiro às categorias e depois fecha as configurações. Tab também alcança o botão para voltar ao Home.

Um ponto amarelo em Atualizações de software e no botão interno indica uma atualização disponível. Ambos desaparecem quando uma verificação bem-sucedida confirma que não há atualização; em caso de falha, o último estado confirmado é mantido.
