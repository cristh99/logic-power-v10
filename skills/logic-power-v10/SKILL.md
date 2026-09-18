---
name: logic-power-v10
description: Emitir y verificar decisiones proof-carrying en dominios finitos declarados con Logic Power v10 — certificados JSON canónicos con digest SHA-256, replay semántico en Python y un segundo verificador independiente en Node/BigInt, con `Exact` e `Impossible` como respuestas de primera clase. Usar cuando se quiere una decisión acompañada de un certificado verificable, comprobar un certificado recibido de un tercero, reproducir los gates del repositorio o interpretar qué significa —y qué no— «VERIFIED» dentro del dominio finito ejecutable declarado.
---

# Logic Power v10 — decisiones proof-carrying

## Qué es

Logic Power v10 opera sobre un **dominio finito ejecutable declarado**: un conjunto finito de hipótesis `H`, una propiedad `P : H → {0,1}` y una familia declarada de experimentos `E`, cada uno con su observación `O_e(h)`. `Exact` e `Impossible` son respuestas de primera clase, no errores: toda ejecución termina en una política de experimentos exacta que separa toda pareja con respuestas opuestas, o en una obstrucción exacta con su pareja testigo. No hay un tercer camino donde el sistema adivine.

Teorema de separación experimental finita (textual de README.md):

> Existe un monitor exacto construido con `E` **si y sólo si** para toda pareja `h₀, h₁` con `P(h₀) ≠ P(h₁)` existe un experimento `e` tal que `O_e(h₀) ≠ O_e(h₁)`.

Su frontera declarada es «1000/1000 sólo dentro del dominio finito ejecutable declarado»; fuera de la gramática la respuesta correcta es ampliar el lenguaje, no estimar.

Los certificados son JSON proof-carrying: `{"payload": …, "sha256": …}`. En `logic_power_v10/certificate.py`, `canonical_json` serializa con `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` — claves ordenadas, sin espacios, ASCII — y `digest_payload` devuelve el SHA-256 hex de esa cadena en UTF-8. El verificador Python (`logic_power_v10/verify_logic_power_v10.py`) comprueba el digest y **reconstruye** el análisis desde `payload.problem` (base fija, CEGIS, obstrucción, política óptima), exigiendo igualdad canónica (`semantic-replay`). El verificador Node (`logic_power_v10/verify_logic_power_v10.js`) es una segunda implementación **sin código compartido**: `stableStringify` propio, racionales con `BigInt`, enumeración de subconjuntos y política memoizada. El manifiesto `LOGIC_POWER_RELEASE_MANIFEST.json` liga los árboles Git publicados por SHA-1 y `tools/validate_logic_power_release.py` los valida contra el checkout.

## Cuándo usarla

- Cuando una decisión deba venir acompañada de un certificado verificable por terceros.
- Para verificar un certificado que alguien te envió, sin confiar en el emisor.
- Para reproducir los gates del repositorio: pruebas del núcleo, ambos verificadores, control negativo y manifiesto.
- Para entender qué significa —y qué no— «VERIFIED 1000/1000 dentro del dominio finito ejecutable declarado».
- Para diagnosticar una obstrucción: localizar la pareja testigo y qué experimento le falta a la gramática.

## Comandos

Desde la raíz del repositorio (Python ≥ 3.12, Node ≥ 18). Todo lo de abajo se ejecutó y la salida mostrada es la observada.

```bash
export PYTHONPATH="$PWD"
mkdir -p reports certificates
python -m unittest discover -s logic_power_v10 -p 'test_*.py' -v
```

Observado: `Ran 12 tests in 0.461s` / `OK` — exit 0.

```bash
python -m logic_power_v10.run_logic_power_v10
```

Observado: exit 0; escribe `certificates/logic_power_v10_{exact,impossible,tampered}.json` y `reports/logic_power_v10{,.canonical}.json`.

```bash
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_exact.json
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_impossible.json
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_exact.json
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_impossible.json
```

