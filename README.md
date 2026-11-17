# CryptoCampo NFT

Trabajo final de Desarrollo de Blockchain: certificados agrícolas de demostración mediante NFTs ERC721 y pagos con un ERC20 llamado BUSD. Permite comprar, publicar, revender y reclamar certificados. **Los NFTs no acreditan existencias físicas verificadas y BUSD no tiene respaldo en dólares ni vínculo con un token externo.**

Las fases 1–7 están completadas dentro del alcance académico. Sepolia conserva dos contratos verificados, 26 transacciones exitosas, 55 controles finales y capturas originales de los tokens importados en MetaMask. La billetera muestra el NFT con un marcador genérico: el render de su imagen sigue siendo una limitación documentada. Esta descripción se basa en evidencia del 15/11/2026 revisada localmente, sin una nueva consulta a la red.

La fase 8 tiene documentación y contenido de entrega preparados localmente. Su aceptación de reproducción sigue pendiente por los bloqueos de DNS y sockets registrados el 16/11/2026. La publicación de estos cambios en GitHub y la comprobación del repositorio publicado siguen pendientes.

| Lectura | Contenido |
| --- | --- |
| [Guía de entrega](docs/entrega.md) | Contratos, las 26 transacciones —incluida `buy`—, capturas y resultados. |
| [Matriz de la consigna](docs/matriz-entrega.md) | Cada indicación vinculada con implementación y evidencia. |
| [Conceptos de los cuatro módulos](docs/fundamento-academico.md) | Material local, aplicación y decisiones propias. |
| [Revisión y reproducción del 16/11](docs/entrega-validacion-2026-11-16.md) | Comandos, versiones, hashes, resultados y bloqueos actuales. |
| [Demostración Anvil](docs/local-demo.md) / [Sepolia y MetaMask](docs/sepolia.md) | Ejecución por etapas, consultas y recuperación. |

## Arquitectura

[BUSD](src/BUSD.sol) hereda de ERC20 de OpenZeppelin y emite 10.000.000 BUSD con 18 decimales al desplegador. [CCNFT](src/CCNFT.sol) hereda de `ERC721Enumerable`, `Ownable` y `ReentrancyGuard`. Mantiene propietarios, nominales, publicaciones y límites; utiliza `IERC20.transferFrom` para pagar directamente entre las cuentas. CCNFT no custodia BUSD.

Hay cinco actores: administrador, comprador A, comprador B, colector de fondos y colector de comisiones. El administrador configura y habilita las operaciones mediante setters `onlyOwner`. El colector recibe el principal de las compras y financia los reclamos; el vendedor recibe el precio de reventa y el colector de comisiones recibe los cargos adicionales.

| Directorio o archivo | Responsabilidad |
| --- | --- |
| [src/](src/) | BUSD y CCNFT. |
| [test/](test/) | Operaciones, administración, atomicidad, reentrada, metadatos y fuzz. |
| [script/](script/) | Identidad, despliegue, configuración, financiación y operaciones. |
| [tools/](tools/) | Instalación, validación integral, gas y ejecutores Anvil/Sepolia. |
| [assets/](assets/) | Certificado SVG y JSON compartido. |
| [docs/](docs/) | Guías e informes; `evidence/` conserva registros originales y hashes. |
| [foundry.toml](foundry.toml), [Makefile](Makefile), [.env.example](.env.example) | Compilación, comandos y nombres de variables. |
| [.github/workflows/](.github/workflows/) | Validación automatizada y comprobación manual de metadatos. |

## Instalación

Ejecutar desde la raíz de este repositorio (`cryptocampo/` en la carpeta de la materia). Se requieren Linux x86_64, Bash, Git, curl, tar, gzip, `install` y utilidades GNU básicas (`uname`, `mktemp`, `mkdir`, `rm`, `mv`, `head`, `grep`). Para los controles se necesitan **Python 3.11 o posterior** y GNU Make. Las herramientas Python usan la biblioteca estándar, sin paquetes de pip. La instalación necesita DNS/HTTPS hacia GitHub y la primera compilación necesita acceso al servidor de compiladores de Solidity. Anvil requiere permiso para abrir sockets locales.

