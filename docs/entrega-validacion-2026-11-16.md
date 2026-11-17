# Revisión de fase 7 y preparación local de fase 8 — 16/11/2026

**Resultado: documentación local preparada; aceptación de reproducción pendiente por bloqueos del entorno.** La fase 7 conserva su cierre académico y la limitación visual de MetaMask. No se publicaron cambios en GitHub ni se enviaron nuevas transacciones públicas. Los controles nuevos revisan archivos locales; no son una nueva consulta a Sepolia, Etherscan o IPFS.

## Entorno y comandos

Linux x86_64, Python 3.12.3, Foundry 1.4.4 (`05794498bf47257b144e2e2789a1d5bf8566be0e`), Solidity 0.8.19, optimizador 200 runs y EVM Paris. OpenZeppelin 4.5.0 en `a5445b0afb8b350417b6e6ab3160554967bc151f` y forge-std 1.9.7 en `77041d2ce690e692d6e03cc812b57d1ddaa4d505`, ambos sin cambios locales. El [resultado final](evidence/delivery-2026-11-16/final-validation/result.json) registra plataforma, Python completo, comandos, tiempos, códigos y hashes de fuentes; sus logs conservan las versiones exactas.

Desde `cryptocampo/` se ejecutó:

```bash
python3 tools/validate-system.py
```

La primera ejecución `20261116T132422039533Z` revisó el estado inicial de esta tarea sobre `61293b9`; su manifiesto identifica el README anterior a esta edición. Tras detectar y corregir la dependencia de una prueba Python de un artefacto ignorado, se repitió la validación integral en `delivery-after-fixture-fix`. Se conserva la [ejecución inicial](evidence/delivery-2026-11-16/validation/result.json) y la [ejecución posterior a la corrección](evidence/delivery-2026-11-16/final-validation/result.json), sin modificar resultados históricos. Los contratos, las pruebas Solidity y los ejecutores se conservan; solo cambia el aislamiento de una prueba Python, además de documentación y la nueva herramienta de entrega.

| Control | Resultado actual | Evidencia |
| --- | --- | --- |
| Metadatos locales | Aprobado | [Log](evidence/delivery-2026-11-16/final-validation/metadata-local.txt). |
| Pruebas Python | 70 aprobadas | [Log](evidence/delivery-2026-11-16/final-validation/python-tests.txt). |
| Formato / compilación forzada | Aprobados | [Formato](evidence/delivery-2026-11-16/final-validation/format.txt), [compilación](evidence/delivery-2026-11-16/final-validation/build.txt). |
| Solidity y fuzz | 49 pruebas, sin fallos/omisiones; cuatro fuzz de 256 casos | [Log](evidence/delivery-2026-11-16/final-validation/solidity-tests.txt). |
| Cobertura y base exigida | Aprobadas | [Resumen y ramas](evidence/delivery-2026-11-16/final-validation/coverage-summary.txt). |
| Compilación optimizada / reporte de gas | Aprobados | [Compilación](evidence/delivery-2026-11-16/final-validation/optimized-build.txt), [gas](evidence/delivery-2026-11-16/final-validation/gas-report.txt). |
| Matriz de gas Anvil | **Bloqueada**, código 1: `PermissionError: [Errno 1] Operation not permitted` al crear un socket | [Log](evidence/delivery-2026-11-16/final-validation/gas-matrix.txt). No hay nuevas 35 mediciones. |
| Dos recorridos Anvil | **Ambos bloqueados**, código 1 por sockets | [Log](evidence/delivery-2026-11-16/final-validation/local-demo.txt), [informe de ambos intentos](evidence/delivery-2026-11-16/final-validation/demo/result.json). No se desplegaron contratos en esta repetición. |

El validador conserva **19/21 comandos con código cero**, y estado global `failed` por los dos bloqueos. Los comandos de Git y versión dentro de ese total solo registran contexto: no acreditan pruebas adicionales. No se renombró el resultado global como aprobado. La evidencia histórica de [gas](gas-scenarios.md), [fase 6](local-demo-validation.md) y [scripts adaptados](evidence/sepolia-local-complete-2026-11-15/review.json) sigue siendo válida para su versión y alcance, sin reemplazar la repetición actual pendiente.

## Cobertura y recorrido comprobado en archivos

