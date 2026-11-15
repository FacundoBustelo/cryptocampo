# Validación local — 14/11/2026

**Actualización del 15/11/2026: fases 2 y 3 validadas en CI.** El usuario aportó [resultados](ci-validation-2026-11-15.md) con compilación y formato satisfactorios, 48 pruebas aprobadas y 97,53 % de ramas de CCNFT cubiertas, además del reporte agregado de gas y [35 transacciones de medición exitosas](gas-scenarios.md), con commit, versiones y revisiones identificados. La nueva prueba cubrió las dos guardas de `claim`; las dos ramas restantes de `trade` están justificadas como inalcanzables mediante la interfaz pública actual. El cierre abarca el rango medido y conserva los límites documentados. Las limitaciones de ejecución y controles pendientes descritos abajo corresponden a la revisión histórica local del 14/11/2026; fueron resueltos en CI dentro del alcance registrado.

Al 14/11/2026, la fase 3 seguía pendiente de validación local; los resultados de CI del 15/11/2026 permiten su cierre, según la actualización anterior. La fase 4 está iniciada: URI compartida, ocho pruebas de metadatos aprobadas, imagen y JSON preparados. No se publicaron recursos en IPFS ni se desplegó en Sepolia.

## Entorno y ejecución

El [registro de comandos](verification-2026-11-14.txt) corresponde al estado posterior a la incorporación de los metadatos. El instalador falló por DNS de GitHub (código 6); compilación, formato, suite, cobertura y gas fallaron por ausencia de Forge (código 127). No hay pruebas aprobadas, porcentajes de cobertura ni cifras de gas que informar. No se pudieron verificar las revisiones contra bibliotecas descargadas ni la versión de un compilador instalado.

La configuración conserva Solidity 0.8.19, OpenZeppelin 4.5.0, Foundry 1.4.4 y forge-std 1.9.7 con las revisiones del README. El TOML y la sintaxis Bash del instalador se verificaron localmente. Hay 47 funciones de prueba, incluidas las 39 previas y las cuatro fuzz configuradas con 256 casos cada una. Las ocho nuevas cubren metadatos; también se amplió la prueba de todos los setters y de interfaces.

## Revisión estática de fase 3

Se contrastaron el PDF conceptual, las indicaciones de entrega, las plantillas y las reglas acordadas. Se mantuvieron las referencias académicas sin editar. BUSD conserva la emisión inicial de 10 millones de tokens. No se modificaron las reglas económicas ni las cuatro operaciones durante este avance.

| Aspecto revisado | Comprobación en fuentes y pruebas escritas |
| --- | --- |
| Permisos y transferencias | Setters con `onlyOwner`; publicación y reclamo comprueban propietario; las tres transferencias públicas siguen bloqueadas, incluso con aprobación. |
| Reentrada e IDs | Las cuatro operaciones usan `nonReentrant`; el ID y nominal se reservan antes del callback de mint; el contador no se reduce al quemar. Hay receptores y ERC20 adversarios en la suite. |
| Atomicidad | Los cobros comprueban el booleano del ERC20; un fallo revierte la transacción. La suite contempla principal y segundo cobro fallidos, receptores que rechazan, y quema previa a un ID inválido, repetido o ajeno. |
| Límites y redondeo | Cantidades positivas hasta `maxBatchCount`, nominal habilitado y límite de nominal vigente; comisiones hasta 10.000. Fórmulas sobre totales con división entera; `profitToPay` mantiene `uint32` completo. |
| Publicaciones y quema | Repetir publicación actualiza sin duplicar; eliminación con búsqueda y swap/pop; reventa y reclamo limpian precio, indicador y lista. La quema elimina el nominal. |
| Conservación del nominal | Compra aumenta `totalValue`, reventa lo conserva y reclamo resta únicamente el nominal; las pruebas escritas contrastan la suma de valores y la enumeración. |

La revisión estática inicial no probaba comportamiento ejecutado ni compatibilidad de compilación. El registro posterior de CI permite identificar cuatro ramas sin cubrir. Las dos guardas de configuración de `trade` son inalcanzables por la interfaz pública actual porque se comprueba primero la existencia del NFT. En `claim`, en cambio, la configuración se comprueba antes de la existencia de IDs: sus dos rechazos sí son alcanzables sin emitir NFTs, y se añadió una prueba para ellos. Ver el [análisis detallado](ci-validation-2026-11-15.md).

## Gas y límites de uso

La búsqueda es O(publicaciones). Insertar, actualizar y eliminar recorren la lista; la eliminación cambia su orden. Reclamar un lote cuesta hasta O(lote × publicaciones), además de la quema y enumeración. Comprar es O(lote). El límite de lote configurado para la demostración es 10; el tipo admite hasta 65.535 y no establece una cantidad segura para una red. La lista global no tiene límite y puede crecer entre varias compras, aunque cada compra respete el lote máximo.

Las mediciones pendientes en la revisión inicial se completaron en CI: reporte agregado y 35 recibos de transacciones con listas de 1, 10 y 100 y lotes de 1 y 10, incluidas actualizaciones al final, eliminaciones en distintas posiciones y reclamos publicados y no publicados. La preparación del estado se separó de cada transacción medida y se documentaron configuración, calentamiento y límite de bloque. Ver [resultados y límites](gas-scenarios.md). No se extrapola un máximo global ni un límite seguro para redes públicas.

## Recursos de fase 4

Se validó `assets/metadata.json` con el parser JSON de Python y `assets/certificate.svg` con ElementTree. Se comprobó que la ficha tiene solo los tres campos acordados y que su imagen local corresponde al SVG existente. El SVG se renderizó mediante librsvg/Cairo a 1200 × 800 y se inspeccionó visualmente: texto «Certificado de demostración» legible, sin recortes, con espiga y campos verdes. No tiene scripts, imágenes externas ni fuentes descargables.

La URI de imagen en localhost y las cadenas de la suite son referencias de prueba. Se preparó la resolución local, pero los contratos no descargan el JSON ni la imagen. Accesibilidad IPFS, pinning y presentación en una billetera quedan pendientes. El README indica el orden imagen → JSON final → configuración de URI.

## Reproducción de la validación

Con conectividad, ejecutar desde `cryptocampo/`:

```bash
bash tools/setup.sh
export PATH="$PWD/.tools/bin:$PATH"
forge --version
git -C lib/openzeppelin-contracts rev-parse HEAD
git -C lib/forge-std rev-parse HEAD
git -C lib/openzeppelin-contracts status --porcelain
git -C lib/forge-std status --porcelain
forge build
forge fmt --check
forge test -vv
forge coverage
forge test --gas-report
```

Comparar revisiones con la tabla del README y comprobar que las dependencias están limpias. Si falla el formato en cambios futuros, ejecutar `forge fmt` y repetir el control. La matriz de recibos se reproduce con `forge build --force` y `python3 tools/measure-gas.py`. Las fases 2 y 3 están cerradas con la evidencia de CI registrada, conservando las limitaciones del rango medido. La fase 4 solo se cerrará con publicación, pinning y accesibilidad real comprobados.
