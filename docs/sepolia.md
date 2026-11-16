# Fase 7 — Sepolia y MetaMask

**Estado: fase 7 completada dentro del alcance académico, con limitación visual de MetaMask documentada.** Ambos contratos están verificados y el recorrido público aprobó 26 recibos exitosos y 55 comprobaciones finales. Se revisaron y archivaron los PNG originales de BUSD (916 en A, Sepolia) y CCNFT (ID 1, ERC721). La billetera muestra un marcador en lugar del certificado; el acceso externo a imagen y JSON fue confirmado por el usuario. Ver [resultado final y capturas](sepolia-results.md). La fase 6 conserva su cierre y evidencia original.

El recorrido conserva Solidity 0.8.19, optimizador de 200 runs, EVM Paris, OpenZeppelin 4.5.0 y la URI IPFS definitiva. No requiere una interfaz web. Sepolia es una red de prueba; BUSD es el ERC20 de demostración del TP y los NFTs son certificados simulados.

## Fundamento académico y recursos

| Referencia local | Aplicación en esta guía |
| --- | --- |
| Módulo 3, tema 10 | RPC, cuentas, fondos de prueba y publicación en Sepolia |
| Módulo 3, tema 14 | Scripts de interacción y lectura del estado de los contratos |
| Módulo 3, tema 15 | Despliegue de NFTs en Sepolia e importación por dirección e ID en MetaMask |
| Módulo 3, tema 21 | Comandos Makefile, interacciones y presentación de los metadatos |

