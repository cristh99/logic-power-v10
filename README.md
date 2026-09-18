# Logic Power v10 — decisiones proof-carrying

**Cuando la información actual no decide una afirmación, esta lógica sintetiza el
experimento mínimo que elimina la ambigüedad. Si ningún experimento permitido puede
hacerlo, entrega una obstrucción verificable en vez de adivinar.**

Cada ejecución termina en uno de dos objetos revisables:

1. una **política de experimentos exacta** que separa toda pareja de hipótesis con
   respuestas opuestas; o
2. una **obstrucción exacta**: dos hipótesis con respuestas opuestas que son
   indistinguibles bajo *toda* la gramática experimental declarada.

No hay un tercer camino donde el sistema rellene el hueco con confianza.

---

## Teorema de separación experimental finita

Sea `H` un conjunto finito de hipótesis, `P : H → {0,1}` la propiedad buscada y `E`
una familia declarada de experimentos. Cada experimento `e` induce una observación
`O_e(h)`.

> Existe un monitor exacto construido con `E` **si y sólo si** para toda pareja
> `h₀, h₁` con `P(h₀) ≠ P(h₁)` existe un experimento `e` tal que `O_e(h₀) ≠ O_e(h₁)`.

La equivalencia es exhaustiva: produce **política exacta** u **obstrucción exacta**.

El resultado matemático de fondo (observaciones suficientes, árboles de decisión,
test covers) es matemática establecida. Lo que aporta este repositorio es el
**compilador proof-carrying integrado y el protocolo de obstrucción**: código
ejecutable, certificados deterministas y verificadores independientes.

## Semántica del monitor

| Terminal | Significado |
|---|---|
| `TRUE` / `FALSE` | toda hipótesis aún compatible comparte el mismo valor |
| `UNKNOWN` | la evidencia actual no decide; hay que adquirir información |
| `INCONSISTENT` | el conjunto de hipótesis compatibles quedó vacío |
| `IMPOSSIBLE` | existe una pareja con respuestas opuestas indistinguible bajo toda la gramática declarada |

`IMPOSSIBLE` no es un fallo: es el resultado correcto, con la pareja testigo
adjunta, cuando el lenguaje experimental es insuficiente. La respuesta correcta es
ampliar el lenguaje, no estimar.

## Capacidad instalada

```text
pregunta lógica
→ hipótesis compatibles
→ parejas con respuestas opuestas
→ experimento separador mínimo
→ actualización de la creencia
→ veredicto exacto o nueva consulta
→ certificado Exact / Impossible
```

- **Base fija mínima:** resuelve el *hitting set* ponderado de todas las parejas conflictivas.
- **Política adaptativa óptima:** minimiza primero el peor costo y después el costo esperado.
- **Síntesis guiada por conflicto (CEGIS):** cada contraejemplo vivo se convierte en
  adquisición de información y reducción verificable del conflicto.
- **Aritmética racional exacta:** `Fraction`, sin flotantes. Los verificadores usan
  `BigInt` en Node y enteros arbitrarios en Python.
- **Certificados:** payload canónico con SHA-256 determinista, replay semántico en
  Python y verificador **independiente** en Node/BigInt.
- **Controles negativos:** un certificado alterado debe ser rechazado por ambos
  verificadores. Es un gate, no una nota al pie.

---

## Qué está probado, con qué herramienta

Esta tabla es el contrato honesto del repositorio. Nada fuera de ella está probado.

| Gate | Herramienta | Qué establece |
|---|---|---|
| 12 pruebas exactas del núcleo | Python `unittest` | política adaptativa, base fija mínima, terminales, obstrucción |
| Replay semántico | `logic_power_v10/verify_logic_power_v10.py` | el certificado se reconstruye desde su payload |
| Verificador independiente | `logic_power_v10/verify_logic_power_v10.js` (Node/BigInt) | una segunda implementación, sin compartir código, acepta el mismo certificado |
| Control negativo | ambos verificadores sobre un certificado alterado | ambos **rechazan** con `payload-hash` |
| Reconstrucción determinista | segunda ejecución del motor | hashes idénticos byte a byte |
| Análisis sintáctico y semántico | TLA+ / SANY 1.8.0 | `tla_v10/ActiveDiscovery.tla` sin errores |
| Model checking — Exact | TLC 1.8.0 | invariantes `TypeOK`, `BeliefNonempty`, `TrueSound`, `FalseSound`, `ImpossibleSound`, `TerminalLegitimate` y propiedad `Termination` |
| Model checking — Impossible | TLC 1.8.0 | la obstrucción emitida es legítima y el modelo termina |
| Teoremas de frontera | Lean 4.33.0-rc1 | declaraciones compiladas **sin `sorry` y sin `sorryAx`** |
| Manifiesto de release | `tools/validate_logic_power_release.py` | los árboles Git publicados coinciden con los SHA de los objetos de origen |