Observado: `{"errors": [], "valid": true}` (Python) y `{"valid":true,"errors":[]}` (Node) — exit 0 en los cuatro.

```bash
python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_tampered.json || echo "rechazado por Python (correcto)"
node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_tampered.json || echo "rechazado por Node (correcto)"
```

Observado: `{"errors": ["payload-hash"], "valid": false}` y `{"valid":false,"errors":["payload-hash"]}` — **exit 1 en ambos**: el certificado alterado es rechazado por los dos verificadores.

```bash
PYTHONPATH="$PWD:$PWD/examples/finance-decisions" \
  python -m unittest discover -s examples/finance-decisions/finance_logic_v10 \
                          -t examples/finance-decisions -p 'test_*.py'
PYTHONPATH="$PWD:$PWD/examples/logistics-capex" \
  python -m unittest discover -s examples/logistics-capex/logistics_power_v1 \
                          -t examples/logistics-capex -p 'test_*.py'
```

Observado: `Ran 10 tests … OK` (finance) y `Ran 9 tests … OK` (logistics).

```bash
PYTHONPATH="$PWD" python -m logic_power_v10.verify_logic_power_v10 \
  examples/logistics-capex/certificates/logistics_power_v1_capex_exact.json
node logic_power_v10/verify_logic_power_v10.js \
  examples/logistics-capex/certificates/logistics_power_v1_capex_impossible.json
```

Observado: `{"errors": [], "valid": true}` y `{"valid":true,"errors":[]}` — los dos certificados pre-construidos son aceptados por ambos verificadores.

```bash
python tools/validate_logic_power_release.py --manifest LOGIC_POWER_RELEASE_MANIFEST.json --root .
python -m unittest -v tests.test_logic_power_release_manifest
```

El gate exige `LOGIC_POWER_RELEASE_MANIFEST_PASS`. En esta máquina (18-09-2026) la salida observada fue `LOGIC_POWER_RELEASE_MANIFEST_REJECTED: Git tree mismatch for logic_power_v10: 36dd15ab… != 0c5f6386…` (exit 2) y `Ran 7 tests … FAILED (failures=1)`: el manifiesto **no** quedó verificado en esta corrida.

## Cómo leer un certificado

Un certificado es `{"payload": …, "sha256": …}`. En `certificates/logic_power_v10_exact.json` el payload trae `schema` (= `logic-power-v10/active-discovery-certificate/1`), `case` (`or_8_exact`), `problem` (`hypotheses` con `id`/`property`/`prior` y `experiments` con `name`/`cost`/`observations`, fracciones como `[numerador, denominador]`) y `analysis` (`conflict_pairs`, `fixed_basis`, `fixed_basis_cost`, `cegis_basis`, `obstruction`, `policy` con `exact`, `worst_cost`, `expected_cost`, `tree`). El `sha256` se calcula sobre la serialización **canónica** del payload (`canonical_json`), no sobre los bytes del archivo. En el certificado impossible de logística (`examples/logistics-capex/certificates/logistics_power_v1_capex_impossible.json`):

```json
      "obstruction": [
        "c1_q0_s0",
        "c1_q0_s1"
      ],
      "policy": {
        "exact": false,
        "expected_cost": [
          0,
          1
        ],
```

Un `Exact` trae `fixed_basis` con los experimentos separadores (en `or_8_exact`: `bit_0`…`bit_7`, `fixed_basis_cost: [8,1]`), `obstruction: null` y `policy.exact: true`. Un `Impossible` trae `fixed_basis: null`, `policy.exact: false`, estado `IMPOSSIBLE` en el árbol y la **pareja testigo** en `analysis.obstruction`: dos hipótesis con `property` opuesta que ningún experimento declarado separa (`c1_q0_s0` vs `c1_q0_s1` aquí; `false_world` vs `true_world` en el demo del núcleo).

## Verificación independiente

No confíes en el productor: ejecuta **ambos** verificadores y compara los códigos de salida (0 = acepta, 1 = rechaza). Un rechazo real se ve así:

