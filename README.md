# CryptoCampo NFT

Contratos para certificados agrícolas de demostración y pagos con un token ERC20 BUSD. Los certificados no acreditan existencias físicas verificadas y el token no tiene respaldo en dólares.

Se incluyen BUSD, que emite 10 millones de tokens con 18 decimales al desplegador, y CCNFT, con compra, publicación, reventa, reclamo y metadatos compartidos. **Fases 2 y 3 validadas en GitHub Actions al 15/11/2026:** entorno con versiones y revisiones fijadas, compilación y formato satisfactorios, 48 pruebas aprobadas, cobertura revisada y 35 transacciones exitosas para medir gas. CCNFT alcanza 100 % de líneas, sentencias y funciones y 97,53 % de ramas; los dos rechazos restantes de `trade` están justificados como inalcanzables mediante las funciones públicas actuales. El cierre abarca el rango medido, sin establecer un máximo global de gas. La fase 4 acredita **publicación y resolución verificadas**: imagen y JSON recuperados por Pinata y Filebase, y cinco comprobaciones aprobadas con la URI definitiva en Anvil. La presentación en billetera y Sepolia quedan para fases posteriores; ambos workflows remotos fueron confirmados en verde por el usuario y sus enlaces están registrados. Ver [evidencia IPFS y Anvil](docs/ipfs-verification-2026-11-15.md). Ver [evidencia y revisión de ramas](docs/ci-validation-2026-11-15.md).

## Entorno

Se requieren Linux x86_64, Bash, Git, curl, tar e install, además de acceso a GitHub y al servidor de compiladores de Solidity.

| Componente | Versión | Revisión |
| --- | --- | --- |
| Foundry | v1.4.4 | 05794498bf47257b144e2e2789a1d5bf8566be0e |
| Solidity | 0.8.19 | Configurada en foundry.toml |
| OpenZeppelin Contracts | v4.5.0 | a5445b0afb8b350417b6e6ab3160554967bc151f |
| forge-std | v1.9.7 | 77041d2ce690e692d6e03cc812b57d1ddaa4d505 |