**Lo que estos gates NO establecen:** omnisciencia, decidibilidad universal,
prioridad científica externa, validez causal en el mundo real, superioridad frente a
métodos existentes, ni aptitud para producción. Fuera de la gramática declarada la
respuesta correcta sigue siendo ampliar el lenguaje o conservar la abstención.

---

## Reproducir los gates

Requisitos: **Python ≥ 3.12**, **Node ≥ 18**, **Java ≥ 11** (para TLA+),
**elan/Lean 4.33.0-rc1** (fijado en `lean-toolchain`).

### 1. Núcleo — Python + Node + controles negativos + determinismo

```bash
export PYTHONPATH="$PWD"
mkdir -p reports certificates

python -m unittest discover -s logic_power_v10 -p 'test_*.py' -v
python -m logic_power_v10.run_logic_power_v10

# ambos verificadores deben ACEPTAR
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_exact.json
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_impossible.json
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_exact.json
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_impossible.json

# control negativo: ambos deben RECHAZAR (salida != 0)
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_tampered.json || echo "rechazado por Python (correcto)"
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_tampered.json || echo "rechazado por Node (correcto)"
```

El guion completo, incluidas la reconstrucción determinista y la cápsula de
evidencia, es `logic_power_v10/ci_v10.sh`.

### 2. TLA+ / TLC

```bash
curl -L --fail -o tools/tla2tools.jar \
  https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar
echo 'feffd16994db963ad945628cfd03d154c195a468  tools/tla2tools.jar' | sha1sum -c -

java -cp tools/tla2tools.jar tla2sany.SANY tla_v10/ActiveDiscovery.tla

cd tla_v10
java -cp ../tools/tla2tools.jar tlc2.TLC -workers 1 -config ActiveDiscoveryExact.cfg      ActiveDiscovery.tla
java -cp ../tools/tla2tools.jar tlc2.TLC -workers 1 -config ActiveDiscoveryImpossible.cfg ActiveDiscovery.tla
```

Ambas corridas deben imprimir `Model checking completed. No error has been found.`

