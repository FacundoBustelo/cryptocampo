# Fundamento académico y decisiones del TP

Este documento relaciona la implementación con el material local de los cuatro módulos. La referencia de estudio es `RESUMEN_MATERIA_TP_FINAL.txt`, en la carpeta de la materia; las rutas de PDFs de la tabla se interpretan desde esa carpeta, fuera del repositorio independiente `cryptocampo/`. Se indican como referencias bibliográficas y no como enlaces relativos que requieran archivos ausentes en la entrega. La [copia fiel del README de entrega](consigna-entrega.md) queda incluida para poder revisar la matriz sin depender del entorno del autor.

## Conceptos aplicados

| Módulo y fuentes locales | Conceptos | Aplicación y evidencia del proyecto |
| --- | --- | --- |
| 1: `modulo1/Tema 1.pdf` a `Tema 3.pdf`, `Tema 6.pdf`, `Tema 9.pdf` | Blockchain, contratos, consenso y tokenización. | CCNFT registra derechos digitales, nominales y propietarios. Los [recibos públicos](entrega.md) permiten seguir cambios de estado; el contrato no verifica mercadería agrícola ni consulta precios externos. |
| 1: `modulo1/Tema 4.pdf`, `Tema 7.pdf` | Billeteras, direcciones y firmas. | Cinco cuentas con responsabilidades separadas; [importación de tokens](sepolia-results.md). Importar permite visualizar tokens ya existentes: no los emite ni compra. |
| 1: `modulo1/Tema 5.pdf`, `Tema 8.pdf` | Gas, ETH y tarifas de transacción. | ETH de Sepolia paga gas; BUSD paga principal/comisiones. El [ejecutor público](../tools/sepolia.py) estima recursos y conserva nonces/recibos. No se toman precios históricos de apuntes como cotizaciones. |
| 2: `Modulo 2/Tema 2.pdf`, `Tema 3.pdf` | Tipos, estado, funciones y visibilidad. | `address`, `bool`, `uint256`, tasas `uint16`, beneficio `uint32`; getters de consulta y operaciones que modifican estado en [CCNFT](../src/CCNFT.sol). |
| 2: `Modulo 2/Tema 4.pdf`, `Tema 6.pdf` | Structs, arrays y mappings. | `TokenSale`, `values`, `validValues`, `tokensOnSale`, `listTokensOnSale`. La lista enumera publicaciones; el mapping no enumera sus claves. [Pruebas de operaciones](../test/CCNFTOperations.t.sol). |
| 2: `Modulo 2/Tema 5 - Almacenamiento de memoria y datos de llamadas.pdf` | `storage`, `memory`, `calldata`. | Venta copiada a `memory` en `trade`; arrays auxiliares en `storage`; IDs del reclamo en `calldata`. Se distingue estado persistente de datos temporales. |
| 2: `Modulo 2/Tema 8.pdf`, `Tema 9 - Importaciones en Solidity.pdf`, `Tema 10.pdf`, `11.pdf` | Composición, imports, ABI y herencia. | `IERC20` conecta CCNFT con BUSD; herencia y overrides compatibles con OpenZeppelin 4.5.0. [Configuración de imports](../foundry.toml) y [pruebas de interfaces](../test/CCNFTAdmin.t.sol). |
| 3: `Modulo3/Tema 1.pdf` a `Tema 8.pdf`, `Tema 13.pdf` | Foundry, compilación, almacenamiento, pruebas y red local. | Separación `src/test/script/lib`, `setUp`, `vm.prank`, asserts, fuzz y cobertura. [Validación integral](../tools/validate-system.py), [gas](gas-scenarios.md) y [dos recorridos Anvil](local-demo-validation.md). |
| 3: `Modulo3/Tema 9 - Interactuar con un contrato inteligente utilizando la CLI.pdf`, `Tema 10.pdf`, `Tema 14.pdf`, `Tema 15.pdf`, `Tema 21.pdf` | Cast, scripts, Sepolia, variables y Makefile. | Scripts `run`, `startBroadcast`/`stopBroadcast`; etapas repetibles, consultas sin transacción y despliegue/verificación. [Makefile](../Makefile), [guía local](local-demo.md) y [guía pública](sepolia.md). |
| 3: `Modulo3/Tema 11.pdf`, `Tema 16.pdf` a `Tema 21.pdf`, `Documento.pdf` | Metadatos, IPFS/Pinata y alternativa SVG/Base64 en cadena. | Se eligió SVG y JSON compartidos en IPFS: [recursos](../assets/), [CIDs y comprobaciones](ipfs-verification-2026-11-15.md). El nominal y propietario están en cadena; la imagen está fuera. Base64 es codificación, no cifrado. |
| 4: `Modulo 4/Tema 3.pdf` a `Tema 9.pdf` | ERC20, ERC721 y OpenZeppelin. | [BUSD](../src/BUSD.sol) conserva suministro y 18 decimales; CCNFT emite, enumera y quema IDs únicos. `approve`/`allowance` son distintos de las aprobaciones ERC721. [Pruebas BUSD](../test/BUSD.t.sol) y [operaciones](../test/CCNFTOperations.t.sol). |
| 4: `Modulo 4/Tema 1.pdf`, `Tema 6.pdf` a `Tema 10.pdf` | Pruebas de NFT y presentación mediante metadatos. | [Pruebas de URI](../test/CCNFTMetadata.t.sol), lectura por gateways y capturas reales de MetaMask; se declara el marcador genérico. `Ownable`, `ReentrancyGuard`, `Counters` y los eventos también están presentes en la plantilla original; no se atribuye igual profundidad de tratamiento a todos los PDFs. |