Las opciones se contrastaron con `forge script --help` y `forge verify-contract --help` de Foundry 1.4.4. La lectura de claves sigue el ejemplo de [startBroadcast de Foundry](https://www.getfoundry.sh/reference/cheatcodes/start-broadcast): `vm.envUint` y `vm.startBroadcast(uint256)`. La clave se incorpora a los firmantes de Forge desde el script. El perfil local mantiene cuentas desbloqueadas, chain ID 31337 y nodo Anvil en loopback; el perfil público exige explícitamente `sepolia` y chain ID **11155111**. Los scripts rechazan cualquier otra combinación.

## Preparar los recursos locales

1. Crear cinco cuentas exclusivas para este TP: administrador, A, B, colector de fondos y colector de comisiones. Guardar sus direcciones y claves en el archivo local `.env`; usar claves hexadecimales con `0x` y 64 dígitos. Las direcciones deben ser distintas y corresponder a sus claves. La quinta cuenta recibe comisiones y no envía transacciones en este recorrido.
2. Obtener un endpoint **HTTPS de Ethereum Sepolia** en el proveedor RPC elegido. Copiarlo a `SEPOLIA_RPC_URL`. La [documentación de redes de Ethereum](https://ethereum.org/developers/docs/networks/) explica Sepolia y reúne enlaces a faucets. Solicitar ETH de prueba para admin, A, B y fondos usando sus direcciones públicas. La cantidad necesaria se determina por gas y precio actuales; los faucets pueden exigir cuenta y tener límites.
3. Crear una API key de Etherscan en su cuenta y completar `ETHERSCAN_API_KEY`. La [API de Etherscan](https://docs.etherscan.io/introduction) permite elegir red mediante `chainid`; esta automatización usa V2 y Sepolia.
4. Desde `cryptocampo/`, copiar el ejemplo una sola vez, completar los valores en un editor local y ejecutar el diagnóstico:

```bash
cp .env.example .env
chmod 600 .env
# Completar .env en un editor local; no imprimirlo ni pasar sus valores como argumentos.
make sepolia-doctor
```

`.env.example` documenta los doce nombres requeridos, sin claves ni ejemplos de claves. El ejecutor lee valores literales; admite comillas y `export`, sin expansión de variables, sustituciones de comandos ni comentarios al final de un valor. El entorno del proceso prevalece sobre `.env`. No es necesario hacer `source .env`.

El diagnóstico comprueba red, las cinco direcciones y firmantes, cuentas sin código, Forge/Cast/Anvil 1.4.4, revisiones limpias de bibliotecas y parámetros de los artefactos. Calcula una reserva inicial orientativa para cada firmante a partir de los recibos reales de fase 6, con margen de gas del 50 % y máximo EIP-1559 calculado como el mayor entre dos veces el precio sugerido por RPC y dos veces la comisión base más la prioridad recomendada. El colector de comisiones puede comenzar con cero ETH. Antes de publicar cada etapa se simula el script completo y se exige ETH para su gas estimado con margen; antes de cada transacción se vuelve a estimar y comprobar saldo. El diagnóstico inicial no sustituye esas simulaciones.

## Publicar y comprobar el recorrido

Todos los comandos leen las claves desde el entorno de los scripts. Los argumentos contienen nombres de red y direcciones públicas. `RPC_URL` y `STATE` pertenecen a Anvil; para Sepolia se utiliza `SEPOLIA_STATE` (predeterminado `.tools/sepolia/state.json`). Conservar siempre el mismo estado para esta demostración.

```bash
make sepolia-deploy
make sepolia-verify
make sepolia-configure
make sepolia-fund
make sepolia-approvals
make sepolia-enable
make sepolia-buy
make sepolia-list
make sepolia-trade
make sepolia-claim
make sepolia-check
```

También existe `make sepolia-demo`, que continúa desde la próxima etapa pendiente y verifica Etherscan antes de configurar. Una ejecución puede detenerse si faltan dos confirmaciones o la RPC falla: reconciliar y repetir el comando usando el mismo estado.

`deploy` simula los scripts existentes, publica BUSD y CCNFT y obtiene las direcciones desde los recibos. Se compara el bytecode desplegado con los artefactos exactos y se conserva en las consultas registradas. Los constructores no tienen argumentos. `verify` usa `forge verify-contract --watch` con Etherscan, Solidity `v0.8.19+commit.7dd6d404`, 200 runs y Paris. Después consulta [getsourcecode de Etherscan](https://docs.etherscan.io/api-reference/endpoint/getsourcecode) y exige fuente, nombre, compilador, optimizador, EVM y argumentos coincidentes. La configuración requiere ambas verificaciones registradas. Una falla de Etherscan se reintenta con `sepolia-verify`, conservando los contratos desplegados.

`configure` fija token, colectores, nominales, límite, lote, comisiones, beneficio y metadatos, conservando las operaciones deshabilitadas. `fund` distribuye 1000 BUSD a A, 1000 a B y una reserva de 10 al colector. Las aprobaciones son exactamente A **204**, B **121,2** y fondos **105 BUSD**, a favor de CCNFT. `enable` exige la financiación y las tres aprobaciones completas.

El recorrido compra dos NFTs de nominal 100, publica uno a 120 BUSD, lo revende a B y lo reclama por 105. Los IDs se descubren consultando la enumeración en cadena después de comprar, y se guardan como `sold_id` y `kept_id`; no se presupone un ID inicial. `Publish.s.sol` publica individualmente las transacciones del plan simulado: valida firmante, nonce, destino, contratos y código de creación. Las guardas académicas de configuración y operaciones se ejecutan en los scripts originales durante la simulación de la etapa.

Los verificadores reutilizados comprueban después de cada etapa: bytecode, propietario, configuración, saldos, autorizaciones, nominal, propietarios, enumeraciones, metadatos, publicaciones y reversiones esperadas. El cierre público requiere las once etapas y las verificaciones de ambos contratos. El resultado final debe ser:

| Control | Resultado exigido |
| --- | --- |
| Variaciones BUSD desde la financiación | A −84; B −16,2; fondos +95; comisiones +5,2 |
| A | Un NFT vigente, `kept_id`, URI definitiva y nominal 100 BUSD |
| NFT revendido | `sold_id` quemado; nominal y publicación cero |
| Nominal total / saldo fondos | 100 / 105 BUSD |
| Autorizaciones A/B/fondos | Todas consumidas: cero |
| Lista de ventas | Vacía |

## Evidencia y recuperación de interrupciones

Cada invocación crea `.tools/sepolia/FECHA/` con `result.json`, consultas y logs filtrados. El estado se escribe mediante reemplazo atómico **antes del primer envío**. El plan conserva remitente, nonce, destino, valor cero y calldata; cada recibo añade su enlace público de Etherscan. Las direcciones verificadas incluyen enlaces `#code`. Los resultados y logs filtran RPC, credenciales de su ruta/query, API key y claves privadas, incluidas sus representaciones hexadecimales y decimales largas. `.tools/sepolia-private/FECHA/` es almacenamiento interno privado de Forge, separado de la evidencia y excluido de Git; sus JSON se filtran al terminar cada comando. No adjuntar ese directorio interno: tras una terminación abrupta puede contener archivos de Forge todavía sin filtrar. Para entregar evidencia, copiar únicamente `result.json`, logs filtrados y los JSON `*-etherscan.json`; revisar también las capturas.

Ante un corte de terminal, timeout o problema de proveedor:

```bash
make sepolia-reconcile
# Repetir la etapa interrumpida, o continuar por la próxima pendiente:
make sepolia-demo
```

La reconciliación localiza las transacciones por **remitente y nonce**, incluso si Forge no alcanzó a guardar el hash. Busca su bloque, compara calldata/destino/valor con la intención, comprueba recibo canónico exitoso y exige dos confirmaciones. Un nonce pendiente impide reenviar; un recibo fallido, otra transacción con ese nonce o un estado inconsistente detienen la automatización. Un prefijo confirmado se conserva y solo se publica el sufijo restante. Si todas las transacciones están confirmadas pero faltaba la comprobación de estado, se completa esa comprobación antes de avanzar. Las etapas anteriores vuelven a comprobarse contra recibos canónicos.

No borrar el estado ni cambiar de archivo para continuar una demostración interrumpida. Mantener esas cuentas reservadas para el recorrido, sin enviar operaciones concurrentes desde MetaMask. El archivo de estado se bloquea durante cada comando. Se rechazan cambios de fuentes, herramientas del proyecto o actores desde el primer checkpoint; conservar el checkout hasta completar el recorrido. Las recuperaciones de versión se limitan a las correcciones revisadas del 15/11/2026. La corrección inicial de comisiones exige los hashes exactos del ejecutor y sus pruebas anteriores, contratos y scripts sin cambios, plan original de dos despliegues y ambos nonces libres en cadena. Conserva una copia del estado anterior y registra la actualización antes de continuar. Si un recibo falla, conservar evidencia y revisar el caso antes de intervenir: no se reintenta el pago automáticamente. La recuperación depende de la disponibilidad de consultas históricas del proveedor; si no están disponibles, se detiene con evidencia.

Las evidencias de fase 6 siguen siendo locales. Una simulación o prueba de recuperación con dobles RPC no acredita publicación en Sepolia.

## Importar en MetaMask y cerrar la fase

1. Activar la visualización de redes de prueba y seleccionar **Sepolia** en MetaMask. Importar las cuentas de prueba localmente si todavía no están en esa billetera. Nunca capturar pantallas de claves ni recuperación.
2. En la pestaña de tokens, importar como token personalizado la dirección **BUSD** registrada en `context.addresses` del último `result.json`. Confirmar símbolo BUSD y **18 decimales**. La [ayuda oficial de MetaMask](https://support.metamask.io/hc/en-us/articles/360015489031) explica la importación por contrato.
3. Seleccionar A. En NFTs, importar manualmente la dirección **CCNFT** y el **`context.kept_id`** decimal obtenido de la evidencia final. Seguir la [importación manual de NFTs](https://support.metamask.io/nfts/nft-tokens-in-your-metamask-wallet/). El NFT reclamado está quemado: usar el vigente que conserva A. Comprobar que la imagen resuelva desde la URI IPFS definitiva; registrar cualquier limitación real de visualización de MetaMask, sin fabricar una captura.
4. Guardar capturas reales de red Sepolia, saldos finales y NFT vigente/imagen. Registrar fecha, dirección de A, dirección CCNFT e ID mostrado. Adjuntar los enlaces de ambos contratos verificados y de despliegue, compra, publicación, reventa y reclamo desde los recibos.
5. Crear el registro público de cierre en `docs/` con enlaces, evidencia filtrada, capturas y resultado de `sepolia-check`. La fase 7 se cierra solamente cuando ambos contratos están verificados, el recorrido público pasó y las capturas reales están disponibles.

**Cierre actual:** importaciones y capturas originales revisadas y archivadas. El NFT 1 permanece en A. La imagen dentro de MetaMask continúa como limitación visual conocida. La preparación de la entrega corresponde a fase 8.

## Corrección del primer intento público

El intento `20261115T211530087585Z` simuló el despliegue y guardó los nonces 4 y 5, pero la RPC rechazó el primer envío con `max priority fee per gas higher than max fee per gas`. El ejecutor fijaba el máximo a partir de `eth_gasPrice` y dejaba que Forge eligiera la prioridad por separado. Ahora consulta comisión base, `eth_maxPriorityFeePerGas` y precio sugerido; utiliza un máximo que cubre base y prioridad y pasa ambos valores explícitos a Forge. La relación entre ambas comisiones está definida en [EIP-1559](https://eips.ethereum.org/EIPS/eip-1559).

Para este intento, ejecutar primero `make sepolia-reconcile` en la terminal del usuario. Esa comprobación acepta la corrección solo después de confirmar que no hay transacciones confirmadas ni pendientes con los nonces originales. Después puede repetirse `make sepolia-deploy` con el mismo archivo de estado. Si se detecta un nonce ocupado o una transacción confirmada, la recuperación se detiene para revisar los recibos. Ver [evidencia de diagnóstico y pruebas](evidence/sepolia-fee-fix-2026-11-15/review.json).

## Recuperación del CREATE fallido por límite de gas

El envío `0xaea382d25998854741a517145c8911a9ef8870710b19afbe4677e104f0b6c523` falló con `status: 0x0`. El recibo aportado por el usuario registra 832.904 unidades de gas consumidas, iguales al límite enviado. El ejecutor había recibido una estimación RPC de 4.165.136, pero Forge publicó con una estimación local menor. Esa diferencia de límites es un defecto del ejecutor; no se atribuye una causa de hardfork sin evidencia adicional.

Se conservaron el log, broadcast público y recibo reportado. La publicación ahora usa `--skip-simulation --gas-estimate-multiplier 150`: en [Forge 1.4.4](https://raw.githubusercontent.com/foundry-rs/foundry/v1.4.4/crates/script/src/broadcast.rs), esa opción activa `eth_estimateGas` justo antes de firmar y enviar, para transacciones sin gas fijo. El broadcast fallido tiene `isFixedGasLimit: false`. Se mantienen la simulación inicial por etapa, las guardas Solidity y la estimación RPC del ejecutor para comprobar ETH suficiente. Los parámetros de compilación y los contratos permanecen intactos.

La preparación del reintento es una acción explícita de solo lectura en cadena:

```bash
make sepolia-recover-deploy FAILED_TX=0xaea382d25998854741a517145c8911a9ef8870710b19afbe4677e104f0b6c523
```

Exige el estado y hashes conocidos del ejecutor anterior, ningún despliegue exitoso, la transacción idéntica a la primera intención CREATE, recibo canónico fallido con dos confirmaciones, consumo de todo el gas asignado, logs vacíos, ausencia de código en la dirección de creación y nonce actual/pendiente igual a 5. Además, ambas creaciones deben simular correctamente por RPC y disponer de ETH suficiente. Después respalda el estado completo, conserva el intento y su recibo en `failed_deployments`, y prepara BUSD/CCNFT con nonces 5 y 6. Repetir esa recuperación no vuelve a desplazar los nonces. Un recibo exitoso, otro nonce ocupado, código existente, cambios ajenos o una simulación fallida detienen la recuperación.

Cuando la recuperación termine correctamente, puede ejecutarse `make sepolia-deploy`. Las aprobaciones y operaciones económicas todavía no comenzaron. La [revisión y pruebas](evidence/sepolia-rpc-gas-fix-2026-11-15/review.json) distingue el recibo aportado, las comprobaciones locales y la reconciliación en cadena pendiente desde la terminal del usuario.

## Despliegue público confirmado

| Contrato | Dirección en Sepolia | Transacción exitosa |
| --- | --- | --- |
| BUSD | [0x2a37e9ac75569eea1537bdb7ba6beb5b6cd8f710](https://sepolia.etherscan.io/address/0x2a37e9ac75569eea1537bdb7ba6beb5b6cd8f710) | [Despliegue BUSD](https://sepolia.etherscan.io/tx/0x35f2d2609f76de72366c3b21fac4d39052e8df0c8f2ab0b94d3246eee83ee114) |
| CCNFT | [0xbd6c1c5f5690d92021bff186597c2b71daf97a34](https://sepolia.etherscan.io/address/0xbd6c1c5f5690d92021bff186597c2b71daf97a34) | [Despliegue CCNFT](https://sepolia.etherscan.io/tx/0xbe5bfb3b8aaca4fd3ba1297b2a3dc33a1e6d196a0623863904a551426747b12d) |

La ejecución posterior `20261115T214054458364Z` completó la verificación de ambos códigos fuente en Etherscan, con Solidity 0.8.19, optimizador 200, Paris y constructores sin argumentos. La configuración posterior `20261115T214350869866Z` confirmó once recibos y el estado. La distribución y las operaciones posteriores también terminaron; `sepolia-check` aprobó el recorrido completo. El siguiente paso es importar los tokens en MetaMask y tomar las capturas.

## Datos finales para MetaMask

Seleccionar **Sepolia** y la cuenta **TP Comprador A**, dirección `0x2564dc8376be1e561086797e66835202d78362f8`.

- BUSD: contrato `0x2a37e9ac75569eea1537bdb7ba6beb5b6cd8f710`, símbolo `BUSD`, 18 decimales, saldo final **916 BUSD**.
- NFT: contrato `0xbd6c1c5f5690d92021bff186597c2b71daf97a34`, ID decimal **1**, vigente y propiedad de A.

Los demás saldos finales de BUSD son B **983,8**, fondos **105** y comisiones **5,2**. La tabla de variaciones acordadas sigue vigente. Registrar las capturas de importación de BUSD y del NFT vigente sin mostrar claves ni el archivo de entorno.

## Primera captura real de MetaMask

El usuario adjuntó en la conversación una captura del NFT 1: se observan ID 1, estándar ERC721 y dirección abreviada compatible con CCNFT. La imagen aparece como un marcador genérico, por lo que la presentación del certificado sigue pendiente. El archivo binario no está disponible en la ruta indicada dentro del entorno del agente: se conserva la [revisión visual](evidence/metamask-import-2026-11-15/review.json), sin declarar una copia ni hash de esa captura. La captura de BUSD fue reportada, pero todavía no fue aportada para inspección. La fase 7 continúa abierta.

El JSON local conserva el campo `image` con el CID definitivo; no se modificaron los archivos publicados ni la URI en cadena. Las consultas web de esta sesión a los gateways fueron inaccesibles y no acreditan disponibilidad actual. El siguiente diagnóstico es abrir la imagen pública desde el navegador del usuario y comprobar después la configuración de contenido multimedia de MetaMask.

El usuario abrió el enlace público de la imagen en su navegador y confirmó «veo un certificado de demostracion». Esto acredita acceso visual reportado por el usuario, sin afirmar una nueva descarga automatizada ni un hash actual. La imagen dentro de MetaMask sigue pendiente. El diagnóstico continúa por la configuración de contenido multimedia/Funcionalidad básica y la resolución de metadatos desde la billetera.

El usuario también abrió los metadatos por Pinata y pegó `name`, `description` e `image`, coincidentes con los campos locales esperados. Se revisaron únicamente archivos públicos de programa de MetaMask 13.56.0.0 instalado: en Privacidad existe un control separado de pasarela IPFS. No se consultó el almacenamiento de la billetera ni sus preferencias configuradas. El siguiente paso es comprobar en la interfaz si esa pasarela está habilitada y qué host utiliza. La carga por Pinata está reportada; todavía no se confirmó la ruta de descarga que usa MetaMask.

## Alcance de la limitación visual de MetaMask

Después de las comprobaciones y el intento de actualización, el usuario indicó que MetaMask sigue mostrando el marcador genérico. La causa exacta no quedó demostrada; no se atribuye a SVG, CORS, caché o gateway como hecho confirmado. Se mantiene la evidencia de propiedad, ID 1 vigente, contratos verificados y recorrido público aprobado. Tanto la imagen por Pinata como los JSON por Pinata y dweb.link fueron accesibles en el navegador del usuario.

Se releyeron las indicaciones originales de entrega (`Consignas-ProyectoFinal/README.md`): requieren una captura de CCNFT y BUSD **importados a MetaMask**, sin exigir expresamente que el certificado se renderice dentro de la billetera. La carga de la imagen se registra como limitación visual, sin presentarla como verificada. Para completar la evidencia se necesitan los archivos originales de la captura de CCNFT importado y la de BUSD; esta última todavía no se inspeccionó. Puede adjuntarse el certificado y su enlace IPFS por separado, identificándolos claramente como evidencia externa a MetaMask. El despliegue y la URI definitiva se conservan.

## Cierre con los archivos originales

El usuario facilitó las rutas de las dos capturas originales, ahora disponibles para lectura. Se abrieron directamente, se inspeccionaron y se copiaron sin modificaciones. BUSD muestra 916 BUSD en la cuenta A y filtro Sepolia. CCNFT muestra ID 1, ERC721 y la dirección abreviada esperada; conserva el marcador genérico de imagen. La evidencia exigida de importación queda satisfecha y la limitación permanece declarada. Ver [resultado final](sepolia-results.md) y [revisión de capturas](evidence/metamask-import-2026-11-15/review.json). Las secciones de diagnóstico anteriores conservan el estado observado en cada momento.