CCNFT conserva 122/122 líneas, 116/116 sentencias, 25/25 funciones y 79/81 ramas (97,53 %). La base de `tools/summarize-coverage.py --check-baseline` exige esos valores. Las dos guardas de configuración de `trade` pendientes son inalcanzables mediante la interfaz pública actual: configurar colectores/token no acepta cero y los setters no permiten volver a ese estado. [Justificación histórica](ci-validation-2026-11-15.md).

La revisión de fase 7 vuelve a contrastar los 796 hashes del recorrido, los 14 de verificación y las dos capturas con sus tamaños y dimensiones. El informe final conservado contiene 55 controles con `actual == expected`; su historial contiene 26 hashes únicos con recibos `status=0x1` y enlaces presentes en la [guía de entrega](entrega.md). Se revisan saldos, variaciones, nominal, propiedad de A sobre ID 1, quema del ID 0, publicaciones y autorizaciones agotadas. Esto comprueba coherencia de evidencia histórica local, no el estado actual de la cadena.

Los hashes de contratos deben seguir siendo:

| Fuente | SHA-256 |
| --- | --- |
| `src/BUSD.sol` | `b1485b693e2aff898eb00e24a3899ce929a2bfbf1ff338e5e99c637509a7c53c` |
| `src/CCNFT.sol` | `f6518122b83c2c3081e1df6e74c3f4e30062966214dd03da5c2cc10214e5ed2b` |

Las capturas se abrieron y revisaron visualmente: A/Sepolia/916 BUSD y CCNFT ID 1/ERC721 con marcador genérico, sin claves ni frase de recuperación. No se alteraron PNG, contratos, URI ni metadatos. Ver [revisión visual original](evidence/metamask-import-2026-11-15/review.json).

## Contenido de entrega y copia limpia

La herramienta [check-delivery.py](../tools/check-delivery.py) usa `git ls-files --cached --others --exclude-standard -z` para incluir archivos versionados y nuevos no ignorados. Rechaza secretos/artefactos por ruta, symlinks y archivos ausentes; comprueba enlaces relativos y anclas Markdown, imágenes PNG/SVG, `.env.example` vacío, patrones de credenciales y coincidencias exactas con valores sensibles del `.env` local sin imprimirlos. Las capturas se revisaron además visualmente. La búsqueda de patrones no demuestra la ausencia de todo secreto posible; sí delimita la revisión efectuada.

También contrasta los manifiestos históricos, los recibos y los hashes de contratos/tests Solidity/ejecutores existentes. El README cambia por documentación; la corrección de la prueba Python se identifica por hash anterior y nuevo (`03fca8b35a48d7dc152415b6d89ee30627b92ad6a2884efb99cad09289c4f11f`). La nueva herramienta se identifica aparte. Un resultado estático `passed` no acredita instalación ni ejecución limpia. El [README original de la consigna](consigna-entrega.md) se copió byte a byte; su hash y comparación se registran en el control.

El exportador copia exactamente ese conjunto y verifica SHA-256; no incluye `.git`, `.env`, `.tools`, `lib`, `out`, `cache` ni `broadcast`. Puede reproducirse desde la raíz:

```bash
# Los dos destinos deben ser nuevos; elegir otro sufijo en cada intento.
python3 tools/check-delivery.py \
  --output-dir .tools/delivery-check/revision-nueva \
  --snapshot /tmp/cryptocampo-entrega-nueva
cd /tmp/cryptocampo-entrega-nueva
bash tools/setup.sh
export PATH="$PWD/.tools/bin:$PATH"
# Solo si el instalador termina con código cero:
# El exportado no tiene .git: crear metadatos locales para los controles Git.
git init
git add .
git -c user.name='Reproduccion local' -c user.email='local@example.invalid' \
  commit -m 'Contenido local preparado para reproduccion'
make validate
python3 tools/check-delivery.py
```

Ese commit identifica únicamente la copia temporal; no acredita publicación ni debe confundirse con un SHA del repositorio remoto. Compilación, pruebas y Anvil no necesitan `.env`. No deben copiarse herramientas, bibliotecas ni cachés del entorno existente para declarar una instalación limpia.

La primera copia limpia se intentó instalar con `bash tools/setup.sh`: **código 6, `Could not resolve host: github.com`**. Se conservan [comando, ruta y cantidad de archivos](evidence/delivery-2026-11-16/initial-clean-install.json) y [salida original](evidence/delivery-2026-11-16/initial-clean-install.txt). Ese primer intento precede a la nueva documentación; la revisión final registra otra exportación del contenido preparado y su intento de instalación. No se sustituyó la descarga fallida por dependencias ignoradas del entorno actual.