| Componente | Versión / revisión fijada |
| --- | --- |
| Foundry | v1.4.4 / `05794498bf47257b144e2e2789a1d5bf8566be0e` |
| Solidity | 0.8.19, optimizador 200 runs, EVM Paris |
| OpenZeppelin Contracts | v4.5.0 / `a5445b0afb8b350417b6e6ab3160554967bc151f` |
| forge-std | v1.9.7 / `77041d2ce690e692d6e03cc812b57d1ddaa4d505` |

```bash
bash tools/setup.sh
export PATH="$PWD/.tools/bin:$PATH"
make build
make test
make test-python
make fmt-check
# Compilación, pruebas/fuzz, cobertura base, gas y dos recorridos Anvil:
make validate
# Enlaces relativos, imágenes, integridad Sepolia y revisión de secretos:
python3 tools/check-delivery.py
```

El instalador descarga los binarios en `.tools/bin/` y las bibliotecas en `lib/`, por revisión fija. Comprueba revisión y ausencia de cambios locales en dependencias ya instaladas. No modifica la configuración del usuario ni crea commits. Forge descarga Solidity 0.8.19 al compilar por primera vez. `.tools/`, `lib/`, `out/`, `cache/` y `broadcast/` se regeneran y están excluidos de Git.

**No hace falta `.env` para compilar, probar o usar Anvil.** Para Sepolia, copiar `.env.example` a `.env`, aplicar `chmod 600 .env` y completar RPC, API de Etherscan y las cinco cuentas de prueba. Las claves se usan por entorno y no deben incorporarse a la entrega. Cada firmante necesita ETH de prueba para gas, además de BUSD para los pagos correspondientes. Ver [preparación pública](docs/sepolia.md).

## Comandos y demostración

| Comando | Efecto |
| --- | --- |
| `make install`, `build`, `fmt-check`, `test`, `test-python` | Instalar, compilar, revisar formato y probar. |
| `make coverage` | Cobertura; `validate` exige además la base documentada. |
| `make gas`, `make gas-matrix` | Reporte de pruebas y 35 mediciones por escenario en Anvil. |
| `make demo` | Dos redes Anvil nuevas; dos recorridos completos con recibos y verificaciones Cast. |
| `make validate` | 21 controles con logs, códigos y hashes en un directorio nuevo de `.tools/validation/`. |
| `make anvil` | Nodo local persistente; las etapas siguientes se ejecutan en otra terminal. |
| `make deploy configure fund approvals enable buy list trade claim` | Recorrido local por etapas sobre `RPC_URL` y `STATE`. |
| `make sepolia-doctor` | Diagnóstico de red, cuentas y financiación pública. |
| `make sepolia-deploy`, `make sepolia-verify` | Publicación y verificación públicas. |
| `make sepolia-check`, `make sepolia-reconcile` | Comprobación del estado y reconciliación de recibos/nonces. |

Las etapas locales usan `RPC_URL=http://127.0.0.1:8545` y `STATE=.tools/demo-state.json` por defecto. Los comandos `sepolia-` publican transacciones cuando la etapa lo requiere y conservan estado separado en `.tools/sepolia/`. Consultar la [secuencia completa y recuperación](docs/sepolia.md) antes de ejecutarlos. Los comandos de validación integral solo utilizan Anvil.

## Operaciones y reglas económicas

Todas las cantidades monetarias son enteros en unidades mínimas: **1 BUSD = `10^18` unidades**. `100 ether` en Solidity representa aquí 100 BUSD, sin transferir ETH. Las tasas se expresan en puntos básicos: `10_000 = 100 %`. Cada división entera trunca sobre el importe total de la operación.

