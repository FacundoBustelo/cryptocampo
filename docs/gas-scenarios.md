# Medición de gas por escenario

El script `tools/measure-gas.py` está preparado para ejecutarse en el paso **Medir gas por tamaño de lista y lote** de GitHub Actions. Todavía no se dispone de resultados de su ejecución con Anvil. No modifica los contratos ni requiere claves personales, cuentas externas o Sepolia.

## Método

Antes de medir, CI ejecuta `forge build --force`. El script comprueba en los metadatos de los artefactos que ambos contratos usan Solidity 0.8.19, EVM Paris y optimizador habilitado con 200 runs. Rechaza artefactos con otra configuración.

Inicia un Anvil temporal en `127.0.0.1:18545`, chain ID 31337, hardfork Paris y límite de bloque de 30.000.000 gas. No utiliza forks ni endpoints externos y termina su proceso al finalizar o fallar. Usa cinco cuentas de desarrollo desbloqueadas del nodo, con funciones de administrador, comprador A, comprador B, colector de fondos y colector de comisiones. Los selectores se obtienen de los artefactos de compilación y se codifican los argumentos usados por este contrato, incluidos los arrays de `claim`.

Para cada longitud de lista se despliegan contratos nuevos y se configura nominal de 100 BUSD, lote máximo 10, comisión de compra del 2 %, de reventa del 1 % y beneficio del 5 %. El límite nominal se aumenta solo en el escenario de medición a 1.000.000 BUSD para poder comparar compras adicionales tras preparar listas de hasta 100 publicaciones. Se financian compradores y colector y se conceden sus aprobaciones. Se emiten los NFTs y se preparan las publicaciones antes de la transacción medida. Hay diez NFTs adicionales sin publicar para medir inserciones y reclamos de lotes completos.

Cada operación medida es una transacción independiente sin lista de acceso explícita. Los accesos a almacenamiento siguen las reglas de calentamiento de esa transacción y no heredan accesos de las transacciones de preparación. Se registra `gasUsed` del recibo de una transacción exitosa: incluye el gas intrínseco y los efectos de los reembolsos aplicables. No es una resta de `gasleft()` dentro de un test ni el gas de una función completa de prueba.

Un snapshot antes de cada operación y su restauración posterior permiten partir del mismo estado dentro de cada escenario. No se cuenta el gas de despliegue, configuración, financiación o preparación. No se mantienen los cambios de una medición para la siguiente.

## Matriz de 35 transacciones

| Operación | Listas iniciales | Lotes o posiciones |
| --- | --- | --- |
| Compra | 1, 10, 100 | Lotes de 1 y 10 NFTs. |
| Nueva publicación | 1, 10, 100 | Insertar un NFT existente sin publicar. |
| Actualización de precio | 1, 10, 100 | Primer y último ID de la lista; cambiar 120 a 121 BUSD. |
| Reventa | 1, 10, 100 | Primer, intermedio y último ID, a 120 BUSD. |
| Reclamo sin publicación | 1, 10, 100 | Lotes de 1 y 10; búsqueda sin coincidencias en la lista. |
| Reclamo publicado | 1, 10, 100 | Lote de 1; lote de 10 solo cuando hay al menos 10 publicados. IDs del final en orden descendente para medir búsquedas largas repetidas. |

Con una lista de un elemento, las posiciones primera, intermedia y última coinciden. No se simula un lote de diez publicados cuando solo hay uno. El script imprime el commit, las revisiones de las bibliotecas, las versiones de Forge y Anvil y una tabla compacta. Guarda también los resultados en `.tools/gas-scenarios.json`, excluido de Git. Una transacción revertida, una configuración de compilación incorrecta o un fallo al restaurar el estado hace fallar el paso.

## Reproducción y límites

Con el entorno ya instalado, desde `cryptocampo/`:

```bash
.tools/bin/forge build --force
python3 tools/measure-gas.py
```

Las mediciones describen únicamente esta matriz, el BUSD del proyecto y receptores que son cuentas de desarrollo. No establecen un máximo global: la lista puede superar 100 elementos y un receptor contrato o un ERC20 configurado distinto puede consumir más gas. Tampoco se fija un límite seguro para una red pública a partir del límite de bloque elegido en Anvil. Se conservará el lote de demostración de 10, documentando el rango medido, sin cambiar las reglas económicas ni limitar la lista global como parte de esta comprobación.