### 3. Lean

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
export PATH="$HOME/.elan/bin:$PATH"
lean ActiveDiscoveryFinite.lean   # no debe aparecer 'sorryAx' en la salida
```

Los archivos Lean sólo importan `Std` (incluido con Lean 4). No requieren Mathlib.

### 4. Manifiesto de release

```bash
python tools/validate_logic_power_release.py --manifest LOGIC_POWER_RELEASE_MANIFEST.json --root .
python -m unittest -v tests.test_logic_power_release_manifest
```

> **Aviso Windows.** `tests/test_logic_power_release_manifest.py` compara hashes de
> árboles Git. Con `core.autocrlf=true` o `core.fileMode=false` (los valores por
> defecto de Git for Windows) una de las 7 pruebas falla por conversión de finales
> de línea y por el bit ejecutable, no por un defecto del código. Ejecutarla con
> `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null` da 7/7. El
> `.gitattributes` de este repositorio fija LF para evitar el mismo problema al
> clonar.

---

## Estado: qué significa "VERIFIED"

El registro canónico del autor marca Logic Power v10 como **VERIFIED el 2 de agosto
de 2026**, con puntuación **1000/1000 *dentro del dominio finito ejecutable
declarado***.

"Verified" aquí significa, de forma concreta y nada más que esto: **todos los gates
de la tabla anterior pasaron sobre una fuente fijada, y los certificados se
reconstruyen de forma determinista**. En el registro canónico:

| Objeto | SHA-256 |
|---|---|
| Certificado `Exact` | `7a05fde469d38ebed19e22838b16776f3bfcec462791d275069e38b2dbea3e7c` |
| Certificado `Impossible` | `0367df5ca9d49c523f87ca1f39c5ebbea4d591231f642ff72f584c012a01b602` |

Ese registro también fija: Python 12/12; verificador Node aceptando ambos
certificados; certificado alterado rechazado por ambos; reconstrucción determinista
con hashes idénticos; SANY sin errores; TLC `Exact` con 5 estados generados, 3
distintos, profundidad 2; TLC `Impossible` con 3 generados, 2 distintos, profundidad
2; Lean 4.33.0-rc1 con 7/7 declaraciones compiladas, ninguna dependiente de axiomas
y sin `sorryAx`.

### Reverificación independiente — 18 de septiembre de 2026

Antes de publicar, los gates ejecutables de este árbol se volvieron a correr sobre
Python 3.14.4 y Node v24.15.0:

| Gate | Resultado |
|---|---|
| Pruebas del núcleo | **12/12 PASS** |
| Verificador Python — `Exact` / `Impossible` | **acepta ambos** |
| Verificador Node/BigInt — `Exact` / `Impossible` | **acepta ambos** |
| Control negativo (certificado alterado) | **rechazado por ambos**, error `payload-hash` |
| Reconstrucción determinista | **PASS** (hashes idénticos) |
| Hashes canónicos de certificado | **reproducidos exactamente** (`7a05fde4…`, `0367df5c…`) |
| `validate_logic_power_release.py` | **`LOGIC_POWER_RELEASE_MANIFEST_PASS`** |
| `tests/test_logic_power_release_manifest.py` | **7/7 PASS** |
| Ejemplo — finance | **10/10 PASS** |
| Ejemplo — logistics | **9/9 PASS** |
| Problem Solver v1 | **32/32 PASS** |
| LP-KAL v1 | **24/24 PASS** |

**No reverificados en esa sesión:** TLA+/SANY, TLC y Lean. La máquina no tenía Java
ni la cadena de herramientas Lean instalados. Para esos tres gates el repositorio
ofrece los comandos exactos y las versiones fijadas, no una afirmación de ejecución.
Corrígelo tú mismo con la sección 2 y 3.

---

## Contenido

### Núcleo

| Ruta | Qué es |
|---|---|
| `logic_power_v10/` | motor de descubrimiento activo, certificados, verificadores Python y Node, 12 pruebas |
| `tla_v10/` | especificación TLA+ del ciclo de vida y las dos configuraciones TLC (`Exact`, `Impossible`) |
| `ActiveDiscoveryFinite.lean` | teoremas de frontera en Lean 4, sin `sorry` |
| `README_v10.md` | documento original del núcleo v10 |
| `LOGIC_POWER_RC.md`, `LOGIC_POWER_RELEASE_MANIFEST.json`, `tools/`, `tests/` | manifiesto de release, linaje por SHA de objetos Git y su validador |

### Componentes del release RC1

| Ruta | Qué es | Estado declarado |
|---|---|---|
| `logic_power_problem_solver_v1/` + `tla_problem_solver_v1/` + `ProblemSolverBoundary.lean` | representación tipada de problemas, enrutamiento de solvers, decisión y planificación exactas, certificados | `INTERNALLY_VERIFIED` — la utilidad externa no está establecida |
| `logic_power_knowledge_action_loop_v1/` + `tla_lp_kal_v1/` + `lean_lp_kal_v1/` | puentes tipados Conocimiento ↔ Acciones: autoridad, evidencia, retroalimentación | verificado internamente; su calibración V4 **empató** con una línea base monolítica igualmente protegida |

### Ejemplos aplicados

| Ruta | Qué es |
|---|---|
| `examples/finance-decisions/` | 5 casos financieros exactos + 1 obstrucción (pasivo tributario oculto), 160 hipótesis finitas, 1 242 parejas conflictivas, 6 certificados |
| `examples/logistics-capex/` | compuerta de autorización de expansión de capacidad: 8 mundos, 7 parejas opuestas, 3 sondas, obstrucción exacta al retirar la traza de continuidad del proveedor |

Los ejemplos importan el paquete `logic_power_v10` desde la raíz:

```bash
PYTHONPATH="$PWD:$PWD/examples/finance-decisions" \
  python -m unittest discover -s examples/finance-decisions/finance_logic_v10 \
                              -t examples/finance-decisions -p 'test_*.py'

PYTHONPATH="$PWD:$PWD/examples/logistics-capex" \
  python -m unittest discover -s examples/logistics-capex/logistics_power_v1 \
                              -t examples/logistics-capex -p 'test_*.py'
```

`examples/logistics-capex/certificates/` trae los dos certificados ya construidos,
de modo que se pueden verificar **sin ejecutar el motor**:

```bash
PYTHONPATH="$PWD" python -m logic_power_v10.verify_logic_power_v10 \
  examples/logistics-capex/certificates/logistics_power_v1_capex_exact.json