```text
$ python -m logic_power_v10.verify_logic_power_v10 certificates/logic_power_v10_tampered.json
{"errors": ["payload-hash"], "valid": false}          # exit 1
$ node logic_power_v10/verify_logic_power_v10.js certificates/logic_power_v10_tampered.json
{"valid":false,"errors":["payload-hash"]}             # exit 1
```

Importa que sean dos implementaciones sin código compartido: el de Python reejecuta el análisis desde `problem`; el de Node recomputa todo con `BigInt` (conflictos, base mínima por subconjuntos, política memoizada, árbol nodo a nodo). Una discrepancia entre ambos señala bug o manipulación, no ruido. `sha256sum` sobre el **archivo** reproduce el hash publicado sólo para archivos byte-idénticos a lo hasheado: `sha256sum certificates/logic_power_v10_exact.json` dio `f32706b3…`, distinto del campo `sha256` (`7a05fde4…`), porque el digest cubre el payload canónico, no el formato pretty-printed del archivo.

## Nunca

- Nunca afirmes nada fuera del dominio finito declarado: «1000/1000» vale sólo dentro del dominio finito ejecutable declarado.
- Nunca presentes `Impossible` como un hecho negativo sobre el mundo: es una obstrucción relativa a las hipótesis y la gramática declaradas, con su pareja testigo; la respuesta correcta es ampliar el lenguaje.
- Nunca digas que los gates TLA+/TLC o Lean pasaron salvo que se ejecutaran en la corrida actual (esta sesión no los ejecutó: la máquina no tiene Java ni Lean).
- El ejemplo financiero no es asesoría financiera; ambos ejemplos son sintéticos, finitos y con entradas declaradas, no estimaciones empíricas.
- Problem Solver v1 y LP-KAL v1 son `INTERNALLY_VERIFIED` únicamente: sin afirmación de utilidad externa ni de superioridad.
- Nunca edites un certificado y lo «refirmes»: el digest deja de coincidir y ambos verificadores lo rechazan con `payload-hash`.
- Nunca describas el manifiesto como verificado si la corrida actual no imprimió `LOGIC_POWER_RELEASE_MANIFEST_PASS`.

## Ejemplo

```bash
export PYTHONPATH="$PWD"
python -m logic_power_v10.verify_logic_power_v10 \
  examples/logistics-capex/certificates/logistics_power_v1_capex_exact.json
node logic_power_v10/verify_logic_power_v10.js \
  examples/logistics-capex/certificates/logistics_power_v1_capex_exact.json
python -m logic_power_v10.verify_logic_power_v10 \
  examples/logistics-capex/certificates/logistics_power_v1_capex_impossible.json
node logic_power_v10/verify_logic_power_v10.js \
  examples/logistics-capex/certificates/logistics_power_v1_capex_impossible.json
```

Observado —los cuatro, exit 0—: `{"errors": [], "valid": true}` (Python) y `{"valid":true,"errors":[]}` (Node). El `exact` (`logistics_capex_gate_exact`) fija `fixed_basis` de 3 sondas con coste `[6,1]`; el `impossible` (`logistics_capex_gate_missing_supplier_sensor`) fija `obstruction: ["c1_q0_s0","c1_q0_s1"]`, la pareja que ninguna sonda separa al retirar la traza de continuidad del proveedor.

## English summary

Logic Power v10 turns finite logical uncertainty into exactly one of two checkable objects: an exact experiment policy separating every hypothesis pair with opposite answers, or an exact obstruction — a witness pair no admissible experiment can distinguish. Every decision emits a deterministic proof-carrying JSON certificate (canonical JSON + SHA-256 digest), replayed semantically by a Python verifier and independently rechecked by a Node/BigInt verifier that shares no code with it; a tampered certificate is rejected by both. All claims hold only inside the declared finite executable domain — «1000/1000» means every gate passed on a pinned source, nothing more — and `Impossible` is a scoped obstruction, not a negative fact about the world.