| Función | Efecto y pagos |
| --- | --- |
| `buy(uint256 value, uint256 amount)` | Emite un lote de nominal permitido. Principal = `value * amount`; comprador → fondos: principal; comprador → comisiones: `principal * buyFee / 10_000`. Aumenta `totalValue` por el principal. |
| `putOnSale(uint256 tokenId, uint256 price)` | Solo el propietario publica, con precio positivo. Una nueva publicación actualiza el precio sin duplicar el ID. No mueve BUSD. |
| `trade(uint256 tokenId)` | Comprador → vendedor: precio publicado; comprador → comisiones: `price * tradeFee / 10_000`. Transfiere el NFT, limpia la publicación y conserva su nominal. Rechaza comprar al propio vendedor. |
| `claim(uint256[] calldata tokenIds)` | Quema los NFTs del llamador y limpia valores y publicaciones. Fondos → llamador: suma nominal + `nominal * profitToPay / 10_000`. Reduce `totalValue` solo por el nominal. IDs repetidos revierten toda la operación. |

`totalValue` es la suma de nominales de NFTs en circulación. Las reventas no lo alteran; los reclamos liberan capacidad de emisión. Los IDs comienzan en cero y no se reutilizan tras una quema.

Compradores iniciales y secundarios necesitan saldo y `BUSD.approve(CCNFT, importe)` por **principal o precio más comisión**. Para `claim`, el colector de fondos aprueba el pago completo a CCNFT. Una aprobación autoriza gasto y no mueve tokens. Configurar `profitToPay` no crea BUSD ni genera rendimientos: el colector necesita saldo y autorización suficientes.

| Parámetro de demostración | Valor |
| --- | --- |
| Nominales permitidos | 100 y 500 BUSD |
| `buyFee`, `tradeFee`, `profitToPay` | 200 (2 %), 100 (1 %), 500 (5 %) |
| `maxBatchCount` | 10 |
| `maxValueToRaise` | 10.000 BUSD de nominal vigente |

Estos valores son decisiones del TP y se configuran por setters. La base de `tradeFee` sobre el precio publicado también es una interpretación adoptada, identificada en el [fundamento académico](docs/fundamento-academico.md). Las comisiones admiten 0–10.000 puntos básicos; `profitToPay` conserva el rango `uint32` de la plantilla. Se rechazan direcciones cero, token sin código, nominal/precio cero y lote configurado en cero. Reducir el límite nominal no altera NFTs existentes ni impide reclamar.

Las operaciones comienzan deshabilitadas. Los setters son exclusivos del administrador; las cuatro operaciones tienen `nonReentrant`. Cada pago comprueba el retorno de `transferFrom` y un fallo revierte cobros, emisión, quema y publicaciones. Las tres transferencias públicas del ERC721 revierten con `Not Allowed`, incluso con aprobación del NFT; la reventa se realiza mediante `trade` y `_safeTransfer` interno.

La lista de ventas usa búsqueda lineal y eliminación por reemplazo con el último elemento: no conserva orden. El costo de reclamar puede crecer como lote × publicaciones. Las [35 mediciones históricas de gas](docs/gas-scenarios.md) abarcan listas de 1, 10 y 100 y lotes de 1 y 10; no establecen una cota global.

## Recorrido y financiación

A y B reciben 1.000 BUSD cada uno; fondos recibe 10 BUSD adicionales del suministro inicial. A autoriza 204 BUSD y compra dos NFTs de 100. Publica el NFT 0 a 120 BUSD; B autoriza 121,2 y lo compra. Fondos autoriza 105 y B reclama el NFT 0. A conserva el NFT 1, de nominal 100 BUSD.

| Cuenta | Saldo inicial BUSD | Saldo final BUSD | Variación |
| --- | ---: | ---: | ---: |
| A | 1.000 | 916 | −84 |
| B | 1.000 | 983,8 | −16,2 |
| Fondos | 10 | 105 | +95 |
| Comisiones | 0 | 5,2 | +5,2 |