Referencias: [Foundry](https://github.com/foundry-rs/foundry/releases/tag/v1.4.4), [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts/releases/tag/v4.5.0) y [forge-std](https://github.com/foundry-rs/forge-std/releases/tag/v1.9.7).

Desde la raíz del repositorio:

```bash
bash tools/setup.sh
export PATH="$PWD/.tools/bin:$PATH"
cp .env.example .env
forge build
forge test -vv
forge fmt --check
forge coverage
forge test --gas-report
```

La instalación guarda los binarios en `.tools/bin/` y las dependencias en `lib/`, sin modificar la configuración del usuario ni crear commits. Las bibliotecas se descargan por revisión fija y se comprueba que una instalación existente conserve esa revisión sin cambios locales. Ambos directorios se regeneran con el instalador y están excluidos de Git. Forge descarga Solidity 0.8.19 durante la primera compilación.

Las variables del ejemplo se reservan para futuras interacciones con Sepolia; no son necesarias para compilar o probar. Los archivos de entorno locales quedan excluidos de Git.

## Contratos y operaciones

CCNFT hereda de `ERC721Enumerable`, `Ownable` y `ReentrancyGuard`, con nombre `CryptoCampo NFT` y símbolo `CCNFT`. Comienza con las tres operaciones deshabilitadas. Los IDs comienzan en cero, se reservan antes de `_safeMint` y no se vuelven a emitir después de una quema.

Los importes usan unidades mínimas del ERC20: para BUSD, `100 ether` en Solidity representa 100 BUSD. Las tasas se expresan en puntos básicos (`10_000 = 100 %`) y la división entera trunca sobre el total de cada operación.

| Función | Efecto y pagos |
| --- | --- |
| `buy(uint256 value, uint256 amount)` | Emite un lote de nominal permitido. Cobra `value * amount` al comprador para fondos, más `principal * buyFee / 10_000` para comisiones. Aumenta `totalValue` por el principal. |
| `putOnSale(uint256 tokenId, uint256 price)` | Solo el propietario puede publicar con precio positivo. Una nueva publicación actualiza el precio sin duplicar el ID. |
| `trade(uint256 tokenId)` | Cobra al comprador el precio publicado para el vendedor, más `price * tradeFee / 10_000` para comisiones. Transfiere mediante `_safeTransfer`, elimina la publicación y conserva el nominal. Rechaza la compra al propio vendedor. |
| `claim(uint256[] calldata tokenIds)` | Quema los NFTs del llamador y elimina nominales y publicaciones. Cobra al colector de fondos la suma nominal más `principal * profitToPay / 10_000`. Reduce `totalValue` solo por el nominal. Los IDs repetidos revierten toda la operación. |

`totalValue` es el nominal vigente, equivalente a la suma de `values` de los NFTs en circulación. Los reclamos liberan capacidad de emisión. El principal de las compras va directamente al colector; CCNFT no custodia BUSD. El colector debe disponer de saldo y aprobar a CCNFT para financiar el pago completo de los reclamos. Compradores iniciales y secundarios también aprueban a CCNFT por principal o precio **más comisión**.

Todos los setters de la plantilla mantienen sus nombres y tipos, y requieren `onlyOwner`. Se rechazan direcciones cero, direcciones de token sin código, nominales y precios cero, lotes configurados en cero y comisiones mayores que 10.000. `profitToPay` conserva todo el rango `uint32`, sin límite adicional del 100 %. Un límite de emisión cero impide nuevas compras; reducirlo no altera el nominal existente ni impide reclamar.

Para comprar se configuran token, ambos colectores, nominales, lote y límite de emisión. Reventa requiere token y colector de comisiones; reclamo requiere token y colector de fondos. Las habilitaciones se administran con `setCanBuy`, `setCanTrade` y `setCanClaim`.

Las cuatro operaciones tienen `nonReentrant`, incluida la publicación durante callbacks de recepción de NFTs. Cada pago comprueba el booleano de `transferFrom`; si la comisión es cero se omite ese cobro. Un fallo revierte pagos, emisiones, quemas y publicaciones. En reventa, la publicación se elimina y la propiedad se actualiza antes de callbacks y cobros. Las tres transferencias públicas de ERC721 revierten con `Not Allowed`, incluso con aprobación del NFT.

Se conservan las auxiliares `find`, `addToArray` y `removeFromArray`: búsqueda lineal, reemplazo por el último elemento y `pop`. La lista no conserva el orden. Publicar, actualizar o eliminar cuesta O(n) en la cantidad de publicaciones; reclamar un lote puede costar O(lote × publicaciones). `maxBatchCount` no limita la longitud global de la lista. La matriz de Anvil midió listas de 1, 10 y 100 y lotes de 1 y 10: comprar diez NFTs consumió 1.475.810 gas; reclamar diez publicados al final de una lista de cien, 1.220.864. Son recibos de escenarios específicos, sin cotas garantizadas para listas mayores, otros ERC20 o receptores contrato. Ver [tabla y límites de interpretación](docs/gas-scenarios.md).

Los eventos `Buy`, `PutOnSale`, `Trade` y `Claim` identifican participantes, IDs y nominal o precio. `Trade` incluye la comisión. `BuyPayment` y `ClaimPayment` registran principal y comisión o beneficio de todo el lote, para reflejar correctamente el redondeo agregado.

El recorrido de aceptación compra dos NFTs de 100 BUSD con 2 % de comisión, revende uno a 120 con 1 % y lo reclama con 5 % de beneficio (105 BUSD). La prueba comprueba eventos, autorizaciones exactas, variaciones de saldo A: −84; B: −16,2; fondos: +95; comisiones: +5,2 BUSD, y nominal final de 100 BUSD. **La prueba pasó en el registro de CI recibido el 15/11/2026.**

## Metadatos compartidos — publicación y resolución verificadas

[`assets/certificate.svg`](assets/certificate.svg) es un certificado agrícola sencillo con el texto visible «Certificado de demostración». Se usan formas y texto SVG, siguiendo la separación entre imagen y metadatos tratada en la cursada. [`assets/metadata.json`](assets/metadata.json) contiene solo `name`, `description` e `image`, sin IDs ni nominales individuales. Todos los NFTs usan la misma ficha; la propiedad y el nominal se consultan en el contrato.

`setMetadataURI(string)` requiere `onlyOwner`, rechaza cadenas vacías con `Empty metadata URI` y emite `MetadataURIUpdated(string metadataURI)` en cada configuración o actualización. El administrador puede cambiar la ficha de todos los NFTs vigentes y futuros. El constructor sigue sin argumentos.

`tokenURI(uint256)` comprueba primero la existencia del NFT y revierte con `Token does not exist` para IDs inexistentes o quemados. Para un NFT vigente devuelve la cadena compartida, inicialmente vacía. Una reventa conserva esa URI. La configuración de metadatos no habilita operaciones ni modifica saldos, publicaciones o nominales; comprar, revender y reclamar funcionan sin configurar la URI.

El JSON preparado para publicar referencia la imagen mediante `ipfs://bafkreidkykrr5euk77wd3srhwatez6bfrkre5jv775mjggz6wx6sihrhd4`. Conserva únicamente nombre, descripción de demostración e imagen. Para revisar los archivos locales desde el directorio del proyecto:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory assets
```

Abrir `http://127.0.0.1:8000/certificate.svg` y `http://127.0.0.1:8000/metadata.json`. En una futura demostración local, el propietario podrá llamar a `setMetadataURI("http://127.0.0.1:8000/metadata.json")`. Las pruebas Solidity comparan cadenas; no descargan recursos ni prueban accesibilidad HTTP. `https://metadata.example.invalid/updated.json`, usado al probar actualizaciones, es otro marcador de prueba sin publicación. Estas referencias locales no sirven para billeteras de terceros.

La publicación se realiza manualmente desde Pinata, eligiendo **IPFS público** y subiendo cada archivo individualmente, sin carpeta contenedora. Primero se sube y fija `certificate.svg`; se comprueba su CID por dos gateways; luego se establece `image` como `ipfs://<CID_REAL_DE_IMAGEN>` y se retira de la descripción la frase sobre pruebas locales. Solo después se sube y fija el JSON definitivo. Ambos archivos deben permanecer fijados. Ver [instrucciones de publicación de Pinata](https://docs.pinata.cloud/files/uploading-files) y [pinning en IPFS](https://docs.ipfs.tech/how-to/pin-files/).

El [registro de publicación](docs/ipfs-publication.json) contiene ambos CIDs, URIs, hashes SHA-256, fechas y evidencia de pinning. La ejecución del 15/11/2026 recuperó imagen y JSON mediante el gateway público de Pinata y el gateway independiente de Filebase: cuatro respuestas HTTP 200, con bytes idénticos a los archivos locales. La imagen recuperada se renderizó y revisó a 1200 × 800. El intento anterior con `ipfs.io` devolvió 429 y permanece documentado; se eligió Filebase explícitamente manteniendo los mismos CIDs.

La URI definitiva configurada y comprobada en el CCNFT temporal es `ipfs://bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4`. Anvil aprobó la URI común de dos NFTs, su conservación tras la reventa, las reversiones de IDs quemados e inexistentes y el rechazo de cambios por terceros. El [informe completo](docs/evidence/ipfs-publication-verified-2026-11-15.json) registra las cuatro descargas, las cinco comprobaciones y 25 transacciones de despliegue, configuración y operaciones. Los contratos conservan sus reglas económicas.

Ambos archivos deben mantenerse fijados en Pinata. La confirmación de subida pública y pinning automático procede de la captura y las declaraciones del usuario, conservadas junto con el registro; la recuperación pública está probada mediante las descargas. No se usaron credenciales de Pinata.

```bash
# Siempre disponible, sin red ni Foundry:
python3 tools/verify-metadata.py --local-only
python3 -m unittest discover -s tools -p 'test_verify_metadata.py' -v

# Tras registrar el CID de la imagen y confirmar su pinning:
python3 tools/verify-metadata.py --image-only --record

# Reproducir la ejecución satisfactoria con Pinata y Filebase:
bash tools/setup.sh
python3 tools/verify-metadata.py --independent-gateway filebase --record

# Otro operador independiente disponible (respondió 429 en el intento previo):
python3 tools/verify-metadata.py --independent-gateway ipfs.io --record

# Probar solo la URI en Anvil, sin nuevas descargas IPFS:
python3 tools/verify-metadata.py --anvil-only --record
```

El verificador compara los bytes de ambos archivos con los locales mediante el gateway público de Pinata y el operador independiente seleccionado (`ipfs.io` o Filebase), valida JSON/SVG y comprueba la referencia a la imagen. También inicia un Anvil temporal, aunque un gateway no responda, despliega BUSD y CCNFT con los parámetros de demostración y verifica la URI compartida antes y después de revender, las reversiones de IDs quemados e inexistentes y el rechazo de cambios por terceros. Los resultados y descargas se guardan en `.tools/metadata-verification/`. Con `--record`, el manifiesto registra el intento, incluso si falla. `--anvil-only` guarda su resultado en `anvil_verification` y `.tools/metadata-verification/anvil/`, conservando el informe de descargas. Su éxito acredita solo la URI en Anvil. Un fallo deja el estado `pending` y devuelve código 1.

El workflow **Verificar publicación IPFS y URI en Anvil** se activa solo mediante `workflow_dispatch` y conserva un artefacto con la evidencia, incluso ante fallos del verificador. Los pushes y PRs ejecutan únicamente la validación local y las pruebas del verificador, además de los controles de contratos existentes. Las pruebas unitarias Solidity mantienen sus referencias locales y no dependen de IPFS.

La [guía de publicación y evidencia](docs/ipfs-publication.md) detalla cómo completar el registro y revisar la imagen recuperada. El [resultado observado](docs/ipfs-verification-2026-11-15.md) es **publicación y resolución verificadas**, con cuatro descargas coincidentes, confirmación de pinning, revisión visual y comprobación real en Anvil. La fase 4 queda cerrada: ambos workflows remotos fueron confirmados en verde por el usuario y [sus enlaces están registrados](docs/evidence/ci-runs-received-2026-11-15.json). Para reproducir el resultado satisfactorio, usar `filebase` como operador independiente. El agente no inspeccionó los logs remotos. La presentación en una billetera permanece pendiente para una fase posterior, junto con Sepolia.

## Organización y comprobación

- `src/`: contratos activos.
- `test/BUSD.t.sol`: metadatos, suministro y asignación inicial de BUSD.
- `test/CCNFTAdmin.t.sol`: configuración, permisos y habilitaciones.
- `test/CCNFTOperations.t.sol`: recorrido de aceptación, eventos, límites, publicaciones, enumeración, reclamos y redondeo.
- `test/CCNFTSecurity.t.sol` y `test/mocks/`: atomicidad ante fallos de saldo, autorización, segundo cobro, ERC20 falso y callbacks ERC721/ERC20.
- `test/CCNFTFuzz.t.sol`: cuatro pruebas parametrizadas de fórmulas y conservación del nominal, con 256 casos por prueba.
- `test/CCNFTMetadata.t.sol`: URI inicial, permisos, cadena vacía, eventos, actualización común, reventa, existencia y separación de la lógica económica.
- `script/`: reservado para scripts de despliegue e interacción.
- `assets/`: certificado SVG y JSON compartido preparado para publicar, con la URI IPFS real de la imagen.
- `docs/`: evidencia de contratos, gas y registro de publicación IPFS.
- `tools/`: instalación reproducible, medición de gas y verificación de metadatos.

El paso de CI **Medir gas por tamaño de lista y lote** ejecuta `tools/measure-gas.py` en un Anvil temporal. Las 35 transacciones con listas de 1, 10 y 100 publicaciones y lotes de 1 y 10 completaron exitosamente, usando gas de recibos y separando la preparación del estado. Se registraron commit, versiones y revisiones de dependencias. Ver [método, resultados y límites](docs/gas-scenarios.md).

La configuración fija Solidity 0.8.19, EVM Paris y optimización con 200 ejecuciones. Las pruebas se ejecutan localmente, sin RPC ni cuentas externas.

Hay 48 funciones de prueba: 2 de BUSD y 46 de CCNFT, incluidas las 4 pruebas fuzz. Se conservaron las 39 originales y se añadieron 8 de metadatos y una de configuración incompleta de `claim`; la prueba de permisos administrativos incluye el nuevo setter y la de interfaces comprueba ERC721Metadata. Las 48 pasaron en el último registro de cobertura recibido el 15/11/2026, sin fallos ni omisiones. CCNFT alcanzó 100 % de líneas, sentencias y funciones y 97,53 % de ramas (79/81). La justificación de las dos guardas restantes de `trade` está en la [revisión de cobertura](docs/ci-validation-2026-11-15.md).

## Estado de verificación al 14/11/2026

`bash tools/setup.sh` se volvió a intentar tras incorporar los metadatos y terminó con código 6: `curl: (6) Could not resolve host: github.com`. No se instalaron Foundry ni bibliotecas. Las revisiones de la tabla están fijadas en el instalador, pero no se pudieron contrastar contra dependencias descargadas. Los comandos y códigos de salida están en la [evidencia de ejecución](docs/verification-2026-11-14.txt); los alcances de la revisión están en la [nota de validación](docs/validation.md).

| Comprobación | Resultado real |
| --- | --- |
| `bash -n tools/setup.sh` | Correcto. |
| Lectura con `tomllib` | Solidity 0.8.19, remappings y 256 casos fuzz comprobados. |
| `git check-ignore --no-index` | 38 rutas representativas excluidas y 16 rutas de proyecto versionables comprobadas; incluye secretos, artefactos, herramientas y bibliotecas. |
| Revisión estática local | 10 fuentes Solidity revisadas. Suministro BUSD conservado y hashes de las referencias académicas sin cambios durante esta revisión. No sustituye a la compilación. |
| JSON y SVG | JSON válido con `name`, `description` e `image`; SVG XML válido, renderizado y revisado visualmente. Imagen y ficha comunes, sin nominales ni IDs. |
| `.tools/bin/forge build` | Bloqueado: ejecutable inexistente (código 127). |
| `.tools/bin/forge test -vv` | Bloqueado: ejecutable inexistente (código 127). |
| `.tools/bin/forge fmt --check` | Bloqueado: ejecutable inexistente (código 127). |
| `.tools/bin/forge coverage` | Bloqueado: ejecutable inexistente (código 127). |
| `.tools/bin/forge test --gas-report` | Bloqueado: ejecutable inexistente (código 127). |

En esa comprobación local del 14/11/2026 no se obtuvieron resultados de pruebas, cobertura ni gas. El [registro posterior de CI del 15/11/2026](docs/ci-validation-2026-11-15.md) permite cerrar las fases 2 y 3: compilación y formato satisfactorios, 48 pruebas aprobadas, cobertura revisada, reporte agregado de gas y 35 recibos de medición por escenario, con entorno identificado. En el avance de fase 4 se reintentó `bash tools/setup.sh`: continúa el error DNS al resolver `github.com`. La nueva validación local y las 14 pruebas iniciales del verificador aprobaron. El usuario instaló después Foundry 1.4.4 y las dependencias fijadas, y recuperó ambos recursos de Pinata con HTTP 200. `ipfs.io` devolvió 429. La ejecución posterior del usuario con Filebase completó las cuatro descargas y la prueba real de Anvil, con estado `verified`. Luego el agente repitió formato, 48 pruebas Solidity, cobertura, reporte agregado de gas y 20 pruebas del verificador con éxito. La nueva medición por escenarios quedó bloqueada por permisos de sockets de esta sesión y el usuario confirmó después ambos workflows remotos en verde, con sus enlaces registrados y sin inspección directa de logs por el agente. Ver [resultado final y límites](docs/ipfs-verification-2026-11-15.md). Ver [evidencia de fase 4](docs/metadata-validation-2026-11-15.json).
