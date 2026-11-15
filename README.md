# CryptoCampo NFT

Contratos para certificados agrícolas de demostración y pagos con un token ERC20 BUSD. Los certificados no acreditan existencias físicas verificadas y el token no tiene respaldo en dólares.

Se incluyen BUSD, que emite 10 millones de tokens con 18 decimales al desplegador, y CCNFT, con compra, publicación, reventa, reclamo y metadatos compartidos. **El 15/11/2026 se registraron compilación con Solidity 0.8.19 y 47 pruebas aprobadas en GitHub Actions**, incluidas cuatro fuzz con 256 casos cada una, y se recibió el reporte agregado de gas. El usuario informó que el workflow completo terminó satisfactoriamente. Se revisaron las cuatro ramas sin cobertura: dos de `trade` son inalcanzables por el invariante de configuración y dos de `claim` motivaron una prueba nueva, todavía pendiente de ejecución. La suite actual tiene 48 pruebas; faltan ejecutar esa actualización y medir listas y lotes por escenario antes de cerrar la fase 3. La fase 4 está iniciada con un certificado SVG y un JSON local; la publicación real en IPFS sigue pendiente. Ver [evidencia y revisión de ramas](docs/ci-validation-2026-11-15.md).

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

Se conservan las auxiliares `find`, `addToArray` y `removeFromArray`: búsqueda lineal, reemplazo por el último elemento y `pop`. La lista no conserva el orden. Publicar, actualizar o eliminar cuesta O(n) en la cantidad de publicaciones; reclamar un lote puede costar O(lote × publicaciones). `maxBatchCount` no limita la longitud global de la lista. El reporte de CI recibido midió máximos agregados de 1.498.834 gas para `buy`, 119.741 para `putOnSale`, 160.027 para `trade` y 529.664 para `claim`; son valores observados en la suite, no cotas garantizadas. Falta medir por separado tamaños de lista y lote. Ver [tabla y límites de interpretación](docs/ci-validation-2026-11-15.md).

Los eventos `Buy`, `PutOnSale`, `Trade` y `Claim` identifican participantes, IDs y nominal o precio. `Trade` incluye la comisión. `BuyPayment` y `ClaimPayment` registran principal y comisión o beneficio de todo el lote, para reflejar correctamente el redondeo agregado.

El recorrido de aceptación compra dos NFTs de 100 BUSD con 2 % de comisión, revende uno a 120 con 1 % y lo reclama con 5 % de beneficio (105 BUSD). La prueba comprueba eventos, autorizaciones exactas, variaciones de saldo A: −84; B: −16,2; fondos: +95; comisiones: +5,2 BUSD, y nominal final de 100 BUSD. **La prueba pasó en el registro de CI recibido el 15/11/2026.**

## Metadatos compartidos — inicio de fase 4

[`assets/certificate.svg`](assets/certificate.svg) es un certificado agrícola sencillo con el texto visible «Certificado de demostración». Se usan formas y texto SVG, siguiendo la separación entre imagen y metadatos tratada en la cursada. [`assets/metadata.json`](assets/metadata.json) contiene solo `name`, `description` e `image`, sin IDs ni nominales individuales. Todos los NFTs usan la misma ficha; la propiedad y el nominal se consultan en el contrato.

`setMetadataURI(string)` requiere `onlyOwner`, rechaza cadenas vacías con `Empty metadata URI` y emite `MetadataURIUpdated(string metadataURI)` en cada configuración o actualización. El administrador puede cambiar la ficha de todos los NFTs vigentes y futuros. El constructor sigue sin argumentos.

`tokenURI(uint256)` comprueba primero la existencia del NFT y revierte con `Token does not exist` para IDs inexistentes o quemados. Para un NFT vigente devuelve la cadena compartida, inicialmente vacía. Una reventa conserva esa URI. La configuración de metadatos no habilita operaciones ni modifica saldos, publicaciones o nominales; comprar, revender y reclamar funcionan sin configurar la URI.

La referencia de imagen del JSON es **solo para pruebas locales**: `http://127.0.0.1:8000/certificate.svg`. Para revisar ambos archivos desde el directorio del proyecto:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 --directory assets
```

Abrir `http://127.0.0.1:8000/certificate.svg` y `http://127.0.0.1:8000/metadata.json`. En una futura demostración local, el propietario podrá llamar a `setMetadataURI("http://127.0.0.1:8000/metadata.json")`. Las pruebas Solidity comparan cadenas; no descargan recursos ni prueban accesibilidad HTTP. `https://metadata.example.invalid/updated.json`, usado al probar actualizaciones, es otro marcador de prueba sin publicación. Estas referencias locales no sirven para billeteras de terceros.