node logic_power_v10/verify_logic_power_v10.js \
  examples/logistics-capex/certificates/logistics_power_v1_capex_impossible.json
```

Ambos son aceptados por los dos verificadores (comprobado el 18-09-2026).

Cada ejemplo conserva su propia frontera honesta en su README. Ambos son **sintéticos,
finitos, deterministas y de aritmética racional exacta**. Los costos, umbrales y
priors son entradas declaradas, no estimaciones empíricas. El ejemplo financiero
**no es asesoría financiera**; el logístico **no prueba validez causal operativa**.

### Procedencia

`LOGIC_POWER_RELEASE_MANIFEST.json` conserva los SHA de los objetos Git de origen y
los números de PR del repositorio privado del autor donde se verificó el material.
Esas referencias no son navegables desde fuera: se publican como linaje, para que
cualquiera pueda comprobar que los árboles aquí publicados son los mismos objetos
inmutables que pasaron los gates, y no una copia reescrita.

### Flujo de trabajo de CI

`.github/workflows/logic-power-v10.yml` es el guion de gates completo tal como
existe en la fuente. Se ejecuta en `workflow_dispatch` y en pull requests que tocan
el núcleo; descarga TLA+ 1.8.0 (verificando su SHA-1) e instala Lean por elan. Los
guiones de CI de los ejemplos se incluyen como `ci-*.yml` **sin activar**, para
lectura.

---

## English summary

**Logic Power v10 turns finite logical uncertainty into one of exactly two checkable
outputs:** an exact experiment policy that separates every pair of hypotheses with
opposite answers, or an exact obstruction — a witness pair that no admissible
experiment can distinguish. There is no third branch where the system guesses.

The monitor terminates in `TRUE`, `FALSE`, `UNKNOWN`, `INCONSISTENT` or
`IMPOSSIBLE`. `IMPOSSIBLE` is a first-class, certificate-carrying answer: the
declared experiment grammar is insufficient, and the correct move is to extend the
language rather than to estimate.

**What is proven, and by what.** Twelve exact Python tests cover the minimum fixed
basis, the cost-optimal adaptive policy and the terminals. Every decision emits a
deterministic SHA-256 certificate, replayed semantically in Python and checked again
by an *independent* Node/BigInt verifier that shares no code with the engine. A
tampered certificate must be rejected by both — that negative control is a gate, not
a footnote. A second run must reproduce identical hashes. `tla_v10/ActiveDiscovery.tla`
is checked by TLA+/SANY and model-checked by TLC in both the `Exact` and the
`Impossible` configuration against six safety invariants and a termination property.
`ActiveDiscoveryFinite.lean` compiles under Lean 4.33.0-rc1 with no `sorry` and no
`sorryAx`. All arithmetic is exact rational; there are no floats anywhere in the
decision path.

**Status.** The author's canonical record marks v10 `VERIFIED` on 2 August 2026, at
`1000/1000` *within the declared finite executable domain*. That phrase means only
this: every gate above passed over a pinned source and the certificates rebuild
deterministically. It is not a claim of omniscience, universal decidability, external
scientific priority, real-world causal validity, or production readiness.

**Re-verified on 18 September 2026** on Python 3.14.4 and Node v24.15.0: core 12/12;
both verifiers accept both certificates; the tampered certificate is rejected by both
with `payload-hash`; the deterministic rebuild matches; the canonical certificate
hashes reproduce exactly; the release-manifest validator returns
`LOGIC_POWER_RELEASE_MANIFEST_PASS`; manifest tests 7/7; applied examples 10/10 and
9/9; Problem Solver 32/32; LP-KAL 24/24. TLA+/TLC and Lean were **not** re-run in
that session — no Java or Lean toolchain was present — so for those three gates this
repository publishes the exact pinned commands rather than a claim of execution. Run
sections 2 and 3 above and check for yourself.

Reproduction commands, per-component boundaries and the full contents map are in the
Spanish sections above; every path and command is identical.

---

## Autoría y licencia

Copyright © 2026 Cristhian López (<https://github.com/cristh99>).

Publicado bajo la **licencia MIT** (ver [`LICENSE`](LICENSE)). Los archivos de origen
no declaraban ninguna licencia; MIT se elige aquí por primera vez para esta
publicación.

Historia de Git: este repositorio es un **árbol huérfano**. Contiene el núcleo
verificado y dos ejemplos aplicados, y ningún dato de tesis, evidencia documental,
dato personal, credencial, ruta local ni dirección de red.