## Qué exige la cátedra y qué se decidió en el proyecto

El PDF `PROYECTO FINAL.pdf` define el objetivo conceptual y las operaciones. `Consignas-ProyectoFinal/src/CCNFT.sol` contiene la plantilla con compra, publicación, reventa, reclamo, setters, `Ownable`, protección de reentrada, contador y transferencias públicas bloqueadas. Los tests originales tienen cuerpos vacíos. El [README original](consigna-entrega.md) pide Foundry, configuración, OpenZeppelin 4.5.0, pruebas, scripts, compilación, Makefile, despliegue/verificación, interacción `buy`, aprobación, importaciones en MetaMask, enlaces de Sepolia y repositorio GitHub. La [matriz](matriz-entrega.md) revisa cada punto.

| Decisión propia o interpretativa | Motivo y consecuencia |
| --- | --- |
| Comisión de `trade` sobre el precio publicado. | La plantilla menciona «valor del NFT» sin terminar la fórmula. Se distingue precio de reventa de nominal: el segundo se conserva para `claim`. |
| `totalValue` como nominal en circulación. | Comprar aumenta, revender conserva y reclamar reduce. El límite permite nueva emisión después de una quema. No es recaudación histórica ni saldo del colector. |
| Nominales 100/500, tasas 2 %/1 %/5 %, lote 10, límite 10.000. | Parámetros configurables de demostración, no cifras obligatorias de cátedra. |
| Cinco cuentas, aprobaciones exactas y reserva inicial de 10 BUSD. | Hacen visibles permisos y pagos; la reserva deja 105 después del primer reclamo. La recomendación de aprobar una cantidad amplia en la consigna es una opción, no una obligación. |
| Validaciones y atomicidad. | Precio/nominal positivos, comisiones hasta 100 %, direcciones no nulas, token con código, no repetir IDs ni duplicar publicaciones. Se conservan tipos e interfaces acordadas; beneficio `uint32` sin tope adicional del 100 %. |
| Ficha SVG/JSON común en IPFS y setter de URI. | Técnica enseñada elegida para identificar certificados. IPFS y NFT dinámico no se exigen expresamente. La URI es administrable; CIDs identifican contenido y el pinning sostiene disponibilidad. |
| Fuzz, adversarios, cobertura base, CI, matriz de gas y recuperación pública. | Controles adicionales derivados del comportamiento del TP; no se presentan como tests entregados por la cátedra. |
| Liquidez conceptual, sin pool ni exchange. | El PDF, sección 8, presenta como opciones una pool DEX (Uniswap/PancakeSwap) o un listado centralizado. El README de entrega no exige uno de esos despliegues. Conforme al alcance aprobado, se explica el concepto y se distribuye suministro BUSD ya emitido; no se acredita acceso a un mercado externo. |

## Unidades, autorización y solvencia

1 BUSD corresponde a `10^18` unidades. Para comprar dos certificados de 100 con comisión del 2 %, A autoriza `204 * 10^18`. Para revender a 120 con 1 %, B autoriza `121200000000000000000`. Para reclamar nominal 100 con beneficio 5 %, el colector autoriza `105 * 10^18`. El spender es siempre CCNFT, que llama a `BUSD.transferFrom`; las aprobaciones no transfieren fondos.

El principal va directamente al colector. Configurar un beneficio no crea rendimiento, reservas ni BUSD: el pago exige saldo y autorización. Las cuentas y el administrador siguen siendo una dependencia de confianza; una red descentralizada no elimina la administración centralizada de `Ownable`. La [contabilidad del recorrido](../README.md#recorrido-y-financiación) distingue nominal, precio, comisiones y reserva.

Las búsquedas son lineales y el costo crece con publicaciones y lote. El límite de lote no limita la lista global. La cobertura mide ejecución de pruebas, la verificación Etherscan relaciona fuentes y bytecode, y la revisión de hashes detecta cambios de archivos; ninguna de ellas acredita respaldo físico, rentabilidad ni disponibilidad futura de gateways.