Para completar la publicación, en este orden:

1. Publicar y fijar mediante pinning `certificate.svg` en IPFS; registrar su CID real y comprobar el contenido recuperado.
2. Sustituir `image` en `metadata.json` por `ipfs://<CID_REAL_DE_IMAGEN>` (añadir `/certificate.svg` únicamente si el CID corresponde a un directorio). Ajustar la descripción para retirar la referencia a una prueba local.
3. Validar de nuevo el JSON, publicarlo y fijarlo en IPFS. Registrar el CID del JSON final: editarlo después cambia su CID.
4. Como propietario, ejecutar `setMetadataURI("ipfs://<CID_REAL_DE_JSON>")`, añadiendo `/metadata.json` si corresponde a un directorio. Los textos entre `<...>` son marcadores explicativos, no URIs utilizables.
5. Recuperar ambos recursos por sus CIDs y un gateway, comprobar la imagen en una billetera compatible y conservar evidencia de pinning y accesibilidad. El contrato guarda la cadena y no comprueba la disponibilidad del contenido.

Los archivos **no están publicados ni fijados en IPFS**. Se comprobó su sintaxis y se revisó visualmente el SVG renderizado a 1200 × 800; las ocho pruebas de metadatos pasaron en CI según el registro recibido el 15/11/2026. Scripts de demostración y despliegue en Sepolia corresponden a fases posteriores.

## Organización y comprobación

- `src/`: contratos activos.
- `test/BUSD.t.sol`: metadatos, suministro y asignación inicial de BUSD.
- `test/CCNFTAdmin.t.sol`: configuración, permisos y habilitaciones.
- `test/CCNFTOperations.t.sol`: recorrido de aceptación, eventos, límites, publicaciones, enumeración, reclamos y redondeo.
- `test/CCNFTSecurity.t.sol` y `test/mocks/`: atomicidad ante fallos de saldo, autorización, segundo cobro, ERC20 falso y callbacks ERC721/ERC20.
- `test/CCNFTFuzz.t.sol`: cuatro pruebas parametrizadas de fórmulas y conservación del nominal, con 256 casos por prueba.
- `test/CCNFTMetadata.t.sol`: URI inicial, permisos, cadena vacía, eventos, actualización común, reventa, existencia y separación de la lógica económica.
- `script/`: reservado para scripts de despliegue e interacción.
- `assets/`: certificado SVG y JSON compartido con referencia de imagen local.
- `docs/`: evidencia del intento de verificación y revisión estática.
- `tools/`: instalación reproducible del entorno.

La configuración fija Solidity 0.8.19, EVM Paris y optimización con 200 ejecuciones. Las pruebas se ejecutan localmente, sin RPC ni cuentas externas.

Hay 48 funciones de prueba: 2 de BUSD y 46 de CCNFT, incluidas las 4 pruebas fuzz. Se conservaron las 39 originales y se añadieron 8 de metadatos y una de configuración incompleta de `claim`; la prueba de permisos administrativos incluye el nuevo setter y la de interfaces comprueba ERC721Metadata. Las 47 anteriores pasaron en el registro de CI recibido el 15/11/2026, sin fallos ni omisiones. En esa ejecución CCNFT alcanzó 100 % de líneas, sentencias y funciones y 95,06 % de ramas (77/81). La prueba nueva aún requiere ejecución en CI. La justificación de las dos guardas de `trade` inalcanzables por la interfaz pública está en la [revisión de cobertura](docs/ci-validation-2026-11-15.md).

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

En esa comprobación local del 14/11/2026 no se obtuvieron resultados de pruebas, cobertura ni gas. El [registro posterior de CI del 15/11/2026](docs/ci-validation-2026-11-15.md) aporta compilación y 47 pruebas aprobadas, con cobertura y reporte agregado de gas. La ejecución local sigue sin entorno instalado; no se reintentaron las descargas. El cierre de fase 3 requiere ejecutar la nueva prueba de configuración de `claim` y completar las mediciones de listas y lotes. El detalle del entorno del runner aún debe incorporarse a la evidencia.