## Defecto reproducible encontrado en copia limpia

La exportación inicial de 2.816 archivos coincidió en todos sus hashes y pasó el control estático, pero la suite Python sin compilación registró 69 éxitos y un error: `test_reverts_require_rpc_revert_data_and_reject_transport_errors` leía `out/CCNFT.sol/CCNFT.json`. Ese archivo está ignorado y el validador ejecuta Python antes de compilar. Ver [fallo original](evidence/delivery-2026-11-16/clean-python-tests.txt) y [registro de la primera reproducción del contenido preparado](evidence/delivery-2026-11-16/clean-reproduction.json).

Se corrigió únicamente esa prueba en `tools/test_sepolia.py`: proporciona una ficha mínima de `methodIdentifiers` mediante `patch.object`, con el selector `505546e7` de `listTokensOnSale(uint256)`. La prueba conserva los tres escenarios: reversión RPC con datos vacíos aceptada, datos incorrectos rechazados y error de transporte propagado. Ya no necesita `out/` ni modifica el ejecutor público. Esta corrección cumple el criterio del plan de cambiar código solo ante un defecto reproducible. La repetición desde una nueva exportación de **2.870 archivos con hashes coincidentes**, sin `out/`, aprobó las **70 pruebas Python**. El control estático también aprobó en esa copia. La instalación volvió a fallar por DNS (código 6), por lo que no se ejecutó la validación integral limpia. La repetición integral en el entorno existente mantiene 19/21 comandos con código cero y los dos bloqueos por sockets.

La [revisión estática de esa exportación inicial](evidence/delivery-2026-11-16/prepared-content-check.json) registra los hashes y el resultado previo a esta corrección. Los informes nuevos identifican la versión corregida separadamente. Una revisión estática aprobada no ocultó el fallo de ejecución.

## Resultado final de las revisiones locales

La [revisión consolidada](evidence/delivery-2026-11-16/review.json) conserva estados, versiones, contratos, corrección reproducible, hashes de evidencia y bloqueos.

- [Exportación corregida: manifiesto y diez controles estáticos](evidence/delivery-2026-11-16/corrected-content-check.json). Identifica el README, la herramienta y la prueba corregidos. Los hashes identifican el contenido exportado; los informes generados después de exportarlo quedan fuera de ese manifiesto.
- [Reproducción corregida: comandos, códigos y límites](evidence/delivery-2026-11-16/corrected-clean-reproduction.json), [70 pruebas sin artefactos](evidence/delivery-2026-11-16/corrected-clean-python-tests.txt), [control estático en la copia](evidence/delivery-2026-11-16/corrected-clean-static-check.json) e [instalación DNS bloqueada](evidence/delivery-2026-11-16/corrected-clean-setup.txt).
- [Requisitos del instalador y comandos Makefile revisados](evidence/delivery-2026-11-16/environment-review.json): herramientas presentes, sintaxis Bash, Python y `git diff --check` correctos; `make -n` revisado sin publicar transacciones.
- [Prueba negativa del auditor](evidence/delivery-2026-11-16/negative-audit-probe.json): una copia temporal con enlace roto y cabecera PEM sintética fue rechazada por los dos controles correspondientes. La muestra se eliminó; no se introdujeron credenciales reales.

La reproducción completa permanece pendiente de instalación y ejecución con red y sockets, aunque el defecto de la prueba Python ya está resuelto. No se usaron herramientas, bibliotecas ni artefactos ignorados del entorno actual para aprobar los controles de la copia.

## Condiciones pendientes de aceptación

1. En un entorno con DNS/HTTPS y sockets locales, instalar y ejecutar `make validate` sobre la copia limpia. Exigir 21 controles aprobados, cobertura base, 35 mediciones exitosas y ambos recorridos con 26 recibos y 419 comprobaciones cada uno. Verificar de nuevo saldo, nominal, propiedad, quema, lista y autorizaciones.
2. Conservar el resultado nuevo, comandos, versiones y hashes en otro directorio. Mantener los bloqueos de esta sesión como antecedentes.
3. Revisar la [matriz de entrega](matriz-entrega.md), publicar el contenido autorizado posteriormente y comprobarlo desde un clon limpio del repositorio publicado, con los enlaces/capturas accesibles.

**La fase 8 no se declara cerrada ni lista con reproducción aprobada.** La documentación y el contenido local permiten revisar lo preparado y los bloqueos concretos. La publicación no formó parte del alcance autorizado de esta implementación.