Las variaciones suman cero, queda nominal total de 100 BUSD y las autorizaciones exactas se consumen. La reserva final de 105 puede cubrir el NFT restante, pero requeriría una nueva aprobación del colector. Sin los 10 iniciales quedarían 95 y faltarían 10 para ese segundo reclamo.

La liquidez se explica conceptualmente: disponer de BUSD distribuido y reservas para reclamos no implica una pool, un precio de mercado ni convertibilidad a dólares. No se implementaron exchanges, oráculos, respaldo agrícola externo ni una interfaz web; la consigna disponible no define una pool como entregable.

## Metadatos y evidencia pública

[certificate.svg](assets/certificate.svg) y [metadata.json](assets/metadata.json) contienen una ficha común de demostración, sin IDs ni nominales individuales. La URI definitiva es `ipfs://bafkreihjmwkav7thv25yhsosaemqlvn5necgydfkofak7dl5zel3zuw5t4`. `tokenURI` comprueba existencia y conserva la ficha en reventa. `setMetadataURI` permite al administrador actualizarla para todos los NFTs; los metadatos no son inmutables. Ambos recursos requieren pinning para su disponibilidad. Ver [publicación y resolución verificadas](docs/ipfs-verification-2026-11-15.md).

| Contrato en Sepolia (11155111) | Código verificado |
| --- | --- |
| BUSD | [0x2a37e9ac75569eea1537bdb7ba6beb5b6cd8f710](https://sepolia.etherscan.io/address/0x2a37e9ac75569eea1537bdb7ba6beb5b6cd8f710#code) |
| CCNFT | [0xbd6c1c5f5690d92021bff186597c2b71daf97a34](https://sepolia.etherscan.io/address/0xbd6c1c5f5690d92021bff186597c2b71daf97a34#code) |

La [guía de entrega](docs/entrega.md) reúne las 26 transacciones y las capturas originales. [Resultado de fase 7](docs/sepolia-results.md) conserva la limitación visual de MetaMask y el intento CREATE fallido, separado de los recibos exitosos.

## Estado y validación

| Fase | Estado y evidencia |
| --- | --- |
| 1. Alcance | Reglas definidas; [fundamento y decisiones](docs/fundamento-academico.md). |
| 2–3. Entorno y contratos | Completadas; [CI, cobertura y ramas inalcanzables](docs/ci-validation-2026-11-15.md). |
| 4. Metadatos | Publicación/resolución verificadas; [IPFS y Anvil](docs/ipfs-verification-2026-11-15.md). |
| 5. Sistema | Completada en el rango medido; [matriz de validación](docs/system-validation.md). |
| 6. Anvil | Dos redes, 52 recibos y 838 comprobaciones históricos; [cierre local](docs/local-demo-validation.md). |
| 7. Sepolia y MetaMask | Completada académicamente con limitación visual; [resultado](docs/sepolia-results.md). |
| 8. Entrega | Documentación local preparada; reproducción actual bloqueada y publicación final pendiente; [revisión actual](docs/entrega-validacion-2026-11-16.md). |

El 16/11/2026 aprobaron compilación, formato, **49 pruebas Solidity** (cuatro fuzz de 256 casos), **70 pruebas Python**, cobertura base y reporte de gas. CCNFT conserva 100 % de líneas (122/122), sentencias (116/116) y funciones (25/25), y 97,53 % de ramas (79/81). Los dos rechazos pendientes de `trade` son inalcanzables mediante la interfaz pública actual. La validación integral actual no está aprobada: la matriz de gas y ambos Anvil requieren sockets y la instalación limpia requiere DNS hacia GitHub. Se conservan logs e informes nuevos junto con los históricos, sin atribuirles una nueva ejecución pública.
